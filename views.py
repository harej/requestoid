import arrow
import configparser
import os
from . import models, wiki
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from mwoauth import ConsumerToken, Handshaker, tokens
from worldly import Worldly

# Views! Views! Views, views, views, views, views views views views views views has a has a has a has a kind of mystery

ROOTDIR = '/var/www/django-src/requestoid/requestoid'
LOCALEDIR = ROOTDIR + '/locale'
translation = Worldly(ROOTDIR + "/i18n.yaml")
_ = translation.render


def requests_handshaker():
    keyfile = configparser.ConfigParser()
    keyfile.read([os.path.expanduser(ROOTDIR + '/.oauth.ini')])
    consumer_key = keyfile.get('oauth', 'consumer_key')
    consumer_secret = keyfile.get('oauth', 'consumer_secret')
    consumer_token = ConsumerToken(consumer_key, consumer_secret)
    return Handshaker("https://meta.wikimedia.org/w/index.php", consumer_token)


def get_username(request):
    handshaker = requests_handshaker()
    if 'access_token_key' in request.session:
        access_key = request.session['access_token_key'].encode('utf-8')
        access_secret = request.session['access_token_secret'].encode('utf-8')
        access_token = tokens.AccessToken(key=access_key, secret=access_secret)
        return handshaker.identify(access_token)['username']
    else:
        return None


def you_need_to_login(request, langcode):
    content = {
                  'headline': _('Login required'),
                  'explanation': _('login_required_message')
              }

    context = {
                  'interface': interface_messages(request, langcode),
                  'language': langcode,
                  'content': content
              }

    return render(request, 'requestoid/error.html', context = context)


def interface_messages(request, langcode):
    '''
    Provides a dictionary to feed into the context, with an ISO 639-1 or -2 language code as input.
    '''

    translation.use_language = langcode

    output = {
                'brand': _('Wikipedia Requests'),
                'login_via_wikipedia': _('Login via Wikipedia'),
                'search': _('Search'),
                'add': _('Add'),
                'help': _('Help'),
                'about': _('About')
             }

    username = get_username(request)
    if username != None:
        output['username'] = username  # leave 'username' key unset if no session

    return output


###


def select_language(request):  # /requests
    available = [
                    {'code': 'en', 'label': 'English'}
                ]

    context = {
                  'interface': interface_messages(request, 'en'),
                  'language': 'en',
                  'available': available
              }

    return render(request, 'requestoid/select_language.html', context = context)


def homepage(request, langcode):  # /requests/en
    translation.use_language = langcode

    content = {
                  'headline': _('Help fill in the gaps on Wikipedia'),
                  'intro': _('homepage_intro')
              }

    context = {
                  'interface': interface_messages(request, langcode),
                  'language': langcode,
                  'content': content
              }

    return render(request, 'requestoid/homepage.html', context = context)


def auth(request):  # /requests/auth
    handshaker = requests_handshaker()
    redirect, request_token = handshaker.initiate()
    request.session['request_token_key'] = request_token.key.decode('utf-8')
    request.session['request_token_secret'] = request_token.secret.decode('utf-8')
    request.session['return_to'] = request.META['HTTP_REFERER']
    return HttpResponseRedirect(redirect)  # This hands the user off to Wikimedia; user returns to the website via the callback view which implements the session


def callback(request):  # /requests/callback
    oauth_verifier = request.GET['oauth_verifier']
    oauth_token = request.GET['oauth_token']
    handshaker = requests_handshaker()
    request_key = request.session['request_token_key'].encode('utf-8')
    request_secret = request.session['request_token_secret'].encode('utf-8')
    request_token = tokens.RequestToken(key=request_key, secret=request_secret)
    access_token = handshaker.complete(request_token, 'oauth_verifier=' + oauth_verifier + '&oauth_token=' + oauth_token)
    request.session['access_token_key'] = access_token.key.decode('utf-8')
    request.session['access_token_secret'] = access_token.secret.decode('utf-8')
    return HttpResponseRedirect(request.session['return_to'])


def add(request, langcode):  # /requests/en/add
    translation.use_language = langcode
    username = get_username(request)
    g = request.GET  # `g` is short for `get`
    p = request.POST  # `p` is short for `post`
    if username == None:
        return you_need_to_login(request, langcode)
    else:
        if 'pagetitle' in g:
            if g['pagetitle'] != "":
                if 'pageid' in p:  # Ready to save to database; pageid is only passed as a parameter if workflow below has been completed
                    now = arrow.utcnow().format('YYYYMMDDHHmmss')
                    userid = wiki.GetUserId(username)

                    # Creating request
                    R = models.Requests(page_id = p['pageid'],
                                        page_title = p['pagetitle'],
                                        user_id = userid,
                                        user_name = username,
                                        wiki = p['request_language'] + 'wiki',
                                        timestamp = now,
                                        summary = p['summary'],
                                        status = 0)
                    R.save()

                    # First log entry: saying the request is created
                    log = models.Logs(request = R,
                                      user_name = username,
                                      user_id = userid,
                                      timestamp = now,
                                      action = 'create',
                                      reference = R.id)
                    log.save()

                    # Next log entry: flagging it as open
                    log = models.Logs(request = R,
                                      user_name = username,
                                      user_id = userid,
                                      timestamp = now,
                                      action = 'flagopen',
                                      reference = R.id)
                    log.save()

                    # Recording note
                    N = models.Notes(request = R,
                                     user_name = username,
                                     user_id = userid,
                                     timestamp = now,
                                     comment = p['note'])
                    N.save()

                    # And a log entry stating note was left
                    log = models.Logs(request = R,
                                      user_name = username,
                                      user_id = userid,
                                      timestamp = now,
                                      action = 'addnote',
                                      reference = N.id)
                    log.save()

                    categories = p['categories'].split('\r\n')
                    wikiprojects = p['wikiprojects'].split('\r\n')

                    for category in categories:
                        if category == '' or category == ' ':
                            continue
                        if category[:9] == 'Category:':
                            category = category[9:]  # truncate "Category:"
                        C = models.Categories(request = R,
                                              cat_id = wiki.GetCategoryId(p['request_language'], category),
                                              cat_title = category,
                                              wiki = p['request_language'] + 'wiki')
                        C.save()

                        log = models.Logs(request = R,
                                          user_name = username,
                                          user_id = userid,
                                          timestamp = now,
                                          action = 'addcategory',
                                          reference = C.id)
                        log.save()

                    for wikiproject in wikiprojects:
                        if wikiproject == '' or wikiproject == ' ':
                            continue
                        if wikiproject[:10] == 'Wikipedia:':
                            wikiproject = wikiproject[10:]  # truncate "Wikipedia:"
                        W = models.WikiProjects(request = R,
                                                project_id = wiki.GetWikiProjectId(p['request_language'], wikiproject),
                                                project_title = wikiproject,
                                                wiki = p['request_language'] + 'wiki')
                        W.save()
                        log = models.Logs(request = R,
                                          user_name = username,
                                          user_id = userid,
                                          timestamp = now,
                                          action = 'addwikiproject',
                                          reference = W.id)
                        log.save()

                    return HttpResponseRedirect("/requests/" + langcode + "/request/" + str(R.id))

                else:  # Show form to collect more details
                    if g['language'] == "":
                        request_language = langcode
                    else:
                        request_language = g['language']

                    pagetitle = g['pagetitle']
                    pageid = wiki.GetPageId(request_language, pagetitle)
                    content = {}
                    content['category_label'] = _('Categories')
                    content['wikiprojects_label'] = _('WikiProjects')
                    content['summary_label'] = _('Summary')
                    content['summary_explanation'] = _('Please provide a brief summary of your request.')

                    # Does the article exist? Two different workflows if so.
                    if pageid == None:  # new article workflow
                        pageid = 0
                        content['summary_inputbox'] = _('Create new article')
                        content['category_explanation'] = _('Enter one category per line. Case sensitive. Do not include "Category:".')
                        content['category_textarea'] = ''
                        content['wikiprojects_explanation'] = _('Enter one WikiProject per line. Case sensitive. Include "WikiProject" if it is in the name.')
                        content['wikiprojects_textarea'] = ''

                    else:  # existing article workflow
                        content['summary_inputbox'] = ''
                        content['category_explanation'] = _('Categories are retrieved automatically from Wikipedia.')
                        content['category_textarea'] = wiki.GetCategories(request_language, pageid)
                        content['wikiprojects_explanation'] = _('WikiProjects are retrieved automatically from Wikipedia. You may add additional projects if you wish.')
                        content['wikiprojects_textarea'] = wiki.GetWikiProjects(request_language, pagetitle)

                    content['note_label'] = _('Add a note')
                    content['note_explanation'] = _('Please expand on your request. It is recommended you include additional context and sources if you have any. You may use wikitext markup.')
                    content['submit_button'] = _('add_submit_button')

                    context = {
                                'interface': interface_messages(request, langcode),
                                'language': langcode,
                                'content': content,
                                'request_language': request_language,
                                'pagetitle': pagetitle,
                                'pageid': pageid
                              }

                    return render(request, 'requestoid/add_details.html', context = context)

        # Default behavior for no pagetitle specified
        content = {
                    'headline': _('add_start_headline'),
                    'inputlabel': _('add_start_input_label'),
                    'explanation': _('add_start_explanation'),
                    'button': _('add_start_button_label')
                  }

        context = {
                    'interface': interface_messages(request, langcode),
                    'language': langcode,
                    'content': content
                  }

        return render(request, 'requestoid/add_start.html', context = context)


def request(request, langcode, reqid):  # /requests/en/request/12345
    translation.use_language = langcode
    p = request.POST
    username = get_username(request)
    userid = wiki.GetUserId(username)
    # First, we determine if there are any POST requests to change the content.

    if 'changestatus' in p:
        if username != None:
            new_status = p['changestatus']
            status_index = {'open': 0, 'complete': 1, 'declined': 2}
            status_log_index = {'open': 'flagopen', 'complete': 'flagcomplete', 'declined': 'flagdecline'}

            R = models.Requests.objects.get(id=reqid)
            R.status = status_index[new_status]
            R.save()

            log = models.Logs(request = R,
                              user_name = username,
                              user_id = userid,
                              timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                              action = status_log_index[new_status],
                              reference = R.id)
            log.save()

    if 'categories' in p:
        R = models.Requests.objects.get(id=reqid)
        if username != None and R.page_id == 0:
            C = models.Categories.objects.filter(request_id=reqid)
            old_categories = [x.cat_title for x in C]
            new_categories = [x for x in p['categories'].split("\r\n") if x != '' and x != ' ']
            normalized_new_categories = []
            for category in new_categories:
                if category[:9] == "Category:":
                    normalized_new_categories.append(category[9:])
                else:
                    normalized_new_categories.append(category)
            new_categories = normalized_new_categories

            taken_out = list(set(old_categories) - set(new_categories))
            added_in = list(set(new_categories) - set(old_categories))

            for category in taken_out:
                query = models.Categories.objects.filter(cat_title=category, request_id=reqid)
                for C in query:  # The above returns a QuerySet; doing it this way in case there's >1 result

                    log = models.Logs(request = R,
                                      user_name = username,
                                      user_id = userid,
                                      timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                                      action = 'delcategory',
                                      reference = C.id,
                                      reference_text = category)
                    log.save()

                    C.delete()

            for category in added_in:
                    C = models.Categories(request = R,
                                          cat_title = category,
                                          cat_id = wiki.GetCategoryId(R.wiki[:-4], category),
                                          wiki = R.wiki)

                    C.save()

                    log = models.Logs(request = R,
                                      user_name = username,
                                      user_id = userid,
                                      timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                                      action = 'addcategory',
                                      reference = C.id)
                    log.save()

    if 'wikiprojects' in p:
        R = models.Requests.objects.get(id=reqid)
        if username != None:
            W = models.WikiProjects.objects.filter(request_id=reqid)
            old_wikiprojects = [x.project_title for x in W]
            new_wikiprojects = [x for x in p['wikiprojects'].split("\r\n") if x != '' and x != ' ']
            normalized_new_wikiprojects = []
            for wikiproject in new_wikiprojects:
                if wikiproject[:10] == "Wikipedia:":
                    normalized_new_wikiprojects.append(wikiproject[10:])
                else:
                    normalized_new_wikiprojects.append(wikiproject)
            new_wikiprojects = normalized_new_wikiprojects

            taken_out = list(set(old_wikiprojects) - set(new_wikiprojects))
            added_in = list(set(new_wikiprojects) - set(old_wikiprojects))

            for wikiproject in taken_out:
                query = models.WikiProjects.objects.filter(project_title=wikiproject, request_id=reqid)
                for W in query:  # The above returns a QuerySet; doing it this way in case there's >1 result

                    log = models.Logs(request = R,
                                      user_name = username,
                                      user_id = userid,
                                      timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                                      action = 'delwikiproject',
                                      reference = W.id,
                                      reference_text = wikiproject)
                    log.save()

                    W.delete()

            for wikiproject in added_in:
                    W = models.WikiProjects(request = R,
                                            project_title = wikiproject,
                                            project_id = wiki.GetWikiProjectId(R.wiki[:-4], wikiproject),
                                            wiki = R.wiki)

                    W.save()

                    log = models.Logs(request = R,
                                      user_name = username,
                                      user_id = userid,
                                      timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                                      action = 'addwikiproject',
                                      reference = W.id)
                    log.save()

    if 'newnote' in p:
        if username != None and p['newnote'] != '' and p['newnote'] != ' ' and p['newnote'] != '\r\n':
            R = models.Requests.objects.get(id=reqid)
            N = models.Notes(request = R,
                             user_name = username,
                             user_id = userid,
                             timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                             comment = p['newnote'])
            N.save()
    
            log = models.Logs(request = R,
                              user_name = username,
                              user_id = userid,
                              timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                              action = 'addnote',
                              reference = N.id)
            log.save()

    # With any changes now processed, we can load the page.

    translation.use_language = langcode
    R = get_object_or_404(models.Requests, id=reqid)

    status = ['Open', 'Complete', 'Declined']  # 0 = open; 1 = complete; 2 = declined

    requestdata = {'id': reqid,
                   'page_title': R.page_title,
                   'page_id': R.page_id,
                   'user_name': R.user_name,
                   'wiki': R.wiki,
                   'summary': R.summary,
                   'status': R.status,
                   'status_verbose': _(status[R.status]),
                   'notes': [],
                   'categories': [],
                   'wikiprojects': []}


    N = models.Notes.objects.filter(request_id=reqid).order_by('timestamp')
    C = models.Categories.objects.filter(request_id=reqid).order_by('cat_title')
    W = models.WikiProjects.objects.filter(request_id=reqid).order_by('project_title')

    for note in N:
        noteblock = {'username': note.user_name,
                     'timestamp': arrow.get(note.timestamp, 'YYYYMMDDHHmmss').format('YYYY-MM-DD | HH:mm:ss'),
                     'comment': wiki.WikitextRender(R.wiki[:-4], note.comment)}

        requestdata['notes'].append(noteblock)

    for category in C:
        requestdata['categories'].append(category.cat_title)

    for wikiproject in W:
        requestdata['wikiprojects'].append(wikiproject.project_title)

    content = {'categories_label': _('Categories'),
               'wikiprojects_label': _('WikiProjects'),
               'nothing_here_yet': _('Nothing here yet...'),
               'save_label': _('Save'),
               'edit_categories_on_wikipedia_label': _('Categories must be changed directly on Wikipedia'),
               'requestdata': requestdata
              }

    if username == None:
        content['list_edit_explanation'] = _('You need to be logged in to edit this list')
    else:
        content['list_edit_explanation'] = _('Click this list to edit it')
        content['mark_as_complete_label'] = _('Mark as Complete')
        content['mark_as_declined_label'] = _('Mark as Declined')
        content['mark_as_open_label'] = _('Mark as Open')
        content['add_a_note_label'] = _('Add a note')
        content['add_button'] = _('Add')
        content['add_a_note_explanation'] = _('Add a note explanation')

    context = {
                'interface': interface_messages(request, langcode),
                'language': langcode,
                'content': content
              }
    return render(request, 'requestoid/request.html', context = context)


def log(request, langcode):  # /requests/en/log
    translation.use_language = langcode
    L = models.Logs.objects.all().order_by('-timestamp')

    context = {
                'interface': interface_messages(request, langcode),
                'language': langcode,
                'headline': _('Log'),
                'content': L
              }
    return render(request, 'requestoid/log.html', context = context)


def search(request, langcode):  # /requests/en/search
    translation.use_language = langcode
    g = request.GET
    if 'searchterm' in g:
        if g['searchterm'] != '' and g['searchterm'] != ' ':
            searchterm = g['searchterm']
            database = g['language'] + 'wiki'
            searchterm = searchterm.replace('_', ' ')
            searchtype = g['searchtype']

            if searchtype == 'article':
                searchterm = wiki.RedirectResolver(g['language'], searchterm, 0)
                R = models.Requests.objects.filter(page_title=searchterm, wiki=database, status=0)
            elif searchtype == 'category':
                if searchterm[:9] == 'Category:':
                    searchterm = searchterm[9:]
                C = models.Categories.objects.filter(cat_title=searchterm, wiki=database, request__status=0)
                R = [entry.request for entry in C]
            elif searchtype == 'wikiproject':
                if searchterm[:10] == 'Wikipedia:':
                    searchterm = searchterm[10:]
                elif searchterm[:3] == "WP:":
                    searchterm = searchterm[3:]
                searchterm = wiki.RedirectResolver(g['language'], searchterm, 4)
                W = models.WikiProjects.objects.filter(project_title=searchterm, wiki=database, request__status=0)
                R = [entry.request for entry in W]

            content = {'search_term': searchterm,
                       'search_type': _(searchtype[0].upper() + searchtype[1:]),
                       'search_data': R}

            context = {
                       'interface': interface_messages(request, langcode),
                       'language': langcode,
                       'content': content
                      }

            return render(request, 'requestoid/list_results.html', context = context)

    # get parameters: language, searchterm, searchtype

    content = {'headline': _('Search'),
               'article_label': _('Article'),
               'category_label': _('Category'),
               'wikiproject_label': _('WikiProject'),
               'go_label': _('Go')}
    context = {
                'interface': interface_messages(request, langcode),
                'language': langcode,
                'content': content
              }
    return render(request, 'requestoid/list_start.html', context = context)


def help(request, langcode):  # /requests/en/help
    translation.use_language = langcode
    content = {'headline': _('Help'),
               'intro': _('help_body')}
    context = {
                'interface': interface_messages(request, langcode),
                'language': langcode,
                'content': content
              }
    return render(request, 'requestoid/help.html', context = context)


def about(request, langcode):  # /requests/en/about
    translation.use_language = langcode
    content = {'headline': _('About Wikipedia Requests'),
               'intro': _('about_body')}
    context = {
                'interface': interface_messages(request, langcode),
                'language': langcode,
                'content': content
              }
    return render(request, 'requestoid/help.html', context = context)


def bulk(request, langcode):  # /requests/en/import
    translation.use_language = langcode
    username = get_username(request)
    userid = wiki.GetUserId(username)
    p = request.POST  # `p` is short for `post`

    if username == None:
        return you_need_to_login(request, langcode)
    else:
        if 'submit' in p:  # request creation can take place
            # Defining default categories and WikiProjects and sanitizing them

            default_categories = []

            for category in p['categories'].split('\r\n'):
                if category == '' or category == ' ':
                    continue
                if category[:9] == 'Category:':
                    category = category[9:]  # truncate "Category:"
                default_categories.append(category)

            default_wikiprojects = []

            for wikiproject in p['wikiprojects'].split('\r\n'):
                if wikiproject == '' or wikiproject == ' ':
                    continue
                if wikiproject[:10] == 'Wikipedia:':
                    wikiproject = wikiproject[9:]  # truncate "Wikipedia:"
                default_wikiprojects.append(wikiproject)


            # Preparing dictionary of individual entries

            entries = {}

            for key in p.keys():
                if key.startswith('pagetitle'):
                    if key[9:] in entries:
                        entries[key[9:]]['pagetitle'] = p[key]
                    else:
                        entries[key[9:]] = {'pagetitle': p[key]}
                elif key.startswith('summary'):
                    if key[7:] in entries:
                        entries[key[7:]]['summary'] = p[key]
                    else:
                        entries[key[7:]] = {'summary': p[key]}
                elif key.startswith('note'):
                    if key[4:] in entries:
                        entries[key[4:]]['note'] = p[key]
                    else:
                        entries[key[4:]] = {'note': p[key]}

            # Creating entries

            now = arrow.utcnow().format('YYYYMMDDHHmmss')
            userid = wiki.GetUserId(username)

            new_requests = []

            for entry in entries.values():

                pageid = wiki.GetPageId(p['request_language'], entry['pagetitle'])
                if pageid == None:
                    pageid = 0

                # Creating request
                R = models.Requests(page_id = pageid,
                                    page_title = entry['pagetitle'],
                                    user_id = userid,
                                    user_name = username,
                                    wiki = p['request_language'] + wiki,
                                    timestamp = now,
                                    summary = entry['summary'],
                                    status = 0)
                R.save()

                new_requests.append(R.id)

                # First log entry: saying the request is created
                log = models.Logs(request = R,
                                  user_name = username,
                                  user_id = userid,
                                  timestamp = now,
                                  action = 'create',
                                  reference = R.id)
                log.save()

                # Next log entry: flagging it as open
                log = models.Logs(request = R,
                                  user_name = username,
                                  user_id = userid,
                                  timestamp = now,
                                  action = 'flagopen',
                                  reference = R.id)
                log.save()

                # Recording note
                N = models.Notes(request = R,
                                 user_name = username,
                                 user_id = userid,
                                 timestamp = now,
                                 comment = entry['note'])
                N.save()

                # And a log entry stating note was left
                log = models.Logs(request = R,
                                  user_name = username,
                                  user_id = userid,
                                  timestamp = now,
                                  action = 'addnote',
                                  reference = N.id)
                log.save()


                if pageid == 0:
                    for category in default_categories:
                        C = models.Categories(request = R,
                                              cat_id = wiki.GetCategoryId(p['request_language'], category),
                                              cat_title = category,
                                              wiki = p['request_language'] + 'wiki')
                        C.save()
                        log = models.Logs(request = R,
                                          user_name = username,
                                          user_id = userid,
                                          timestamp = now,
                                          action = 'addcategory',
                                          reference = C.id)
                        log.save()

                else:
                    categories = wiki.GetCategories(p['request_language'], pageid)
                    for category in categories:
                        C = models.Categories(request = R,
                                              cat_id = wiki.GetCategoryId(p['request_language'], category),
                                              cat_title = category,
                                              wiki = p['request_language'] + 'wiki')
                        C.save()
                        log = models.Logs(request = R,
                                          user_name = username,
                                          user_id = userid,
                                          timestamp = now,
                                          action = 'addcategory',
                                          reference = C.id)
                        log.save()


                if pageid == 0:
                    wikiprojects = default_wikiprojects
                else:
                    wikiprojects = list(set(default_wikiprojects + wiki.GetWikiProjects(p['request_language'], pagetitle)))

                for wikiproject in wikiprojects:
                    W = models.WikiProjects(request = R,
                                            project_id = wiki.GetWikiProjectId(p['request_language'], wikiproject),
                                            project_title = wikiproject,
                                            wiki = p['request_language'] + 'wiki')
                    W.save()

                    log = models.Logs(request = R,
                                      user_name = username,
                                      user_id = userid,
                                      timestamp = now,
                                      action = 'addwikiproject',
                                      reference = W.id)
                    log.save()

            content = {'new_requests': new_requests}
            context = {
                        'interface': interface_messages(request, langcode),
                        'language': langcode,
                        'content': content
                      }

            return render(request, 'requestoid/bulk_result.html', context = context)

        else:  # render form
            content = {'headline': _('Bulk Import'),
                       'submit_button': _('Save'),
                       'page_title_label': _('add_start_input_label'),
                       'summary_label': _('Summary'),
                       'add_a_note': _('Add a note'),
                       'add_button': _('Add'),
                       'categories_label': _('Categories'),
                       'categories_placeholder': _('Bulk categories placeholder'),
                       'wikiprojects_label': _('WikiProjects'),
                       'divider1': _('All Requests'),
                       'divider2': _('Per Request'),
                       'remove_button': _('Remove'),
                       'language_label': _('Language')}
            context = {
                        'interface': interface_messages(request, langcode),
                        'language': langcode,
                        'content': content
                      }
            return render(request, 'requestoid/bulk_start.html', context = context)
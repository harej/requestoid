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
    p = request.POST
    username = get_username(request)
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
                              user_id = wiki.GetUserId(username),
                              timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                              action = status_log_index[new_status],
                              reference = R.id)
            log.save()


    translation.use_language = langcode
    R = get_object_or_404(models.Requests, id=reqid)

    status = ['Open', 'Complete', 'Declined']  # 0 = open; 1 = complete; 2 = declined

    requestdata = {'id': reqid,
                   'page_title': R.page_title,
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
                     'timestamp': arrow.get(note.timestamp, 'YYYYMMDDHHmmss').format('YYYY-MM-DD HH:mm:ss'),
                     'comment': wiki.WikitextRender(R.wiki[:-4], note.comment)}

        requestdata['notes'].append(noteblock)

    for category in C:
        requestdata['categories'].append(category.cat_title)

    for wikiproject in W:
        requestdata['wikiprojects'].append(wikiproject.project_title)

    content = {'notes_label': _('Notes'),
               'categories_label': _('Categories'),
               'wikiprojects_label': _('WikiProjects'),
               'mark_as_complete_label': _('Mark as Complete'),
               'mark_as_declined_label': _('Mark as Declined'),
               'mark_as_open_label': _('Mark as Open'),
               'nothing_here_yet': _('Nothing here yet...'),
               'requestdata': requestdata}
               
    if username == None:
        content['list_edit_explanation'] = _('You need to be logged in to edit this list')
    else:
        content['list_edit_explanation'] = _('Click this list to edit it')

    context = {
                'interface': interface_messages(request, langcode),
                'language': langcode,
                'content': content
              }
    return render(request, 'requestoid/request.html', context = context)
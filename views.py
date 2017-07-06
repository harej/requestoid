import arrow
import os
from . import authentication, models, transactions, wiki
from .worldly import Worldly
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from mwoauth import tokens

# Views! Views! Views, views, views, views, views views views views views views
# has a has a has a has a kind of mystery

cwd = os.path.dirname(os.path.realpath(__file__))
translation = Worldly(cwd + "/i18n.yaml")
_ = translation.render

def _interface_messages(request, langcode):
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
                'about': _('About'),
                'footer': _('Footer')
             }

    username = authentication.get_username(request)
    if username != None:
        output['username'] = username  # leave 'username' key unset if no session

    return output

def _create_page(request, langcode, content, template):
    context = {'interface': _interface_messages(request, langcode),
                'language': langcode,
                'content': content}
    return render(request, template, context = context)

def you_need_to_login(request, langcode):
    content = {'headline': _('Login required'),
               'explanation': _('login_required_message')}

    return _create_page(request, langcode, content, 'requestoid/error.html')

def select_language(request):  # /requests
    content = {'available':
                  [{'code': 'en', 'label': 'English'},
                   {'code': 'fi', 'label': 'suomi'},
                   {'code': 'sv', 'label': 'Svenska'},
                   {'code': 'zh-hant', 'label': '繁體中文'}]}

    return _create_page(request, 'en', content, 'requestoid/select_language.html')

def homepage(request, langcode):  # /requests/en
    translation.use_language = langcode

    content = {'headline': _('Help fill in the gaps on Wikipedia'),
               'intro': _('homepage_intro')}

    return _create_page(request, langcode, content, 'requestoid/homepage.html')


def auth(request):  # /requests/auth
    # This is the view called "auth," not a method that carries out authentication
    handshaker = authentication.requests_handshaker()
    redirect, request_token = handshaker.initiate()
    request.session['request_token_key'] = request_token.key.decode('utf-8')
    request.session['request_token_secret'] = request_token.secret.decode('utf-8')
    request.session['return_to'] = request.META['HTTP_REFERER']
    return HttpResponseRedirect(redirect)  # This hands the user off to Wikimedia; user returns to the website via the callback view which implements the session


def callback(request):  # /requests/callback
    oauth_verifier = request.GET['oauth_verifier']
    oauth_token = request.GET['oauth_token']
    handshaker = authentication.requests_handshaker()
    request_key = request.session['request_token_key'].encode('utf-8')
    request_secret = request.session['request_token_secret'].encode('utf-8')
    request_token = tokens.RequestToken(key=request_key, secret=request_secret)
    access_token = handshaker.complete(request_token, 'oauth_verifier=' + oauth_verifier + '&oauth_token=' + oauth_token)
    request.session['access_token_key'] = access_token.key.decode('utf-8')
    request.session['access_token_secret'] = access_token.secret.decode('utf-8')
    return HttpResponseRedirect(request.session['return_to'])


def add(request, langcode):  # /requests/en/add
    translation.use_language = langcode
    username = authentication.get_username(request)
    g = request.GET  # `g` is short for `get`
    p = request.POST  # `p` is short for `post`
    if username == None:
        return you_need_to_login(request, langcode)
    else:
        if 'pagetitle' in g:
            if g['pagetitle'] != "":
                if 'pageid' in p:  # Ready to save to database; pageid is only passed as a parameter if workflow below has been completed
                    userid = wiki.GetUserId(username)
                    categories = p['categories'].split('\r\n')
                    wikiprojects = p['wikiprojects'].split('\r\n')

                    R = transactions.NewEntry(
                        p['pageid'],
                        p['pagetitle'],
                        userid,
                        username,
                        p['request_language'] + 'wiki',
                        p['summary'],
                        p['note'],
                        categories,
                        wikiprojects,
                        p['request_language'])

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
                    content['summary_explanation'] = _('What is the goal? For example: create article, expand article, add sources...')

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

                    content['pagetitle'] = pagetitle
                    content['pageid'] = pageid
                    content['request_language'] = request_language

                    return _create_page(request, langcode, content, 'requestoid/add_details.html')

        # Default behavior for no pagetitle specified
        content = {'headline': _('add_start_headline'),
                   'inputlabel': _('add_start_input_label'),
                   'explanation': _('add_start_explanation'),
                   'button': _('add_start_button_label'),
                   'wiki_language': wiki.GetEquivalentWiki(langcode)}

        return _create_page(request, langcode, content, 'requestoid/add_start.html')

def request(request, langcode, reqid):  # /requests/en/request/12345
    translation.use_language = langcode
    p = request.POST
    username = authentication.get_username(request)
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
            transactions._post_log(R, status_log_index[new_status], R.id)

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
                    transactions._post_log(R, 'delcategory', C.id, category)
                    C.delete()

            for category in added_in:
                    transactions.AddCategory(R, R.wiki[:-4], category)

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
                    transactions._post_log(R, 'delwikiproject', W.id, wikiproject)
                    W.delete()

            for wikiproject in added_in:
                    transactions.AddWikiProject(R, R.wiki[:-4], wikiproject)

    if 'newnote' in p:
        if username != None and p['newnote'] != '' and p['newnote'] != ' ' and p['newnote'] != '\r\n':
            R = models.Requests.objects.get(id=reqid)
            transactions.AddNote(R, p['newnote'])

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

    return _create_page(request, langcode, content, 'requestoid/request.html')

def log(request, langcode):  # /requests/en/log
    translation.use_language = langcode
    L = models.Logs.objects.all().order_by('-timestamp')[:500]
    content = {'headline': _('Log'), 'content': L}
    return _create_page(request, langcode, content, 'requestoid/log.html')

def search(request, langcode):  # /requests/en/search
    translation.use_language = langcode
    g = request.GET
    if 'searchterm' in g:
        searchterm = g['searchterm'].replace('_', ' ')
        searchtype = g['searchtype']
        if searchterm != '' and searchterm != ' ':
            R = transactions.retrieve_requests(searchterm, searchtype, g['language'])

            content = {'search_term': searchterm,
                       'search_type': _(searchtype[0].upper() + searchtype[1:]),
                       'wiki_language': wiki.GetEquivalentWiki(langcode),
                       'search_count': len(R['open']),
                       'search_data': R['open'],
                       'complete_requests_count': len(R['complete']),
                       'complete_requests_label': _('complete_requests'),
                       'open_requests_label': _('open_requests')}

            return _create_page(request, langcode, content, 'requestoid/list_results.html')

    # get parameters: language, searchterm, searchtype

    content = {'headline': _('Search'),
               'article_label': _('Article'),
               'category_label': _('Category'),
               'wikiproject_label': _('WikiProject'),
               'go_label': _('Go'),
               'wiki_language': wiki.GetEquivalentWiki(langcode)}

    return _create_page(request, langcode, content, 'requestoid/list_start.html')

def help(request, langcode):  # /requests/en/help
    translation.use_language = langcode
    content = {'headline': _('Help'),
               'intro': _('help_body')}
    return _create_page(request, langcode, content, 'requestoid/help.html')

def about(request, langcode):  # /requests/en/about
    translation.use_language = langcode
    content = {'headline': _('About Wikipedia Requests'),
               'intro': _('about_body')}
    return _create_page(request, langcode, content, 'requestoid/help.html')

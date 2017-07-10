import arrow
from . import models, wiki

def _post_log(request, action, reference, reference_text=None, username=None, userid=None):
    if username == None:
        username = request.user_name

    if userid == None:
        userid = request.user_id

    log = models.Logs(request = request,
                      user_name = username,
                      user_id = userid,
                      timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                      action = action,
                      reference = reference,
                      reference_text = reference_text)
    log.save()

    return log

def retrieve_requests(searchterm, searchtype, language):
    database = language + 'wiki'
    if searchtype == 'article':
        searchterm = wiki.RedirectResolver(language, searchterm, 0)
        R = {
        'open': models.Requests.objects.filter(page_title=searchterm, wiki=database, status=0),
        'complete': models.Requests.objects.filter(page_title=searchterm, wiki=database, status=1)
        }
    elif searchtype == 'category':
        if searchterm[:9] == 'Category:':
            searchterm = searchterm[9:]
        C1 = models.Categories.objects.filter(cat_title=searchterm, wiki=database, request__status=0)
        R1 = [entry.request for entry in C1]
        C2 = models.Categories.objects.filter(cat_title=searchterm, wiki=database, request__status=1)
        R2 = [entry.request for entry in C2]
        R = {'open': R1, 'complete': R2}
    elif searchtype == 'wikiproject':
        if searchterm[:10] == 'Wikipedia:':
            searchterm = searchterm[10:]
        elif searchterm[:3] == "WP:":
            searchterm = searchterm[3:]
        searchterm = wiki.RedirectResolver(language, searchterm, 4)
        W1 = models.WikiProjects.objects.filter(project_title=searchterm, wiki=database, request__status=0)
        R1 = [entry.request for entry in W1]
        W2 = models.WikiProjects.objects.filter(project_title=searchterm, wiki=database, request__status=1)
        R2 = [entry.request for entry in W2]
        R = {'open': R1, 'complete': R2}

    return R

def create_request_entry(page_id, page_title, userid, username, wiki, summary):
    R = models.Requests(page_id = page_id,
                        page_title = page_title,
                        user_id = userid,
                        user_name = username,
                        wiki = wiki,
                        timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                        summary = summary,
                        status = 0)
    R.save()
    _post_log(R, 'create', R.id)
    _post_log(R, 'flagopen', R.id)
    return R

def add_note(request, content, username=None, userid=None):
    if username == None:
        username = request.user_name

    if userid == None:
        userid = request.user_id

    N = models.Notes(request = request,
                     user_name = request.user_name,
                     user_id = request.user_id,
                     timestamp = arrow.utcnow().format('YYYYMMDDHHmmss'),
                     comment = content)
    N.save()
    _post_log(request, 'addnote', N.id)
    return N

def add_category(request, request_language, category, username=None, userid=None):
    if username == None:
        username = request.user_name

    if userid == None:
        userid = request.user_id

    C = models.Categories(request = request,
                          cat_id = wiki.GetCategoryId(request_language, category),
                          cat_title = category,
                          wiki = request.wiki)
    C.save()
    _post_log(request, 'addcategory', C.id)
    return C

def add_wikiproject(request, request_language, wikiproject, username=None, userid=None):
    if username == None:
        username = request.user_name

    if userid == None:
        userid = request.user_id

    W = models.WikiProjects(request = request,
                            project_id = wiki.GetWikiProjectId(request_language, wikiproject),
                            project_title = wikiproject,
                            wiki = request_language + 'wiki')
    W.save()
    _post_log(request, 'addwikiproject', W.id)
    return W

def new_entry(page_id, page_title, userid, username, wiki, summary, note, categories, wikiprojects, request_language):
    R = create_request_entry(
            page_id,
            page_title,
            userid,
            username,
            wiki,
            summary)

    add_note(R, note)

    for category in categories:
        if category == '' or category == ' ':
            continue
        if category[:9] == 'Category:':
            category = category[9:]  # truncate "Category:"

        add_category(R, request_language, category)

    for wikiproject in wikiprojects:
        if wikiproject == '' or wikiproject == ' ':
            continue
        if wikiproject[:10] == 'Wikipedia:':
            wikiproject = wikiproject[10:]  # truncate "Wikipedia:"

        add_wikiproject(R, request_language, wikiproject)

    return R

def bulk_create(manifest):
    for entry in manifest:
        new_entry(entry['page_id'], entry['page_title'], entry['userid'],
                  entry['username'], entry['wiki'], entry['summary'])

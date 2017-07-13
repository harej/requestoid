import requests
from . import tool_labs_utils
from bs4 import BeautifulSoup

sql = tool_labs_utils


def CanonicalPageTitle(raw_input):
    output = raw_input.replace(' ', '_')
    output = output[0].upper() + output[1:]
    return output


def WikipediaQuery(language, sqlquery):
    return sql.WMFReplica().query(language + 'wiki', sqlquery, None)


def GetId(language, pagetitle, namespace):
    pagetitle = CanonicalPageTitle(pagetitle)
    q = 'select page_id from page where page_namespace = {0} and page_title = "{1}";'.format(
        namespace, pagetitle.replace('"', '\\"'))
    result = WikipediaQuery(language, q)
    if result == []:
        return 0
    else:
        return result[0][0]


def GetPageId(language, pagetitle):
    return GetId(language, pagetitle, 0)


def GetCategoryId(language, pagetitle):
    return GetId(language, pagetitle, 14)


def GetWikiProjectId(language, pagetitle):
    return GetId(language, pagetitle, 4)


def GetUserId(username):
    q = 'select gu_id from globaluser where gu_name = "{0}";'.format(username)
    return sql.WMFReplica().query('centralauth', q, None)[0][0]


def GetCategories(language, pageid):
    q = 'select cl_to from categorylinks where cl_from = {0};'.format(pageid)
    result = WikipediaQuery(language, q)
    if result == []:
        return ''
    else:
        output = ''
        for entry in result:
            output += entry[0].decode('utf-8').replace('_', ' ') + '\n'
        return output


def GetWikiProjects(language, pagetitle):
    pagetitle = CanonicalPageTitle(pagetitle)
    q = 'select pi_project from projectindex where pi_page = "{0}";'.format(
        'Talk:' + pagetitle)
    result = sql.ToolsDB().query('s52475__wpx_p', q, None)
    if result == []:
        return ''
    else:
        output = ''
        for entry in result:
            output += entry[0].replace('_', ' ').replace('Wikipedia:',
                                                         '') + '\n'
        return output


def WikitextRender(language, source):
    # https://en.wikipedia.org/w/api.php?action=parse&format=json&text=%5B%5Blol%5D%5D&contentmodel=wikitext
    url = 'https://{0}.wikipedia.org/w/api.php'.format(language)
    params = {
        'action': 'parse',
        'format': 'json',
        'contentmodel': 'wikitext',
        'text': source
    }
    r = requests.get(url, params=params)
    blob = r.json()
    html = blob['parse']['text']['*']

    # Now, we need to take "internal" links and make them actually point to Wikipedia

    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.findAll('a'):
        if a['href'][:6] == '/wiki/':
            a['href'] = a['href'].replace(
                '/wiki/', 'https://{0}.wikipedia.org/wiki/'.format(language))
        elif a['href'][:3] == '/w/':
            a['href'] = a['href'].replace(
                '/w/', 'https://{0}.wikipedia.org/w/'.format(language))

    return str(soup)


def RedirectResolver(language, pagetitle, namespace):
    normalized_pagetitle = CanonicalPageTitle(pagetitle)
    q = 'select rd_title from redirect left join page on page_id = rd_from where page_title = "{0}" and page_namespace={1};'.format(
        normalized_pagetitle, namespace)
    result = WikipediaQuery(language, q)
    if result == []:
        return pagetitle
    else:
        return result[0][0].decode('utf-8').replace('_', ' ')


def GetEquivalentWiki(langcode):
    return {'zh-hant': 'zh'}.get(langcode, langcode)

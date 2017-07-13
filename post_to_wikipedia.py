import os
import sys
import django
sys.path.append("/var/www/django-src/requestoid")
os.environ["DJANGO_SETTINGS_MODULE"] = "requestoid.settings"
django.setup()

import pywikibot
import mwparserfromhell
from requestoid import views, wiki

already_done = []


def page_constructor(bot, language, fieldtype, fieldvalue):
    # Construct template page titles (e.g. Template:Wikipedia Requests/Article/Barack Obama)

    report_page_title = 'Template:Wikipedia_Requests/' + fieldtype[0].upper(
    ) + fieldtype[1:].replace('ikiproject', 'ikiProject') + '/'
    if fieldtype == 'article':
        report_page_title += fieldvalue
    elif fieldtype == 'category':
        if fieldvalue[:9] == 'Category:':
            report_page_title += fieldvalue[9:]
        else:
            report_page_title += fieldvalue
    elif fieldtype == 'wikiproject':
        if fieldvalue[:10] == 'Wikipedia:':
            report_page_title += fieldvalue[10:]
        else:
            report_page_title += fieldvalue

    if report_page_title not in already_done:  # no need to do the same report twice
        # Do the lookup
        R = views.retrieve_requests(
            fieldvalue.replace('_', ' '), fieldtype, language)

        # Construct the page (or say, No requests)
        report_page_contents = "'''{0}''' total open requests • '''{1}''' total completed requests\n".format(
            len(R['open']), len(R['complete']))
        format_string = '* [[{0}]]: {1} ([https://wpx.wmflabs.org/requests/{2}/request/{3} view request details])\n'
        counter = 0
        for req in R['open']:
            if counter == 10:  # no more than 10 in a posting
                break
            report_page_contents += format_string.format(
                req.page_title, req.summary, language, req.id)
            counter += 1

        # Save
        page = pywikibot.Page(bot, report_page_title)
        page.text = report_page_contents
        page.save(
            "Updating list of requests", minor=False, async=True, quiet=True)

        already_done.append(report_page_title)


def main(language):
    bot = pywikibot.Site('en', 'wikipedia')

    # Get list of transclusions of {{Wikipedia Requests}}

    q = 'select page_namespace, page_title from templatelinks join page on page_id = tl_from where tl_namespace = 10 and tl_title = "Wikipedia_Requests";'
    transclusions = [(x[0], x[1].decode('utf-8'))
                     for x in wiki.WikipediaQuery(language, q)]  # page IDs

    # Find the pages; parse using MWPH (remember: a page may have more than one instance of the template)

    ns = {
        1: 'Talk:',
        2: 'User:',
        3: 'User_talk:',
        4: 'Wikipedia:',
        5: 'Wikipedia_talk:',
        10: 'Template:',
        11: 'Template_talk:',
        12: 'Help:',
        13: 'Help_talk:',
        14: 'Category:',
        15: 'Category_talk:',
        100: 'Portal:',
        101: 'Portal_talk:',
        119: 'Draft_talk:',
        446: 'Education_Program:',
        447: 'Education_Program_talk:',
        2600: 'Topic'
    }

    for pair in transclusions:
        page_title = ns[pair[0]] + pair[1]
        page = pywikibot.Page(bot, page_title)
        wikitext = mwparserfromhell.parse(page.text)
        for template in wikitext.filter_templates():
            if template.name.matches('Wikipedia Requests'):
                if template.has('article'):
                    page_constructor(bot, language, 'article',
                                     str(template.get('article').value))

                elif template.has('category'):
                    page_constructor(bot, language, 'category',
                                     str(template.get('category').value))

                elif template.has('wikiproject'):
                    page_constructor(bot, language, 'wikiproject',
                                     str(template.get('wikiproject').value))


if __name__ == "__main__":
    main('en')

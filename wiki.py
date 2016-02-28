from . import tool_labs_utils

sql = tool_labs_utils

def CanonicalPageTitle(raw_input):
	output = raw_input.replace(' ', '_')
	output = output[0].upper() + output[1:]
	return output

def WikipediaQuery(language, sqlquery):
	return sql.WMFReplica.query(language + 'wiki', sqlquery, None)

def GetPageId(language, pagetitle):
	pagetitle = CanonicalPageTitle(pagetitle)
	q = 'select page_id from page where page_namespace = 0 and page_title = "{0}";'.format(pagetitle)
	result = WikipediaQuery(language, q)
	if result == None:
		return None
	else:
		return result[0][0]

def GetCategories(language, pageid):
	q = 'select cl_to from categorylinks where cl_from = {0};'.format(pageid)
	result = WikipediaQuery(language, q)
	if result == None:
		return ''
	else:
		output = ''
		for entry in result[0]:
			output += entry.replace('_', ' ') + '\n'
		return output

def GetWikiProjects(language, pagetitle):
	pagetitle = CanonicalPageTitle(pagetitle)
	q = 'select pi_project from projectindex where pi_page = "{0}";'.format('Talk:' + pagetitle)
	result = sql.ToolsDB().query('s52475__wpx', q, None)
	if result == None:
		return ''
	else:
		output = ''
		for entry in result[0]:
			output += entry.replace('_', ' ').replace('Wikipedia:', '')
		return output
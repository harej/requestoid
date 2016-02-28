# -*- coding: utf-8 -*-
"""
Generic utility for querying a database on Tool Labs
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import pymysql


class ToolLabs:
    def mysql(self, host, db, sqlquery, values):
        """Generic wrapper for carrying out MySQL queries"""

        conn = pymysql.connect(host=host, port=3306, db=db, read_default_file='.sql.ini', charset='utf8')
        cur = conn.cursor()
        cur.execute(sqlquery, values)
        data = []
        for row in cur:
            data.append(row)
        conn.commit()
        return data

class WMFReplica:
    def query(self, db, sqlquery, values):
        """Queries for WMF wiki database replicas on Labs (e.g. enwiki)"""
        self.host = db + '.labsdb'
        self.database = db + '_p'
        self.sqlquery = sqlquery
        self.values = values
        return ToolLabs().mysql(self.host, self.database, self.sqlquery, self.values)

class ToolsDB:
    def query(self, db, sqlquery, values):
        """Queries a Tool Labs database"""
        return ToolLabs().mysql('tools-db', db, sqlquery, values)
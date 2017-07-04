# -*- coding: utf-8 -*-
"""
Generic utility for querying a database on Tool Labs
Copyright (C) 2015-2017 James Hare
Licensed under MIT License: https://mitlicense.org
"""

from . import config
import pymysql
import os

cwd = os.path.dirname(os.path.realpath(__file__))

class ToolLabs:
    def mysql(self, host, user, password, db, sqlquery, values, port):
        """Generic wrapper for carrying out MySQL queries"""

        conn = pymysql.connect(
            host=host, port=port, db=db, user=user, password=password,
            charset='utf8')
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
        self.host = config.SQL_WMF_REPLICA_ADDRESS.format(db)
        self.database = db + '_p'
        self.sqlquery = sqlquery
        self.values = values
        self.port = config.SQL_WMF_REPLICA_PORT
        return ToolLabs().mysql(
            self.host, config.SQL_USER, config.SQL_PASSWORD, self.database,
            self.sqlquery, self.values, self.port)

class ToolsDB:
    def query(self, db, sqlquery, values):
        """Queries a Tool Labs database"""
        return ToolLabs().mysql(
            config.SQL_TOOLSDB_ADDRESS, config.SQL_USER, config.SQL_PASSWORD,
            db, sqlquery, values, config.SQL_TOOLSDB_PORT)

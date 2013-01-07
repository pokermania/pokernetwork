# -*- coding: utf-8 *-*

import MySQLdb as _my
import warnings
import os
from contextlib import closing

def query(_query, _args=None, user=None, password=None, host=None, port=3306, database=None):
    kw = {'db':database} if database else {}
    with closing(_my.connect(user=user, passwd=password, host=host, port=port, **kw)) as db:
        with closing(db.cursor()) as c:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", Warning)
                c.execute(_query, _args)
            return c.fetchall()

def setup_db(schema, _queries=[], user=None, password=None, host=None, port=3306, database=None):
    with closing(_my.connect(user=user, passwd=password, host=host, port=port)) as db:
        db.query("DROP DATABASE IF EXISTS `%s`" % (database,))
        db.query("CREATE DATABASE `%s`" % (database,))
        
    with closing(_my.connect(user=user, passwd=password, host=host, port=port, db=database)) as db:
        db.autocommit(True)

        os.system("mysql -u '%s'%s%s%s '%s' < %s" % (
            user,
            " -p'%s'" % password if password else '',
            " -h '%s'" % host if host else '',
            " -P %s" % port if port else '',
            database,
            schema
        ))

        with closing(db.cursor()) as c:
            for q, a in _queries:
                if type(a) in (list, tuple) and len(a) > 0:
                    for args in a:
                        try: c.execute(q, args)
                        except: print q,"\n    ", args
                else:
                    c.execute(q)

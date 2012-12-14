# -*- coding: utf-8 *-*

import MySQLdb as _my
import warnings
import os

def query(_query, _args=None, user=None, password=None, host=None, port=3306, database=None):
    if database:
        db = _my.connect(user=user, passwd=password, host=host, port=port, db=database)
    else:
        db = _my.connect(user=user, passwd=password, host=host, port=port)
    try:
        c = db.cursor()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", Warning)
                c.execute(_query, _args)
            return c.fetchall()
        finally:
            c.close()
    finally:
        db.close()

def setup_db(schema, _querys=[], user=None, password=None, host=None, port=3306, database=None):
    db = _my.connect(user=user, passwd=password, host=host, port=port)
    try:
        db.query("DROP DATABASE IF EXISTS `%s`" % (database,))
        db.query("CREATE DATABASE `%s`" % (database,))
    finally:
        db.close()
    db = _my.connect(user=user, passwd=password, host=host, port=port, db=database)
    try:
        db.autocommit(True)

        os.system("mysql -u '%s'%s%s%s '%s' < %s" % (
            user,
            " -p'%s'" % password if password else '',
            " -h '%s'" % host if host else '',
            " -P %s" % port if port else '',
            database,
            schema
        ))

        c = db.cursor()
        try:
            for q, a in _querys:
                if type(a) in (list, tuple) and len(a) > 0:
                    for args in a:
                        try:
                            c.execute(q, args)
                        except:
                            print q,"\n    ", args
                else:
                    c.execute(q)
        finally:
            c.close()
    finally:
        db.close()

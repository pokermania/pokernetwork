# -*- coding: utf-8 *-*

import MySQLdb as _my
import warnings

def query(_query, _args=(), user=None, password=None, host=None, port=3306, database=None):
    if database:
        _c = _my.connect(user=user, passwd=password, host=host, port=port, db=database)
    else:
        _c = _my.connect(user=user, passwd=password, host=host, port=port)

    cursor = _c.cursor()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Warning)
            cursor.execute(_query, _args)
        return cursor.fetchall()
    finally:
        cursor.close()
        _c.close()

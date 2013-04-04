#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, stat
from stat import S_IRWXU, S_IRWXG, S_IROTH, S_IXOTH
from glob import glob
from distutils.core import setup

from distutils.command.build import build as DistutilsBuild

class ExtendedBuild(DistutilsBuild):
    
    def run(self):
        os.system("python setup.py configure -b")
        for f in EXECUTABLES:
            os.chmod(f, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH)
        DistutilsBuild.run(self)

EXECUTABLES = [
    'database/pokerdatabaseupgrade',
    'pokernetwork/pokerserver',
    'pokernetwork/pokerbot'
]

setup(
    name='poker-network',
    version='2.3.0',
    packages=[
        'pokernetwork',
        'pokernetwork.util'
    ],
    package_data={'pokernetwork': ['../twisted/plugins/*.py']},
    data_files=[
        ('bin', EXECUTABLES),
        ('share/poker-network/database', glob('database/*.sql')),
        ('share/poker-network/conf', ['conf/poker.server.xml', 'conf/poker.bot.xml', 'conf/poker.pem', 'conf/badwords.txt', 'conf/poker.pem']),
        ('share/man/man8', [
            'pokernetwork/pokerserver.8',
            'pokernetwork/pokerbot.8',
            'database/pokerdatabaseupgrade.8'
        ]),
        ('share/man/man5', ['database/pokerdatabase.5'])
    ],
    cmdclass={'build': ExtendedBuild}
)


#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os
sys.path.append('../common')
from distutils.core import setup
from setup_ext.test import TestCommand
from setup_ext.configure import ConfigureCommand

from distutils.command.build import build as DistutilsBuild

class ExtendedBuild(DistutilsBuild):
    
    def run(self):
        DistutilsBuild.run(self)
#        os.system("make -C po all")
#        os.system("make -C conf buildconf")

setup(
    name = 'poker-network',
    version = '2.2.0',
    packages = ['pokernetwork', 'twisted/plugins'],
    cmdclass = {
    	'test': TestCommand,
    	'configure': ConfigureCommand,
    	'build': ExtendedBuild
    }
)


#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name = 'poker-network',
    version = '2.1.5',
    packages = [
        'pokernetwork',
        'pokeradditions',
    ],
    test_suite='tests.all_tests',
)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Jason Davies
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name = 'Cozy-CouchDB-FUSE',
    version = '0.1',
    description = 'CouchDB FUSE module',
    long_description = \
"""This is a Python FUSE module for CouchDB.  It allows CouchDB document
attachments to be mounted on a virtual filesystem and edited directly.""",
    url = 'https://github.com/poupotte/couchdb-fuse',
    zip_safe = True,

    py_modules = ['src/cozy_files'],

    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database :: Front-Ends',
    ],

    entry_points = {
        'console_scripts': [
            'cozy_files = cozy_files:main',
        ],
    },    
    depends = 'python-gtk2, python-glade2',

    install_requires = [
    'fuse-python>=0.2', 
    'CouchDB>=0.9', 
    'requests>=2.0.1'
    ]
)

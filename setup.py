#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of GooCalendar.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

import io
import os
import re
from setuptools import setup, find_packages


def read(fname):
    return io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()


def get_version():
    init = read(os.path.join('goocalendar', '__init__.py'))
    return re.search("__version__ = '([0-9.]*)'", init).group(1)


setup(name='GooCalendar',
    version=get_version(),
    author='Cédric Krier',
    author_email='cedric.krier@b2ck.com',
    url='https://goocalendar.tryton.org/',
    description='A calendar widget for GTK using PyGoocanvas',
    long_description=read('README'),
    packages=find_packages(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Widget Sets',
        ],
    license='GPL-2',
    python_requires='>=3.4',
    )

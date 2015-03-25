# -*- coding: utf-8 -*-
"""
Setup twisted_event_dispatcher
"""
from setuptools import setup, find_packages

setup(
    name='twisted_event_dispatcher',
    author='Chris Scutcher',
    author_email='cscutche@cisco.com',
    url='https://github.com/cscutcher/twisted_event_dispatcher',
    version='0.1',
    packages=find_packages(),
    install_requires=('twisted', 'zope.interface', 'mock'),
    namespace_packages = ['oni'],
    description='Experimental generic event dispatcher written for twisted.'
)

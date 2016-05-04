#!/usr/bin/env python

from distutils.core import setup

setup(name='hawkular-client',
      version='0.4.0',
      description='Python client to communicate with Hawkular over HTTP(S)',
      author='Michael Burman',
      author_email='miburman@redhat.com',
      url='http://github.com/hawkular/hawkular-client-python',
      packages=['hawkular']
      )

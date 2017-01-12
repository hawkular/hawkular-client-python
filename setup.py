#!/usr/bin/env python

from distutils.core import setup
from os import path
from setuptools.command.install import install

here = path.abspath(path.dirname(__file__))

# Create rst here from Markdown
if path.exists(path.join(here, 'README.md')):
    import pypandoc
    z = pypandoc.convert('README.md','rst',format='markdown')
    with open('README.rst','w') as outfile:
        outfile.write(z)

with open(path.join(here, 'README.rst')) as f:
    long_description = f.read()

    
setup(name='hawkular-client',
      version='0.5.0',
      description='Python client to communicate with Hawkular server over HTTP(S)',
      author='Michael Burman',
      author_email='miburman@redhat.com',
      license='Apache License 2.0',
      url='http://github.com/hawkular/hawkular-client-python',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Topic :: System :: Monitoring',
      ],
      packages=['hawkular']
      )

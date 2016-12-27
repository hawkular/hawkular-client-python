import os

version = os.environ.get('HAWKULAR_VERSION','latest')

if version != 'latest':
    major_version, minor_version = version.split('.')
    major_version = int(major_version)
    minor_version = int(minor_version)
else:
    major_version = minor_version = 0
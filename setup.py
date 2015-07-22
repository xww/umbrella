#!/usr/bin/python
# Copyright (c) 2010 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import setuptools

from umbrella.common import setup
from umbrella.version import version_info as version

requires = setup.parse_requirements()
depend_links = setup.parse_dependency_links()

setuptools.setup(
    name='umbrella',
    version=version.canonical_version_string(always=True),
    description='The umbrella project provides services for administrator '
                'action, statistics for platform',
    license='Apache License (2.0)',
    author='hzzhoushaoyu',
    author_email='openstack@lists.launchpad.net',
    url='',
    packages=setuptools.find_packages(exclude=['bin']),
    test_suite='nose.collector',
    cmdclass=setup.get_cmdclass(),
    include_package_data=True,
    install_requires=requires,
    dependency_links=depend_links,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Environment :: No Input/Output (Daemon)',
    ],
    scripts=['bin/umbrella-api',
             'bin/umbrella-manage'],
    py_modules=[])

#!/usr/bin/env python
#
# Copyright (c) 2008-2011 by Enthought, Inc.
# All rights reserved.

"""
Extensible Application Framework

Envisage is a Python-based framework for building extensible applications,
that is, applications whose functionality can be extended by adding "plug-ins".
Envisage provides a standard mechanism for features to be added to an
application, whether by the original developer or by someone else. In fact,
when you build an application using Envisage, the entire application consists
primarily of plug-ins. In this respect, it is similar to the Eclipse and
Netbeans frameworks for Java applications.

Each plug-in is able to:

- Advertise where and how it can be extended (its "extension points").
- Contribute extensions to the extension points offered by other plug-ins.
- Create and share the objects that perform the real work of the application
  ("services").

The Envisage project provides the basic machinery of the Envisage
framework. This project contains no plug-ins. You are free to use:

- plug-ins from the EnvisagePlugins project
- plug-ins from other ETS projects that expose their functionality as plug-ins
- plug-ins that you create yourself

Prerequisites
-------------
If you want to build Envisage from source, you must first install
`setuptools <http://pypi.python.org/pypi/setuptools/0.6c8>`_.

"""

from setuptools import setup, find_packages

# This works around a setuptools bug which gets setup_data.py metadata
# from incorrect packages.
setup_data = dict(__name__='', __file__='setup_data.py')
execfile('setup_data.py', setup_data)
INFO = setup_data['INFO']


# Pull the description values for the setup keywords from our file docstring.
DOCLINES = __doc__.split("\n")

# The actual setup function call.
setup(
    author = "Martin Chilvers, et. al.",
    author_email = "info@enthought.com",
    download_url = ('http://www.enthought.com/repo/ets/envisage-%s.tar.gz' %
                    INFO['version']),
    classifiers = [c.strip() for c in """\
        Development Status :: 5 - Production/Stable
        Intended Audience :: Developers
        Intended Audience :: Science/Research
        License :: OSI Approved :: BSD License
        Operating System :: MacOS
        Operating System :: Microsoft :: Windows
        Operating System :: OS Independent
        Operating System :: POSIX
        Operating System :: Unix
        Programming Language :: Python
        Topic :: Scientific/Engineering
        Topic :: Software Development
        Topic :: Software Development :: Libraries
        """.splitlines() if len(c.strip()) > 0],
    description = DOCLINES[1],
    entry_points = """
        [envisage.plugins]
        envisage.core = envisage.core_plugin:CorePlugin
        """,
    ext_modules = [],
    include_package_data = True,
    install_requires = INFO['install_requires'],
    license = "BSD",
    long_description = '\n'.join(DOCLINES[3:]),
    maintainer = 'ETS Developers',
    maintainer_email = 'enthought-dev@enthought.com',
    name = "envisage",
    packages = find_packages(),
    platforms = ["Windows", "Linux", "Mac OS-X", "Unix", "Solaris"],
    tests_require = [
        'nose >= 0.10.3',
        ],
    test_suite = 'nose.collector',
    url = "http://code.enthought.com/projects/envisage/",
    version = INFO['version'],
    zip_safe = False,
)

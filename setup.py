import os, zipfile
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from distutils.command.build import build as distbuild
from distutils import log
from pkg_resources import DistributionNotFound, parse_version, require, VersionConflict 

from setup_data import INFO
from make_docs import HtmlBuild 

# Function to convert simple ETS project names and versions to a requirements
# spec that works for both development builds and stable builds.  Allows
# a caller to specify a max version, which is intended to work along with
# Enthought's standard versioning scheme -- see the following write up:
#    https://svn.enthought.com/enthought/wiki/EnthoughtVersionNumbers
def etsdep(p, min, max=None, literal=False):
    require = '%s >=%s.dev' % (p, min)
    if max is not None:
        if literal is False:
            require = '%s, <%s.a' % (require, max)
        else:
            require = '%s, <%s' % (require, max)
    return require


# Declare our ETS project dependencies.
APPTOOLS = etsdep('AppTools', '3.0.0b1')
CHACO = etsdep('Chaco', '3.0.0b1')
DEVTOOLS_FBI = etsdep('DevTools[fbi]', '3.0.0b1')  # -- only by the debug/fbi_plugin.py
ENVISAGECORE = etsdep('EnvisageCore', '3.0.0b1')
TRAITSGUI = etsdep('TraitsGUI', '3.0.0b1')
TRAITS_UI = etsdep('Traits[ui]', '3.0.0b1')

def generate_docs():
    """If sphinx is installed, generate docs.
    """
    doc_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'docs')
    source_dir = os.path.join(doc_dir, 'source')
    html_zip = os.path.join(doc_dir,  'html.zip')
    dest_dir = doc_dir
    
    required_sphinx_version = "0.4.1"
    sphinx_installed = False
    try:
        require("Sphinx>=%s" % required_sphinx_version)
        sphinx_installed = True
    except (DistributionNotFound, VersionConflict):
        log.warn('Sphinx install of version %s could not be verified.'
                    ' Trying simple import...' % required_sphinx_version)
        try:
            import sphinx
            if parse_version(sphinx.__version__) < parse_version(required_sphinx_version):
                log.error("Sphinx version must be >=%s." % required_sphinx_version)
            else:
                sphinx_installed = True
        except ImportError:
            log.error("Sphnix install not found.")
    
    if sphinx_installed:             
        log.info("Generating %s documentation..." % INFO['name'])
        docsrc = source_dir
        target = dest_dir
        
        try:
            build = HtmlBuild()
            build.start({
                'commit_message': None,
                'doc_source': docsrc,
                'preserve_temp': True,
                'subversion': False,
                'target': target,
                'verbose': True,
                'versioned': False
                }, [])
            del build
            
        except:
            log.error("The documentation generation failed.  Falling back to "
                      "the zip file.")
            
            # Unzip the docs into the 'html' folder.
            unzip_html_docs(html_zip, doc_dir)
    else:
        # Unzip the docs into the 'html' folder.
        log.info("Installing %s documentaion from zip file.\n" % INFO['name'])
        unzip_html_docs(html_zip, doc_dir)

def unzip_html_docs(src_path, dest_dir):
    """Given a path to a zipfile, extract
    its contents to a given 'dest_dir'.
    """
    file = zipfile.ZipFile(src_path)
    for name in file.namelist():
        cur_name = os.path.join(dest_dir, name)
        if not name.endswith('/'):
            out = open(cur_name, 'wb')
            out.write(file.read(name))
            out.flush()
            out.close()
        else:
            if not os.path.exists(cur_name):
                os.mkdir(cur_name)
    file.close()

class my_develop(develop):
    def run(self):
        develop.run(self)
        # Generate the documentation.
        generate_docs()

class my_build(distbuild):
    def run(self):
        distbuild.run(self)
        # Generate the documentation.
        generate_docs()

setup(
    author = 'Martin Chilvers',
    author_email = 'info@enthought.com',
    cmdclass = {
        'develop': my_develop,
        'build': my_build
    },
    dependency_links = [
        'http://code.enthought.com/enstaller/eggs/source',
        ],
    description = 'The Envisage Action Framework',
    entry_points = '''
        [enthought.envisage.plugins]
        workbench = enthought.envisage.ui.workbench.workbench_plugin:WorkbenchPlugin
        shell = enthought.plugins.python_shell.python_shell_plugin:PythonShellPlugin
        developer = enthought.envisage.developer.developer_plugin:DeveloperPlugin
        developer_ui = enthought.envisage.developer.ui.developer_ui_plugin:DeveloperUIPlugin
        ''',
    extras_require = {
        'chaco': [
            CHACO,
            ],
        'debug': [
            DEVTOOLS_FBI,
            ],

        # All non-ets dependencies should be in this extra to ensure users can
        # decide whether to require them or not.
        'nonets': [
            #'wx ==2.6',  # wx not available in egg format on all platforms.
            ],
        },
    ext_modules = [],
    include_package_data = True,
    install_requires = [
        APPTOOLS,
        ENVISAGECORE,
        TRAITSGUI,
        TRAITS_UI,
        ],
    license = 'BSD',
    name = 'EnvisagePlugins',
    namespace_packages = [
        'enthought',
        'enthought.envisage',
        'enthought.plugins',
        ],
    packages = find_packages(exclude=['examples']),
    tests_require = [
        'nose >= 0.10.3',
    ],
    test_suite = 'nose.collector',
    url = 'http://code.enthought.com/envisage',
    version = INFO['version'],
    zip_safe = False,
    )

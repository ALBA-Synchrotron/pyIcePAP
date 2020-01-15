# setup.py
import sys
from setuptools import setup
from setuptools import find_packages

# The version is updated automatically with bumpversion
# Do not update manually
__version = '3.2.0'

# windows installer:
# python setup.py bdist_wininst

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords

# ipython profile magic commands implementation
package_list = ['*ipy']

setup_requirements = []

TESTING = any(x in sys.argv for x in ["test", "pytest"])
if TESTING:
    setup_requirements += ['pytest-runner']
test_requirements = ['pytest', 'pytest-cov']

SPHINX = any(x in sys.argv for x in ["build_sphinx"])
if SPHINX:
    setup_requirements += ['sphinx', 'sphinx-argparse', 'sphinx_rtd_theme']


setup(
    name="icepap",
    description="Python IcePAP Extension",
    version=__version,
    author="Guifre Cuni et al.",
    author_email="ctbeamlines@cells.es",
    url="https://github.com/ALBA-Synchrotron/pyIcePAP",
    packages=find_packages(),
    package_data={'': package_list},
    include_package_data=True,
    license="GPLv3",
    long_description="Python IcePAP Extension for Win32, Linux, BSD, Jython",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3.5',
        'Topic :: Communications',
        'Topic :: Software Development :: Libraries',
    ],
    entry_points={
        'console_scripts': [
            'icepap = icepap.__main__:main',
        ]
    },
    install_requires=['numpy'],
    setup_requires=setup_requirements,
    tests_require=test_requirements,
    python_requires='>=3.5',
)

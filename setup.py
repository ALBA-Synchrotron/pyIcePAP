# setup.py
import sys
from setuptools import setup
from setuptools import find_packages

# The version is updated automatically with bumpversion
# Do not update manually
__version = '2.8.1'

# windows installer:
# python setup.py bdist_wininst

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords

# ipython profile magic commands implementation
package_list = ['*ipy']

TESTING = any(x in sys.argv for x in ["test", "pytest"])
setup_requirements = []
if TESTING:
    setup_requirements += ['pytest-runner']
test_requirements = ['pytest', 'pytest-cov']

setup(
    name="pyIcePAP",
    description="Python IcePAP Extension",
    version=__version,
    author="Guifre Cuni",
    author_email="guifre.cuni@cells.es",
    url="https://github.com/ALBA-Synchrotron/pyIcePAP",
    packages=find_packages(),
    package_data={'': package_list},
    include_package_data=True,
    license="Python",
    long_description="Python IcePAP Extension for Win32, Linux, BSD, Jython",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Python Software Foundation License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Topic :: Communications',
        'Topic :: Software Development :: Libraries',
    ],
    entry_points={
        'console_scripts': [
            'pyIcePAP = pyIcePAP.__main__:main',
        ]
    },
    install_requires=['numpy'],
    setup_requires=setup_requirements,
    tests_require=test_requirements
)

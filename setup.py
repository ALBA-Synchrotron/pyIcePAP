# setup.py
from setuptools import setup
from setuptools import find_packages

# The version is updated automatically with bumpversion
# Do not update manually
__version = '2.0.0' 

# windows installer:
# python setup.py bdist_wininst

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords

# ipython profile magic commands implementation
package_list = ['*ipy']

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
    }
)

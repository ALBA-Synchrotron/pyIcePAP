# setup.py
from setuptools import setup
from setuptools import find_packages

# The version is updated automatically with bumpversion
# Do not update manually
__version = '1.0.3-alpha' 

#windows installer:
# python setup.py bdist_wininst

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords

setup(
    name="pyIcePAP",
    description="Python IcePAP Extension",
    version=__version,
    author="Guifre Cuni",
    author_email="guifre.cuni@cells.es",
    url="",
    packages=find_packages(),
    license="Python",
    long_description="Python IcePAP Extension for Win32, Linux, BSD, Jython",
    classifiers = [
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
)

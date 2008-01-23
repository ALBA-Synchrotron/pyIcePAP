# setup.py
from distutils.core import setup
import sys

#windows installer:
# python setup.py bdist_wininst

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords
if sys.version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

setup(
    name="pyIcePAP",
    description="Python IcePAP Extension",
    version="1.0",
    author="Guifre Cuni",
    author_email="gcuni@cells.es",
    url="",
    packages=['pyIcePAP'],
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

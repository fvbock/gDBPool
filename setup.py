from distutils.core import setup

VERSION = (0, 1, 1, 0)
__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))


setup(
    name = 'gDBPool',
    version = '0.1.1',
    author = 'Florian von Bock',
    author_email = 'f@vonbock.com',
    packages = ['gDBPool',],
    description = 'Database pooling and interaction/query runner for gevent.',
    long_description = open('README.md').read(),
    classifiers = [
        "Topic :: Database",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
    ],
)

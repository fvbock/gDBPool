from distutils.core import setup

VERSION = (0, 1, 3, 0)
__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))


setup(
    name = 'gDBPool',
    version = '0.1.3',
    author = 'Florian von Bock',
    author_email = 'f@vonbock.com',
    url = 'https://github.com/fvbock/gDBPool',
    license = 'MIT License',
    packages = ['gdbpool',],
    description = 'Database (PostgreSQL) pooling and interaction/query runner for gevent.',
    long_description = open('README.rst').read(),
    classifiers = [
        "Topic :: Database",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
    ],
)

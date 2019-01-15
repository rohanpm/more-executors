from setuptools import setup


def get_description():
    return 'A library of composable Python executors'


def get_long_description():
    try:
        text = open('README.md').read()
    except IOError as error:
        if error.errno == 2:
            return get_description()
        raise

    # The README starts with the same text as "description",
    # which makes sense, but on PyPI causes same text to be
    # displayed twice.  So let's strip that.
    return text.replace(get_description() + '.\n\n', '', 1)


setup(
    name='more-executors',
    version='1.18.0',
    author='Rohan McGovern',
    author_email='rohan@mcgovern.id.au',
    packages=['more_executors'],
    url='https://github.com/rohanpm/more-executors',
    license='GNU General Public License',
    description=get_description(),
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    install_requires=[
        'futures;python_version<"3"',
        'six',
        'monotonic',
    ],
)

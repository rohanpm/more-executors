from setuptools import setup
import os

if os.environ.get('USE_PANDOC') == '1':
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
else:
    long_description = ''

setup(
    name='more-executors',
    version='1.1.0',
    author='Rohan McGovern',
    author_email='rohan@mcgovern.id.au',
    packages=['more_executors'],
    url='https://github.com/rohanpm/more-executors',
    license='GNU General Public License',
    description='A library of composable Python executors',
    long_description=long_description,
    install_requires=[
        'futures;python_version<"3"',
        'six',
    ],
    tests_require=[
        'hamcrest',
    ]
)

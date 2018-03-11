from setuptools import setup

setup(
    name='more-executors',
    version='1.0.0',
    author='Rohan McGovern',
    author_email='rohan@mcgovern.id.au',
    packages=['more_executors'],
    license='GNU General Public License',
    install_requires=[
        'futures;python_version<"3"',
        'six',
    ],
    tests_require=[
        'hamcrest',
    ]
)

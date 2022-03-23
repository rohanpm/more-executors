from setuptools import setup, find_packages


def get_description():
    return "A library of composable Python executors and futures"


def get_long_description():
    text = open("README.md").read()

    # The README starts with the same text as "description",
    # which makes sense, but on PyPI causes same text to be
    # displayed twice.  So let's strip that.
    return text.replace(get_description() + ".\n\n", "", 1)


def get_install_requires():
    return open("requirements.in").readlines()


setup(
    name="more-executors",
    version="2.10.1",
    author="Rohan McGovern",
    author_email="rohan@mcgovern.id.au",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    url="https://github.com/rohanpm/more-executors",
    license="GNU General Public License",
    description=get_description(),
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=get_install_requires(),
    extras_require={"prometheus": ["prometheus-client"]},
    project_urls={
        "Changelog": "https://github.com/rohanpm/more-executors/blob/master/CHANGELOG.md",
        "Documentation": "https://rohanpm.github.io/more-executors/",
    },
)

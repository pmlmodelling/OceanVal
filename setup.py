from setuptools import Command, find_packages, setup
import sys

DESCRIPTION = "A Python package for ocean model validation and analysis"
LONG_DESCRIPTION = """

**oceanVal** is a Python package designed to automate the process of validating ocean models against observational datasets. It provides a suite of tools to facilitate the comparison of model outputs with various observational data sources, enabling researchers to assess model performance effectively. 

Core abilities of oceanVal include:

  - Matching model output variables to observational datasets 
  - Assesing spatial and temporal performance of ocean models 
  - Assessing model skill using a variety of statistical metrics 
  - Asssessing extent of model biases 
  - Generating comprehensive validation reports in html format


"""


PROJECT_URLS = {
    "Bug Tracker": "https://github.com/pmlmodelling/oceanVal/issues",
    "Source Code": "https://github.com/pmlmodelling/oceanVal",
}

extras_require: dict() = dict()


REQUIREMENTS = [i.strip() for i in open("requirements.txt").readlines()]

setup(name='oceanval',
      version='0.1.9',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      python_requires='>=3.6.1',
      classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

      project_urls=PROJECT_URLS,
      url = "https://github.com/pmlmodelling/oceanVal",
      author='Robert Wilson',
      maintainer='Robert Wilson',
      author_email='rwi@pml.ac.uk',
      include_package_data=True,
      package_data={
      'oceanval': ['data/*'] },

      packages = ["oceanval"],
      setup_requires=[
        'setuptools',
        'setuptools-git',
        'wheel',
    ],
      install_requires = REQUIREMENTS,
      extras_require = extras_require,
      zip_safe=False)





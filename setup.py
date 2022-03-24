'''
Created on 23.03.2021

@author: Fernando Penaherrera @UOL/OFFIS
'''

"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils

from setuptools import setup, find_packages
import pathlib
here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
#long_description = (here / 'README.md').read_text(encoding='utf-8')

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='electricity_markets',  # Required
    version='0.1.0',  # Required
    description='Project to model the trading of energy to different markets using various power plant models',  # Optional
    # long_description=long_description,  # Optional
    long_description_content_type='text/markdown',  # Optional (see note above)
    url='https://github.com/Fernando3161/EnergyMarketsSimulation',  # Optional #Change later
    author='Fernando Penaherrera V., Steffen Wehkamp',  # Optional
    author_email='fernandoandres.penaherreravaca@offis.de',  # Optional
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Researchers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',

    ],
    include_package_data=True,
    package_data={
        
        # Include any *.msg files found in the "hello" package, too:
        "electricity_markets": ["raw/*.csv","raw/*.json","raw/*.xlsx"],
    },
       keywords='Electricity, Markets, Energy',  # Optional
    packages=find_packages(
        where="src",
    ),
    package_dir={"": "src"},
    python_requires='>=3.6, <4',
    install_requires=[
        "matplotlib",
        "oemof.solph",
        "openpyxl",
        "xlsxwriter", ],

    project_urls={  # Optional
        'Bug Reports': 'https://github.com/Fernando3161/EnergyMarketsSimulation',
        #'Funding': 'ZLE Funders',
        'Documentation': "https://github.com/Fernando3161/EnergyMarketsSimulation",
        'Source': "https://github.com/Fernando3161/EnergyMarketsSimulation",
    },
)


if __name__ == '__main__':
    pass

'''
Created on 20.05.2021

@author: Fernando Penaherrera @UOL/OFFIS
'''
import os
from os.path import join


def get_project_root():
    """Return the path to the project root directory.

    :return: A directory path.
    :rtype: str
    """
    return os.path.realpath(os.path.join(
        os.path.dirname(__file__),
        os.pardir,
    ))


BASE_DIR = get_project_root()
SOURCE_DIR = join(BASE_DIR, "src")
ENERGY_MARKETS_DIR = join(SOURCE_DIR, "energy_markets")
EXAMPLES_DIR = join(BASE_DIR, "examples")
EXAMPLES_DATA_DIR = join(EXAMPLES_DIR, "data")
EXAMPLES_RESULTS_DIR = join(EXAMPLES_DIR, "results")
EXAMPLES_PLOTS_DIR = join(EXAMPLES_DIR, "plots")


if __name__ == '__main__':
    print(EXAMPLES_PLOTS_DIR)
    pass

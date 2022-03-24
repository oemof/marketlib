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
ENERGY_MARKETS_DIR = join(BASE_DIR, "electricity_markets")
RAW_DATA_DIR = join(ENERGY_MARKETS_DIR, "raw")
DATA_DIR = join(BASE_DIR, "data")
PROC_DATA_DIR = join(DATA_DIR, "processed")
MODEL_DATA_DIR = join(DATA_DIR, "dumped_models")
RESULTS_DIR = join(BASE_DIR, "results")
RESULTS_DATA_DIR = join(RESULTS_DIR, "data")
RESULTS_VIS_DIR = join(RESULTS_DIR, "visualizations")


if __name__ == '__main__':
    pass

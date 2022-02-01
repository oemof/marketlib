'''
Created on 1 Feb 2022

@author: Fernando Penaherrera @UOL/OFFIS
'''
from src.market_price_generator import create_markets_info
import pandas as pd
from src.common import PROC_DATA_DIR
from os.path import join
data = create_markets_info(2020)

DATA_O = join(PROC_DATA_DIR,"check_price_pattern_all")

data_origin = pd.read_excel()

if __name__ == '__main__':
    pass
'''
Created on 20.01.2022

@author: Fernando Penaherrera @UOL/OFFIS
@author: Steffen Wehkamp OFFIS

Create market price time series from historical data
Using price pattern generated from historical data from 2015-2019

'''

import datetime
import pandas as pd
import calendar

def create_da_price_pattern(year):

    start = datetime.date(year, 1, 1)

    if is_leap_year(year)==True:
        days = 364
    else:
        days = 365

    periods = days * 24

    dti = pd.date_range(start, periods=periods, freq="H")

    #ToDo: check each entry for time, day and month
    #ToDo: index match function for each entry to find value from excel
    # table day_ahead_price_profile.xlsx
    #ToDo: check if year is historic (2015-2020)
    #ToDo: match historical years with values from excel table
    # market_parameter.xlsx
    
    return dti

def is_leap_year(year):
    """Determine whether a year is a leap year."""

    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


if __name__ == '__main__':
    create_da_price_pattern(2018)

'''
Created on 20.01.2022

@author: Fernando Penaherrera @UOL/OFFIS
@author: Steffen Wehkamp OFFIS

Create market price time series from historical data
Using price pattern generated from historical data from 2015-2019

'''

import datetime
import pandas as pd
from os.path import join
from src.common import RAW_DATA_DIR, PROC_DATA_DIR


def read_text_ranges(s):
    if "-" in str(s):
        s0, s1 = s.split("-")
        s_l = list(range(int(s0), int(s1) + 1))
    else:
        s_l = [int(s)]

    return s_l


def create_da_price_pattern(year):

    start = datetime.date(year, 1, 1)

    if is_leap_year(year):
        days = 364
    else:
        days = 365

    periods = days * 24

    dti = pd.date_range(start, periods=periods, freq="H")

    df = pd.DataFrame()
    df["Date"] = dti
    df["Month"] = dti.month
    df["DayOfWeek"] = dti.dayofweek

    #ToDo: check each entry for time, day and month

    #EXCEL READER
    EXCEL_DATA = join(RAW_DATA_DIR, "day_ahead_price_profile.xlsx")
    da_data = pd.read_excel(
        EXCEL_DATA,
        "DA_Price",
        engine='openpyxl',
        parse_dates=False)
    da_data["Day_Range_Min"] = [min(read_text_ranges(s))
                                for s in da_data["day"]]
    da_data["Day_Range_Max"] = [max(read_text_ranges(s))
                                for s in da_data["day"]]

    price = []
    i = 0
    while i < periods:
        print(i)
        month = df.at[i, "Month"]
        day_of_week = df.at[i, "DayOfWeek"] + 1

        da_data_month = da_data[da_data["month"] == month]

        da_data_day = da_data_month[da_data_month["Day_Range_Min"]
                                    <= day_of_week]
        da_data_day = da_data_day[da_data_day["Day_Range_Max"] >= day_of_week]

        partial_data = da_data_day.T
        cols = partial_data.columns
        print(cols)
        partial_data = partial_data.drop(
            ["month", "day", "Day_Range_Min", "Day_Range_Max"])
        vals = [v for v in partial_data[cols[0]]]
        for v in vals:
            price.append(v)
        i += 24

    df["da_price"] = price

    res = df[["Date", "da_price"]]
    res.set_index("Date", inplace=True)

    import matplotlib.pyplot as plt
    res["da_price"].head(24 * 7 * 12).plot()
    CSV_SAVE = join(PROC_DATA_DIR, "generated_da_price_{}.csv".format(year))
    res.to_csv(CSV_SAVE)

    plt.show()

    #ToDo: index match function for each entry to find value from excel
    # table day_ahead_price_profile.xlsx
    #ToDo: check if year is historic (2015-2020)
    #ToDo: match historical years with values from excel table
    # market_parameter.xlsx

    return res


def is_leap_year(year):
    """Determine whether a year is a leap year."""

    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


if __name__ == '__main__':
    create_da_price_pattern(2018)

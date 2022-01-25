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
import logging
logging.basicConfig(level=logging.INFO)


def read_text_ranges(s):
    '''
    Reads the ranges of a text if it is written in a "4-6" format.
    If text is a single digit returns a list only with this digit

    :param s: String of text. Can be a single digit "4" or a range "2-6"
    '''
    if "-" in str(s):
        s0, s1 = s.split("-")
        s_l = list(range(int(s0), int(s1) + 1))
    else:
        s_l = [int(s)]

    return s_l


def create_da_price_pattern(year, market, mean_val=None):
    '''
    Creates a Price Pattern for the Day Ahead Price.
    Uses existing profiles to compose a pattern for a whole year

    :param year: Desired year
    :param market: Day Ahead or Intra Day. One of ["da", "id"]
    :param mean_val: Mean value. Optional for the years 2015-2020, since data exists.
    '''

    if market not in ["da", "id"]:
        raise ValueError('Parameter "market" must be one "da" or "id".')

    start = datetime.date(year, 1, 1)

    if is_leap_year(year):
        days = 364
    else:
        days = 365

    if market == "da":
        periods = days * 24
        dti = pd.date_range(start, periods=periods, freq="H")

    if market == "id":
        periods = days * 24 * 4
        dti = pd.date_range(start, periods=periods, freq="15T")

    df = pd.DataFrame()

    # Need some parameters of the Datetime object to search patterns
    df["Date"] = dti
    df["Month"] = dti.month
    df["DayOfWeek"] = dti.dayofweek

    # EXCEL READER
    if market == "da":
        EXCEL_DATA = join(RAW_DATA_DIR, "day_ahead_price_profile.xlsx")  # xxxx
    elif market == "id":
        EXCEL_DATA = join(RAW_DATA_DIR, "intraday_price_profile.xlsx")  # xxxx

    da_data = pd.read_excel(
        EXCEL_DATA,
        "Price",
        engine='openpyxl',
        parse_dates=False)

    # Pass the text ranges as intervals
    da_data["Day_Range_Min"] = [min(read_text_ranges(s))
                                for s in da_data["day"]]
    da_data["Day_Range_Max"] = [max(read_text_ranges(s))
                                for s in da_data["day"]]

    price = []
    i = 0

    # Loop
    while i < periods:
        month = df.at[i, "Month"]

        day_of_week = df.at[i, "DayOfWeek"] + 1  # Python puts monday at 0

        # Filter data to search the corresponding values
        da_data_month = da_data[da_data["month"] == month]
        da_data_day = da_data_month[da_data_month["Day_Range_Min"]
                                    <= day_of_week]
        da_data_day = da_data_day[da_data_day["Day_Range_Max"] >= day_of_week]

        # Easier to transpose the table
        partial_data = da_data_day.T
        cols = partial_data.columns
        partial_data = partial_data.drop(
            ["month", "day", "Day_Range_Min", "Day_Range_Max"])
        for v in partial_data[cols[0]]:
            price.append(v)

        # Since daily profiles are alreade in order just go to next day

        if market == "da":
            i += 24
        elif market == "id":
            i += 24 * 4

    df["price"] = price

    mean_profile = df["price"].mean()

    if year in range(2015, 2021) and mean_val is None:
        # Look for the value of year in the given excel data
        MARKET_PAR_FILE = join(RAW_DATA_DIR, "market_parameter.xlsx")
        market_pars = pd.read_excel(
            MARKET_PAR_FILE,
            "MarketParams",
            engine='openpyxl',
            parse_dates=False)
        market_pars.set_index("year", inplace=True)
        if market == "da":
            col_name = "dayahead"
        elif market == "id":
            col_name = "intraday"

        mean_price_year = market_pars.at[year, col_name]

        # Scale the whole profile shape with the mean value proportion
        df["price"] = df["price"] * mean_price_year / mean_profile

    if mean_val:
        # Override the previous one if mean value is given
        df["price"] = df["price"] * mean_val / mean_profile

    if year not in range(2015, 2021) and mean_val is None:
        raise ValueError(
            "For years outside of 2015-2020 a mean value is required. I.e.: mean_val=40")

    # Take only the necesary columns
    res = df[["Date", "price"]]

    new_column_name = f"{market}_price"

    res.rename(columns={"price": new_column_name}, inplace=True)
    res.set_index("Date", inplace=True)

    CSV_FILENAME = join(PROC_DATA_DIR,
                        "generated_{}_price_{}.csv".format(market, year))
    res.to_csv(CSV_FILENAME)
    logging.info(
        "{} Price pattern for the year {} saved to {}".format(
            market.upper(), year, CSV_FILENAME))

    return res


def is_leap_year(year):
    """
    Determine whether a year is a leap year.

    :param year: Year (int)
    """

    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


if __name__ == '__main__':
    create_da_price_pattern(2018, market="da")
    create_da_price_pattern(2018, market="id")
    create_da_price_pattern(2019, market="da", mean_val=60)
    create_da_price_pattern(2019, market="id", mean_val=50)
    create_da_price_pattern(2022, market="da", mean_val=75)
    create_da_price_pattern(2022, market="id", mean_val=75)
    create_da_price_pattern(2025, market="id")
    create_da_price_pattern(2025, market="da")

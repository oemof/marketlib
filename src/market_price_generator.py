'''
Created on 20.01.2022

@author: Fernando Penaherrera @UOL/OFFIS
@author: Steffen Wehkamp OFFIS

Create market price time series from historical data
Using price pattern generated from historical data from 2015-2019

'''
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


def create_price_pattern(year, market, mean_val=None):
    '''
    Creates a Price Pattern for the Day Ahead Price.
    Uses existing profiles to compose a pattern for a whole year

    :param year: Desired year
    :param market: Day Ahead or Intra Day. One of ["da", "id"]
    :param mean_val: Mean value. Optional for the years 2015-2020, since data exists.
    '''

    if market not in ["da", "id"]:
        raise ValueError('Parameter "market" must be one "da" or "id".')

    START = f"{year}-01-01 00:00:00"

    if market == "da":
        END = f"{year}-12-31 23:00:00"
        dti = pd.date_range(start=START, end=END, freq="H", tz='Europe/Berlin')

    if market == "id":
        END = f"{year}-12-31 23:45:00"
        dti = pd.date_range(
            start=START,
            end=END,
            freq="15T",
            tz='Europe/Berlin')

    periods = len(dti)

    df = pd.DataFrame()
    
    # Need some parameters of the Datetime object to search patterns
    df["Date"] = dti
    df["Month"] = dti.month
    df["DayOfWeek"] = dti.dayofweek

    # Excel reader
    if market == "da":
        EXCEL_DATA = join(RAW_DATA_DIR, "day_ahead_price_profile.xlsx")
    elif market == "id":
        EXCEL_DATA = join(RAW_DATA_DIR, "intraday_price_profile.xlsx")

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

    # Loop for the different time stamps
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

        # Since daily profiles are already in order just go to next day

        if market == "da":
            i += 24
        elif market == "id":
            i += 24 * 4

    # Copy the price info to the dataframe
    df["price"] = price


    if mean_val:
        # Override the previous one if mean value is given
        # The values of the profiles in the excel data are normalized to 100
        df["price"] = df["price"] * mean_val / 100

    if year not in range(2015, 2021) and mean_val is None:
        raise ValueError(
            "For years outside of 2015-2020 a mean value is required. I.e.: 'mean_val=40'")

    # Take only the necessary columns
    res = df[["Date", "price"]]
    
    # Reformat Dataframe to avoid conflicts with other markets
    new_column_name = f"{market}_price"
    res.rename(columns={"price": new_column_name}, inplace=True)
    res.set_index("Date", inplace=True)

    logging.info(
        "{} Price pattern for the year {} created".format(
            market.upper(), year))
    return res


def create_markets_info(
        year,
        mean_da=None,
        mean_id=None,
        fb=None,
        fp=None,
        save_csv=False):
    '''
    Creates a dataframe with information on the IntraDay, Day Ahead, Future Base, and Future Peak
    markets

    For years 2015-2017: Uses DA and ID market data, FP and FB must be given
    For years 2018-2020: Uses DA, ID, FP, and FB market data. None must be given
    For years 2021-2025: Uses FB and FP market data. DA and ID must be given
    For years 2025-: DA, ID, FP and FP market data must be giiven

    :param year: Year for data
    :param mean_da: Mean Day Ahead price. Required for years 2022 an onwards
    :param mean_id: Mean Intraday price. Required for years 2022 an onwards
    :param fb: Future Base Prices. Required for years outside of 2018-2025
    :param fp: Future Peak Prices. Required for years outside of 2018-2025
    '''
    # Check the years:
    if year < 2015:
        raise ValueError("Year has to be greater than 2015")

    if year >= 2021 and mean_da is None:
        raise ValueError(
            'Mean Day ahead price "mean_da=" must be given for year>2021')

    if year >= 2021 and mean_id is None:
        raise ValueError(
            'Mean Intraday price "mean_id=" must be given for year>2021')

    if year not in range(2018, 2026) and fb is None:
        raise ValueError(
            'Future Base price "fb=" must be given for years not in 2018-2025')

    if year not in range(2018, 2026) and fp is None:
        raise ValueError(
            'Future Peak price "fp=" must be given for years not in 2018-2025')

    # Get DA and ID info
    if year in range(2015, 2021):
        DA_ID_MARKET_PARAMETER = join(RAW_DATA_DIR, "market_parameter.xlsx")
        da_id_data = pd.read_excel(DA_ID_MARKET_PARAMETER, "MarketParams",
                                   index_col="year",
                                   engine='openpyxl'
                                   )

        mean_da = da_id_data.at[year, "dayahead"]
        mean_id = da_id_data.at[year, "intraday"]

    day_ahead = create_price_pattern(
        year=year, market="da", mean_val=mean_da)
    day_ahead = day_ahead.resample("15min").pad()
    intra_day = create_price_pattern(
        year=year, market="id", mean_val=mean_id)
    markets_data = pd.concat([day_ahead, intra_day], axis=1)

    # Need to copy the last 3 values to fill the table for Day Ahead
    for i in range(1, 4):
        markets_data["da_price"][-i] = markets_data["da_price"][-4]

    if year in range(2018, 2025):
        future_base = pd.read_csv(
            join(
                RAW_DATA_DIR,
                "future_base_prices.csv")).set_index("year").loc[year]["price"]
    else:
        future_base = fb

    markets_data["future_base"] = [future_base] * markets_data.shape[0]

    if year in range(2018, 2025):
        future_peak = pd.read_csv(
            join(
                RAW_DATA_DIR,
                "future_peak_prices.csv")).set_index("year").loc[year]["price"]
    else:
        future_peak = fp

    future_peak_vals = [future_peak] * markets_data.shape[0]

    day_of_the_week = markets_data.index.dayofweek

    for i in range(markets_data.shape[0]):
        # Make the future peaks value 0 outside 8h and 21h exclusive (up to
        # 20h45)

        if markets_data.index[i].hour not in range(8, 21):
            future_peak_vals[i] = 0

        # Make weekend values == 0
        if day_of_the_week[i] in [5, 6]:
            future_peak_vals[i] = 0

    markets_data["future_peak"] = future_peak_vals

    time_stamps = markets_data.index.tolist()
    utc_offset = [t.tz._utcoffset for t in time_stamps]

    # check those where the offset is different from the 01-Jan 00:00:00
    diff = [False if utc == utc_offset[0] else True for utc in utc_offset]

    # now a quick solution is to move the prices 1 hour up for the times with
    # utc +2
    da_utc = [markets_data["da_price"][i] if diff[i] ==
              False else markets_data["da_price"][i + 4] for i in range(0, len(diff))]
    id_utc = [markets_data["id_price"][i] if diff[i] ==
              False else markets_data["id_price"][i + 4] for i in range(0, len(diff))]

    markets_data["da_price"] = da_utc
    markets_data["id_price"] = id_utc

    logging.info(f"Electricity market prices (DA,ID,FB,FP) for {year} created")

    # Write the dataframe to a csv
    if save_csv:
        markets_data.to_csv(join(PROC_DATA_DIR, "EnergyMarketPrice_{}.csv".format(year)))

    return markets_data


if __name__ == '__main__':
    for i in range(2018, 2021):
        create_markets_info(i, save_csv=True)
    create_markets_info(year=2021, mean_da=75, mean_id=60, save_csv=True)
    create_markets_info(year=2030, mean_da=75, mean_id=60, fb=75, fp = 80, save_csv=True)

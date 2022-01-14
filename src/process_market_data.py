'''
Created on 17.06.2021

@author: Fernando Penaherrera @UOL/OFFIS

Clean the Electricity Price Data to have it ready for being read as
an oemof.solph.flow() Price Info

'''
from src.common import RAW_DATA_DIR, PROC_DATA_DIR
import os
import pandas as pd
from os.path import isfile, join
import logging
from pandas.core.common import SettingWithCopyWarning

import warnings
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

logging.basicConfig(level=logging.INFO)

def process_market_data(overwrite = True):
    '''
    Procceses  the raw data files into ordered csvs with the data
    of Day Ahead and Intra Day prices for future evaluation.
    Needs to be run only once since the data is to be further read
    and processed by other methods.
    '''
    market_filename = os.path.join(PROC_DATA_DIR, "market_data.csv")
    
    if overwrite and isfile(market_filename):
        return None
        # raise FileExistsError("Market data file exists. Delete file before continuing")
    
    day_ahead = os.path.join(RAW_DATA_DIR,"day_ahead_index_prices.csv")
    intra_day = os.path.join(RAW_DATA_DIR,"intraday_index_prices.csv") 
    
    # Read File as CSV and create the DFs
    
    # First the day ahead
    # Create a date time index between the start and the end
    # This is the easy way since data has daylight saving times which
    # are giving issues with the dadta reading
    start = "2014-01-01"
    periods= 62112
    freq = 60
    dti_da = pd.date_range(start, periods=periods, freq="{}min".format(freq), tz="Europe/Berlin")
    da_data=pd.read_csv(day_ahead, names=["date","day_ahead"], sep=";")
    da_dict={"Date": dti_da, "day_ahead":da_data["day_ahead"]}
    df_da= pd.DataFrame.from_dict(da_dict)
    df_da.set_index("Date", inplace=True)
    df_da=df_da.resample("15min").pad()
    
    ## Same for intra day
    start = "2015-01-01"
    periods= 210528
    freq = 15
    dti_id = pd.date_range(start, periods=periods, freq="{}min".format(freq), tz="Europe/Berlin")
    id_data=pd.read_csv(intra_day, names=["date","intra_day"], sep=";")
    id_dict={"Date": dti_id, "intra_day":id_data["intra_day"]}
    df_id= pd.DataFrame.from_dict(id_dict)
    df_id.set_index("Date", inplace=True)
    df_id=df_id.resample("15min").pad()
    
    # Join the DFs
    df_concat = pd.concat([df_da, df_id], axis=1)
    df_concat.to_csv(market_filename)
    logging.info("Market data processed and saved in {}".format(market_filename))
    
def read_market_data(start="2016-05-15", periods= 100, freq=15):
    '''
    Provides a dataframe with market data from the specified datetime 
    with the required number of steps.
    Resolution is 15 mins by default.
    
    :param start: String with the start date. "YYYY-MM-DD"
    :param periods: Number of periods
    :param freq: Frequency in minutes. One of [15,30,60]
    '''
    if freq not in [15,30,60]:
        raise ValueError("Frequency must be 15, 30, or 60 min")
    
    market_filename = os.path.join(PROC_DATA_DIR, "market_data.csv")
        
    periods *=freq/15
  
    dti = pd.date_range(start, periods=periods, freq="{}min".format(freq), tz="Europe/Berlin")
    start= dti[0] 
    end = dti[-1]
  
    df=pd.read_csv(market_filename)
    df["Date"]=pd.to_datetime(df["Date"], utc=True)
    datetime_index = pd.DatetimeIndex(df["Date"].values)
    df.set_index(datetime_index, inplace=True)
    df.drop("Date", axis=1, inplace=True)
    df_subset= df.loc[start:end]
 
    year = int(start.year)
    if year not in range(2018,2026):
        raise ValueError("No Future Base or Future Peak data for the given year")
    
    future_base =pd.read_csv(
        join(RAW_DATA_DIR,"future_base_prices.csv")).set_index("year").loc[year]["price"]
    future_peak =pd.read_csv(
        join(RAW_DATA_DIR,"future_peak_prices.csv")).set_index("year").loc[year]["price"]
    future_peak_vals = [future_peak]*df_subset.shape[0]
    
    day_of_the_week= df_subset.index.dayofweek
    
    for i in range(df_subset.shape[0]):
        # Make the future peaks value 0 outside 8h and 21h exclusive (up to 20h45) 

        if df_subset.index[i].hour not in range(8,21):
            future_peak_vals[i] = 0
        
        # Make weekend values == 0
        if day_of_the_week[i] in [5,6]:
            future_peak_vals[i] = 0
    
    
    df_subset["future_peak"]= future_peak_vals
    
    # Constant values for future base
    df_subset["future_base"]= [future_base]*df_subset.shape[0]
       
    return df_subset

def get_market_data(year=2016, overwrite=False):
    """
    Writes a pickle with the dataframe for the year
    """
    filename= os.path.join(PROC_DATA_DIR,"ElectrictyMarket{}.pkl".format(year))
    if isfile(filename) and overwrite==False:
        logging.info("Market data for the year {} loaded from {}".format(year, filename))
        return pd.read_pickle(filename)
        
    else:
        start = str(year)+"-01-01"
        periods = 365*24
        
        # Leap year
        if year/4 == 0:
            periods += 24 
        periods= periods*4 # 15 mins
        freq= 15 
        df = read_market_data(start, periods, freq)
        df.to_pickle(os.path.join(PROC_DATA_DIR,"ElectrictyMarket{}.pkl".format(year)))
        logging.info("Market data for the year {} saved in {}".format(year, filename))

        return df

def solve_and_write_data():
    '''
    Generates market data for years 2016 to 2020 and saves into plks
    '''
    process_market_data()
    for year in range(2018,2021):
        get_market_data(year, overwrite=True)

if __name__ == '__main__':
    solve_and_write_data()
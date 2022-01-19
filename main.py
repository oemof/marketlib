'''
Created on 14.01.2022

@author: Fernando Penaherrera @UOL/OFFIS

Main file for modelling of the different markets.

The first sets of models consider a district with different
power sources and four different markets to sell excess energy.

For analysis, scenarios with different market prices (inflated) are
build to study the functionality of the model

The second set of models considers only one type of power plant with four 
different markets and analyzes which is the best option for selling energy,
considering only operational costs.
'''

from src.district_model_4_markets import main as district_model
from src.power_plants_model import main as power_plants_model


if __name__ == '__main__':
    
    district_model(year=2020, days = 28)
    power_plants_model(year = 2020, days=28)
    
    pass
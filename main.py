'''
Created on 14.01.2022

@author: Fernando Penaherrera @UOL/OFFIS

Main file for modelling of the different markets on the examples folder.

The first sets of models consider a district with different
power sources and four different markets to sell excess energy.

For analysis, scenarios with different market prices (inflated) are
build to study the functionality of the model

The second set of models considers only one type of power plant with four 
different markets and analyzes which is the best option for selling energy,
considering only operational costs.
'''

from examples.district_model_4_markets import main as model_4_markets
from examples.power_plants_model import main as model_power_plants

if __name__ == '__main__':
    
    model_4_markets(year=2019, days=30)
    model_power_plants(year=2019, days=30)
    
    pass
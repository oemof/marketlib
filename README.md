# EnergyMarketsSimulation
Project to model the trading of energy to different markets using various power plant models


 
Main file for modeling of the different markets.

main.py
The first sets of models consider a district with different
power sources and four different markets to sell excess energy.

For analysis, scenarios with different market prices (inflated) are
build to study the functionality of the model

The second set of models considers only one type of power plant with four 
different markets and analyzes which is the best option for selling energy,
considering only operational costs.

## PricePatternGenerator
Project to create price pattern for energy markets based on historical prices.

The function market_price_generator creates market price time series for historical and future years.
For historical time series the year is necessary parameter.
For future years there are necessary and optional parameter:
###Necessary
* year
###Optional
* Average market price
* Average volatility (year)
* Volatility pattern

The methodology implemented in this library is described in [this](https://doi.org/10.1002/ceat.202100062) scientific paper:
Supportive Information can be found [here](https://onlinelibrary.wiley.com/action/downloadSupplement?doi=10.1002%2Fceat.202100062&file=ceat202100062-sup-0001-misc_information.pdf).

The price pattern dimensions are:
* Time
* Day (typical days)
* Month

This is due to the findings of the mentioned paper:
1. Price pattern barely depend on the years:
![Figure 4](https://user-images.githubusercontent.com/25903724/150540178-f7e3ebc9-5886-4c93-b86d-bbda13020f1a.png)
2. Price pattern depend very much on the days:
![Figure 5](https://user-images.githubusercontent.com/25903724/150540240-44f64eb8-9c68-4db4-aeee-a56670c2af31.png)
3. Seasonality can be mapped well via the months parameter (in comparision to dynamic functions and seasons)
![Seasonality](https://user-images.githubusercontent.com/25903724/150540842-64b364e8-be71-4cf9-8687-09c7516c5f34.PNG)

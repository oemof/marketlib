'''
Created on 14.01.2022

@author: Fernando Penaherrera @UOL/OFFIS
@review: Steffen Wehkamp @OFFIS

This set of functions model the different power plants and their outputs
in the different markets

#1 Define Power Plants Scenarios
#2 Define Market Scenarios
#3 Build  Energy Systems which consider the different Scenarios
#4 Combine Scenarios and present results in a nice dataframe/csv
#5 Dump the scenarios as .oemof files
#6 Save results as graphics
'''

from enum import Enum
from oemof.solph import (EnergySystem, Bus, Sink, Source, Flow)
import pandas as pd
from src.common import RESULTS_DATA_DIR, RESULTS_VIS_DIR
import matplotlib.pyplot as plt
from src.process_market_data import get_market_data
from src.district_model_4_markets import get_district_dataframe,\
    build_model_and_constraints, solve_model, post_process_results
from os.path import join
import logging


class PowerPlants(Enum):
    '''
    Listing of the different power plants available
    '''
    COAL = 1
    GAS = 2
    BIOGAS = 3
    PV = 4
    WIND = 5


def get_boundary_data(year=2020, days=366):
    '''
    Constructs dataframes with the information for modelling

    :param year: Year under consideration
    :param days: Days to model. Default is 366 for a leap year
    '''
    district_df = get_district_dataframe(year=year).head(24 * 4 * days)

    # Create Energy System with the dataframe time series
    market_data = get_market_data(year=year).head(24 * 4 * days)

    return district_df, market_data


def create_energy_system(scenario, district_df, market_data):
    '''
    Creates an oemof energy system for the input scenario

    :param scenario: One of the PowerPlants Scenario
    :param district_df: Dataframe with the district information
    :param market_data: Dataframe with market prices for each market
    '''

    meta_data = {}

    # Variable costs information, EUR/MWh
    meta_data["cv"] = {"coal": 43.92,
                       "gas": 46.17,
                       "biogas": 68.15,
                       "pv": 0,
                       "wind": 0}

    meta_data["max_energy"] = {
        "coal": 1,
        "gas": 1,
        "biogas": 1,
        "wind": district_df["Wind_pu"].values,
        "pv": district_df["PV_pu"].values}

    energy_system = EnergySystem(timeindex=district_df.index)

    label = scenario.name.lower()

    # create Bus
    b_el = Bus(label="b_el_out")

    # create Source
    source = Source(label="source", outputs={b_el: Flow(
        nominal_value=1,
        max=meta_data["max_energy"][label],
        variable_costs=meta_data["cv"][label])})

    # The markets each are modelled as a sink
    s_day_ahead = Sink(
        label="s_da",
        inputs={b_el: Flow(variable_costs=-market_data["day_ahead"].values)})

    s_intraday = Sink(
        label="s_id",
        inputs={b_el: Flow(variable_costs=-market_data["intra_day"].values)})

    s_future_base = Sink(
        label="s_fb",
        inputs={b_el: Flow(variable_costs=-market_data["future_base"].values)})

    s_future_peak = Sink(
        label="s_fp",
        inputs={b_el: Flow(variable_costs=-market_data["future_peak"].values)})

    energy_system.add(
        b_el,
        source,
        s_day_ahead,
        s_future_base,
        s_future_peak,
        s_intraday)

    return energy_system


def calculate_kpis(res, market_data):
    '''
    Calculate a set of KPIs and return them as dataframe
    :param res: Results dataframe
    :param market_data: Market dataframe
    '''

    total_energy = res.sum() / 4  # Since it it was in 15min intervals
    income = {
        "income, da": res["b_el_out, s_da"].values *
        market_data["day_ahead"].values,
        "income, id": res["b_el_out, s_id"].values *
        market_data["intra_day"].values,
        "income, fb": res["b_el_out, s_fb"].values *
        market_data["future_base"].values,
        "income, fp": res["b_el_out, s_fp"].values *
        market_data["future_peak"].values}

    income["income, total"] = income["income, da"] + \
        income["income, id"] + income["income, fb"] + income["income, fp"]

    income_total = {k: round(v.sum() / 4, 1) for k, v in income.items()}
    income_total["average_price EUR/MWh"] = income_total["income, total"] / \
        total_energy["source, b_el_out"]
    income_total = pd.Series(income_total)

    kpis = total_energy.append(income_total)
    return kpis


def model_power_plant_scenario(scenario, district_df, market_data, days=365):
    '''
    Model an scenario and calculate kpis based on the given boundary data 
    
    :param scenario: Scenario from PowerPlants
    :param district_df: Dataframe with information of the District
    :param market_data: Market Data with electricity price information
    :param days: Number of days to model, starting on 01/01
    '''
    
    es = create_energy_system(scenario, district_df, market_data)
    model = build_model_and_constraints(es)
    solved_model = solve_model(model)
    results = post_process_results(solved_model)
    kpis = calculate_kpis(results, market_data)

    return results, kpis


def solve_and_write_data(year=2020, days=365):
    '''
    Solve the different scenarios and write the data to a XLSX

    :param year: Year of data
    :param days: Number of days to model, starting on 01/01
    '''
    data_path = join(RESULTS_DATA_DIR, 'PowerPlantsModels.xlsx')
    writer = pd.ExcelWriter(data_path, engine='xlsxwriter')

    results_dict = {}

    # One cannot open and close the workbook w/o deleting previous books
    district_df, market_data = get_boundary_data(year=year, days=days)

    for scenario in PowerPlants:
        results, kpis = model_power_plant_scenario(
            scenario, district_df, market_data, days=days)

        results_dict[scenario] = results

        ts_name = scenario.name + '-TimeSeries'
        kpi_name = scenario.name + '-KPIs'

        # Open Excel Writer

        workbook = writer.book
        worksheet = workbook.add_worksheet(ts_name)
        writer.sheets[ts_name] = worksheet

        # Save results and kpis to excel
        results.to_excel(writer, sheet_name=ts_name)
        worksheet = workbook.add_worksheet(kpi_name)
        writer.sheets[kpi_name] = worksheet
        kpis.to_excel(writer, sheet_name=kpi_name)

    writer.save()
    logging.info(f"Results and KPIs saved to {data_path}")
    return results_dict


def create_graphs(results_dict):
    '''
    Create graphs and save them in the Results visualization directory

    :param results_dict: Dictionary with the results from the different scenarios
    '''
    for scenario in PowerPlants:
        results = results_dict[scenario]
        c = [c for c in results.columns if "b_el_out" in c.split(",")[0]]
        styles = ['b', 'r:', 'y-.', 'g-.']
        results[c].plot(figsize=(16, 12), style=styles)
        plt.savefig(join(RESULTS_VIS_DIR, f"PowerPlant-{scenario.name}.jpg"))
        logging.info(f"Plot saved  year and Scenario {scenario.name}")


def main(year = 2020, days=365):
    '''
    Chain functions to solve, write, and plot data from the scenario results

    :param days: Number of days to plot, starting on 01/01
    '''
    results_dict = solve_and_write_data(year =year, days=days)
    create_graphs(results_dict)


if __name__ == '__main__':
    main(year=2020, days=28)

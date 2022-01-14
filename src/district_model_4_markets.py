'''
Created on 29.06.2021

@author: Fernando Penaherrera @UOL/OFFIS

Creates a model with demands for a district and several power plants

Data and configurations are obtained from the ENAQ Model

Scenarios manipulate the size of the facilites (such as CHP, PV, Storage)
'''

import pandas as pd
from src.common import RAW_DATA_DIR, RESULTS_DIR, RESULTS_DATA_DIR,\
    RESULTS_VIS_DIR
from oemof.solph import (EnergySystem, Bus, Sink, Source, Flow,
                         Transformer, GenericStorage, Model)
from src.process_market_data import get_market_data
from oemof.solph import views, processing
import matplotlib.pyplot as plt
import logging
import pyomo.environ as po
from enum import Enum
import os
from os.path import join
import json

logging.basicConfig(level=logging.INFO)

# Get data
# TODO: See if I can parse the info from the website
# https://www.boerse.de/rohstoffe/Erdgas/XD0002745517
GAS_PRICE = 3.66  # EUR per mmBTU

# EUR/mmBTU / (293.07 kWh/mmBTU)*(1000 kWh/MWh)
GAS_PRICE = GAS_PRICE / 293.07 * 1000


class Scenarios(Enum):
    BASELINE = 1
    DAY_AHEAD = 2
    FUTURE_BASE = 3
    FUTURE_PEAK = 4


def get_district_dataframe(year=2017):
    '''
    Build a dataframe with the information of the district found
    in the first excel file found. By default searches the year 2017

    :param year: Year

    :return: Dataframe with the district energy demand info.
    '''
    EXCEL_DATA = join(RAW_DATA_DIR, "quartier1_{}.xlsx".format(year))

    if not os.path.isfile(EXCEL_DATA):
        EXCEL_DATA = join(RAW_DATA_DIR, "quartier1_{}.xlsx".format(2017))
        logging.warning(
            "No district data found for year {}. Using year 2017".format(year))
    start = str(year) + "-01-01"
    days = 365  # Full year

    # Correct for leap year
    if year % 4 == 0:
        days += 1

    # Set first the datetime objects with the appropriate dates
    dates = pd.date_range(start, periods=days * 24 + 1, freq="H")

    # Electricity
    electricity = pd.read_excel(EXCEL_DATA, "electricity demand series")[
        "DE01"][2:].tolist()

    # Heat
    heat = pd.read_excel(EXCEL_DATA, "heat demand series")[
        "DE01"][2:].tolist()

    # PV Production per kW installed (as data source, no direct PV Modeling)
    pv_df = pd.read_excel(EXCEL_DATA, "volatile series")

    # Data is on the 4th column
    pv_pu = pv_df[pv_df.columns[3]][2:].tolist()

    # Wind Production per kW installed (as data source, no direct WK Modeling)
    wind_df = pd.read_excel(EXCEL_DATA, "volatile series")

    # Data is on the 5th column
    wind_pu = wind_df[wind_df.columns[4]][2:].tolist()

    # Complete the last hour so I get a full year.
    # Copy the last value for simplicity
    electricity.append(electricity[-1])
    heat.append(heat[-1])
    pv_pu.append(pv_pu[-1])
    wind_pu.append(wind_pu[-1])

    min_len = min(len(dates),
                  len(electricity),
                  len(heat),
                  len(pv_pu),
                  len(wind_pu))


    # Build Dataframe from a dictionary
    district_data = {
        "Date": dates[0:min_len],
        "Electricity": electricity[0:min_len],
        "Heat": heat[0:min_len],
        "PV_pu": pv_pu[0:min_len],
        "Wind_pu": wind_pu[0:min_len]}
    
    
    district_df = pd.DataFrame.from_dict(district_data)
    district_df.set_index("Date", inplace=True)

    # Set the time resolution as 15 mins
    district_df = district_df.resample("15T").pad()

    # Remove the last value as it is for 01-Jan 00:00 of next year.
    return district_df[:-1]


def get_market_dataframe(days=7, year=2017, scenario=Scenarios.BASELINE):
    """
    The scenarios are showing a strong preference for intraday markets
    "Artifical" scenarios are built. These inflate Future Base, Future Peak,
    and day ahead, to see if the constraints are working properly.
    """

    # Get data of the energy demands and of the PV production per unit
    # Get market data as per the raw files
    market_data = get_market_data(year=year).head(days * 24 * 4)

    # Definition of scenarios. Inflation of market prices for functionality
    # evaluation
    if scenario == Scenarios.BASELINE:
        logging.info("Normal Scenario")

    if scenario == Scenarios.DAY_AHEAD:
        logging.info("Day Ahead Price Inflated")
        market_data["day_ahead"] = market_data["day_ahead"] * 2

    if scenario == Scenarios.FUTURE_BASE:
        logging.info("Future Base Price Inflated")
        market_data["future_base"] = market_data["future_base"] * 3

    if scenario == Scenarios.FUTURE_PEAK:
        market_data["future_peak"] = market_data["future_peak"] * 3

    return market_data


def create_energy_system(boundary_data, market_data, sizing=None):
    # Default Data of the devices of the disctrit
    # The same configuration needs to be passed if changes are to be made
    # to the district configuraiton
    if sizing is None:
        sizing = dict()
        sizing["PV"] = 200  # kW
        sizing["Boiler"] = {"Power": 300,  # kW
                            "Eff": 0.85,  # 1
                            }
        sizing["Battery"] = {
            "Input_Power": 10,  # kW
            "Output_Power": 10,  # kW
            "Self_Discharge": 0.1,  # 1
            "Capacity": 200,  # kWh
            "Eff_Inflow": 0.98,  # 1
            "Eff_Outflow": 0.98,  # 1
        }
        sizing["CHP"] = {
            "ElectricPower": 30,  # kW
            "ThermalPower": 60,  # kW
            "ElectricEfficiency": 0.3,  # 1
            "ThermalEfficiency": 0.6,  # 1
        }

        JSON_DIR = join(RAW_DATA_DIR, "district_sizing.json")

        with open(JSON_DIR, 'w') as fp:
            json.dump(sizing, fp)
    
    elif os.path.exists(sizing):
        with open(sizing) as json_file:
            sizing = json.load(json_file)
        
        
    # Create Energy System with the dataframe time series
    energy_system = EnergySystem(timeindex=boundary_data.index)

    # Buses
    b_renewable = Bus(label="b_renewable")
    b_el_out = Bus(label="b_el_out", inputs={b_renewable: Flow()})
    b_electric_supply = Bus(label="b_electric_supply",
                            inputs={b_renewable: Flow()})
    b_heat_gas = Bus(label="b_gas")
    b_heat_supply = Bus(label="b_heat_supply")

    energy_system.add(
        b_electric_supply,
        b_renewable,
        b_el_out,
        b_heat_gas,
        b_heat_supply)

    # Energy Sources
    s_electric_grid = Source(
        label="s_electric_grid",
        outputs={
            b_electric_supply: Flow(
                variable_costs=market_data["day_ahead"] / 1000)})  # EUR/kWh

    s_gas = Source(
        label='m_gas',
        outputs={
            b_heat_gas: Flow(
                variable_costs=GAS_PRICE / 1000)})  # EUR/kWh

    # Create local energy demand
    d_el = Sink(label='d_el',
                inputs={
                    b_electric_supply: Flow(
                        fix=boundary_data['Electricity'],
                        nominal_value=1
                    )})

    d_heat = Sink(label='d_heat',
                  inputs={
                      b_heat_supply: Flow(
                          fix=boundary_data['Heat'],
                          nominal_value=1
                      )})

    energy_system.add(s_electric_grid, s_gas, d_el, d_heat)

    # Technologies

    # Photovoltaic
    s_pv = Source(
        label="s_pv",
        outputs={
            b_renewable: Flow(
                nominal_value=1,
                max=boundary_data["PV_pu"] *
                sizing["PV"])})
    # Boiler
    t_boiler = Transformer(
        label='t_boiler',
        inputs={b_heat_gas: Flow()},
        outputs={
            b_heat_supply: Flow(nominal_value=sizing["Boiler"]['Power'])},
        conversion_factors={
            b_heat_gas: 1,
            b_heat_supply: sizing["Boiler"]['Eff']})

    # Electric Battery
    sto_battery = GenericStorage(
        label='sto_battery',
        inputs={
            b_renewable: Flow(nominal_value=sizing["Battery"]["Input_Power"])},
        outputs={
            b_renewable: Flow(nominal_value=sizing["Battery"]["Output_Power"])},
        loss_rate=sizing["Battery"]["Self_Discharge"],
        nominal_storage_capacity=sizing["Battery"]["Capacity"],
        inflow_conversion_factor=sizing["Battery"]["Eff_Inflow"],
        outflow_conversion_factor=sizing["Battery"]["Eff_Outflow"],
        initial_storage_level=0,
        balanced=False)

    # CHP
    # TODO: MTTRES Model GenericCHP
    t_chp = Transformer(
        label='t_chp',
        inputs={b_heat_gas: Flow()},
        outputs={
            b_renewable: Flow(nominal_value=sizing["CHP"]["ElectricPower"]),
            b_heat_supply: Flow(nominal_value=sizing["CHP"]["ElectricPower"])},
        conversion_factors={
            b_renewable: sizing["CHP"]["ElectricEfficiency"],
            b_heat_supply: sizing["CHP"]["ThermalEfficiency"]})

    if sizing["Boiler"]['Power'] + \
            sizing["CHP"]["ElectricPower"] < boundary_data["Heat"].max():
        raise AssertionError(
            "Thermal power not enough for district. Cheack Boiler and CHP Sizes")

    energy_system.add(t_boiler, s_pv, sto_battery, t_chp)

    # Markets
    s_day_ahead = Sink(
        label="s_da",
        inputs={
            b_el_out: Flow(
                variable_costs=-
                market_data["day_ahead"] /
                1000)})

    s_intraday = Sink(
        label="s_id",
        inputs={
            b_el_out: Flow(
                variable_costs=-
                market_data["intra_day"] /
                1000)})

    s_future_base = Sink(
        label="s_fb",
        inputs={
            b_el_out: Flow(
                variable_costs=-
                market_data["future_base"] /
                1000)})

    s_future_peak = Sink(
        label="s_fp",
        inputs={
            b_el_out: Flow(
                variable_costs=-
                market_data["future_peak"] /
                1000)})

    energy_system.add(s_day_ahead, s_intraday, s_future_base, s_future_peak)

    return energy_system


def build_model_and_constraints(energy_system):
    '''
    Build a pyomo Model and add constraints for the proper sinks

    :param energy_system: Energy System with the appropiate markets.
    '''
    DAYS = int(energy_system.timeindex.size / 24 / 4)
    # Build model
    model = Model(energy_system)

    # Add Market Constraints

    # Constraint for the Day Ahead Market
    # i = inflow
    # o = outflow
    flows = {}
    for (i, o) in model.flows:
        if str(i) == "b_el_out" and str(o) == "s_da":
            flows[(i, o)] = model.flows[i, o]

    for (i, o) in flows:
        for t in model.TIMESTEPS:
            if t % 4 != 0:
                # ToDo: Change name to day_ahead
                limit_name = "intraday_markets_{}={}".format(t, t - t % 4)
                setattr(model, limit_name, po.Constraint(
                    rule=(model.flow[i, o, t] - model.flow[i, o, t - t % 4] == 0)))

    # Constraint for the Future Peak
    # ToDo: Exchange peak and base naming
    flows = {}

    for (i, o) in model.flows:
        if str(i) == "b_el_out" and str(o) == "s_fb":
            flows[(i, o)] = model.flows[i, o]

    for (i, o) in flows:
        for t in model.TIMESTEPS:
            if t != 0:
                limit_name = "future_base_{}={}".format(t, 0)
                setattr(model, limit_name, po.Constraint(
                    rule=(model.flow[i, o, t] - model.flow[i, o, 0] == 0)))

    # Constraint for the Future Base
    # what are the time steps for decision making?
    # 8*4+1 == 33 -> 32 is the time step for 8:00 AM

    flows = {}
    for (i, o) in model.flows:
        if str(i) == "b_el_out" and str(o) == "s_fp":
            flows[(i, o)] = model.flows[i, o]

    times_future_base = [32 + 96 * d for d in range(DAYS)]
    times_future_base_constraint = [
        [time_step + j for j in range(0, 4 * 13)] for time_step in times_future_base]

    tfb = []
    for l in times_future_base_constraint:
        for e in l:
            tfb.append(e)

    for time_step in tfb[1:]:  # for each day
        # range = 12*4 #time steps for the constraint, 13 hrs after 8 am, until
        # 20:45
        # the last bit of the 13h is not included
        t0 = tfb[0]
        for (i, o) in flows:
            limit_name = "future_peak_{}={}".format(time_step, t0)
            setattr(model, limit_name, po.Constraint(
                rule=(model.flow[i, o, t0] - model.flow[i, o, time_step] == 0)))

    times_fb_null = [
        t for t in model.TIMESTEPS if t not in tfb]
    for t in times_fb_null:
        limit_name = "future_peak_null_{}".format(t)
        setattr(
            model,
            limit_name,
            po.Constraint(
                rule=(
                    model.flow[i, o, t] == 0)))

    return model


def solve_model(model):
    '''
    Solve the constrained model

    :param model: oemof.solph model.
    '''
    # Solve the model
    model.solve(solver="cbc",
                solve_kwargs={'tee': False},
                solver_io='lp',
                cmdline_options={'ratio': 0.1})
    energy_system = model.es
    if model.solver_results.Solver[0].Status != "ok":
        raise AssertionError("Solver did not converge. Stopping simulation")

    energy_system.results['valid'] = True
    energy_system.results['solve_and_write_data'] = processing.results(
        model)
    energy_system.results['solve_and_write_data'] = views.convert_keys_to_strings(
        energy_system.results['solve_and_write_data'])
    energy_system.results['meta'] = processing.meta_results(
        model)

    return energy_system


def post_process_results(energy_system):
    '''
    Process Results into a nicer Data Frame

    :param energy_system: Solved energy system
    '''

    results = energy_system.results['solve_and_write_data']
    results_list = []
    for k in results.keys():
        if "flow" in list(results[k]['sequences'].keys()):
            flow = results[k]['sequences']['flow']
            if True:
                key_name = str(k)
                for s in [
                        "(", "'", ")"]:  # remove ( ' ) characters
                    key_name = key_name.replace(s, "")
                flow.rename(key_name, inplace=True)
                flow_df = pd.DataFrame(flow)
                results_list.append(flow_df)
    results = pd.concat(results_list, axis=1)

    return results


def save_results(results, year, scenario):
    '''
    Save the results in cleaner dataframes and in a graphic
    
    :param results: Results dataframe
    :param year: Year of the analysis
    :param scenario: Scenario number
    '''
    columns = results.columns

    # Get the results of selling energy
    res_sell = [c for c in columns if "b_el_out" in c.split(",")[0]]
    styles = ['b', 'r:', 'y-.', 'g-.']
    results[res_sell].plot(figsize=(16, 12), style=styles)

    results.to_csv(
        join(RESULTS_DATA_DIR, "MarketResults{}-Sc{}.csv".format(year, scenario.value)))
    plt.savefig(
        join(RESULTS_VIS_DIR, "MarketResults{}-Sc{}.jpg".format(year, scenario.value)))
    logging.info(
        f"Results saved for year {year} and Scenario {scenario.value}")


def create_and_solve_scenario(days=7, year=2017, sizing=None, scenario=1):
    '''
    Chain of functions to model the different scenarios 
    
    :param days: Number of days
    :param year: Year of simulation
    :param sizing: Sizing data. Can be empty and default data will be passed
    :param scenario: Scenario Enum value
    '''

    boundary_data = get_district_dataframe(year=year).head(days * 24 * 4)
    market_data = get_market_dataframe(days=days, year=year, scenario=scenario)
    energy_system = create_energy_system(boundary_data, market_data, sizing)
    model = build_model_and_constraints(energy_system)
    solved_energy_system = solve_model(model)
    results = post_process_results(solved_energy_system)
    save_results(results, year, scenario)


def main(year=2019,days=28):
    for scenario in Scenarios:
        create_and_solve_scenario(days=days,year=year, scenario=scenario)


if __name__ == '__main__':
    main(year=2019,days=28)

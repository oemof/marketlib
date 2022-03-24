'''
Created on 23 Mar 2022

@author: Fernando Penaherrera @UOL/OFFIS
'''

import pyomo.environ as po
from oemof.solph import Model


def build_model_and_constraints(energy_system):
    '''
    Build a pyomo Model and add constraints for the proper sinks

    :param energy_system: Energy System with the appropiate markets.
    '''
    # Build model
    model = Model(energy_system)

    # Before anything I need the shape of the future_peak in the shape of 1
    # and 0

    # electric bus
    bus_el_out = [n for n in energy_system.nodes if n.label == "b_el_out"][0]
    # check output
    key = [k for k in bus_el_out.outputs.keys() if "s_fp" in str(k)][0]
    future_base_flow_price = bus_el_out.outputs[key].variable_costs

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
                limit_name = "day_ahead_{}={}".format(t, t - t % 4)
                setattr(model, limit_name, po.Constraint(
                    rule=(model.flow[i, o, t] - model.flow[i, o, t - t % 4] == 0)))

    # Constraint for the Future Peak
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
    # I rather look at the shape of the cost of the flow to see
    # if the price is 0, then constraint is 0
    # if price is not 0, then the price is equal

    flows = {}
    for (i, o) in model.flows:
        if str(i) == "b_el_out" and str(o) == "s_fp":
            flows[(i, o)] = model.flows[i, o]

    times_future_base_constraint = [t for t in model.TIMESTEPS if abs(
        future_base_flow_price[t]) > 0.001]  # a small tolerance there

    for time_step in times_future_base_constraint[1:]:  # for each day
        # range = 12*4 #time steps for the constraint, 13 hrs after 8 am, until
        # 20:45
        # the last bit of the 13h is not included
        t0 = times_future_base_constraint[0]
        for (i, o) in flows:
            limit_name = "future_peak_{}={}".format(time_step, t0)
            setattr(model, limit_name, po.Constraint(
                rule=(model.flow[i, o, t0] - model.flow[i, o, time_step] == 0)))

    times_fb_null = [
        t for t in model.TIMESTEPS if t not in times_future_base_constraint]
    for t in times_fb_null:
        limit_name = "future_peak_null_{}".format(t)
        setattr(
            model,
            limit_name,
            po.Constraint(
                rule=(
                    model.flow[i, o, t] == 0)))

    return model


if __name__ == '__main__':
    pass

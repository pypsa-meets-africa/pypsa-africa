# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
Adds extra extendable components to the clustered and simplified network.

Relevant Settings
-----------------

.. code:: yaml

    costs:
        year:
        version:
        rooftop_share:
        USD2013_to_EUR2013:
        dicountrate:
        emission_prices:

    electricity:
        max_hours:
        marginal_cost:
        capital_cost:
        extendable_carriers:
            StorageUnit:
            Store:

.. seealso::
    Documentation of the configuration file ``config.yaml`` at :ref:`costs_cf`,
    :ref:`electricity_cf`

Inputs
------

- ``resources/costs.csv``: The database of cost assumptions for all included technologies for specific years from various sources; e.g. discount rate, lifetime, investment (CAPEX), fixed operation and maintenance (FOM), variable operation and maintenance (VOM), fuel costs, efficiency, carbon-dioxide intensity.

Outputs
-------

- ``networks/elec_s{simpl}_{clusters}_ec.nc``:


Description
-----------

The rule :mod:`add_extra_components` attaches additional extendable components to the clustered and simplified network. These can be configured in the ``config.yaml`` at ``electricity: extendable_carriers:``. It processes ``networks/elec_s{simpl}_{clusters}.nc`` to build ``networks/elec_s{simpl}_{clusters}_ec.nc``, which in contrast to the former (depending on the configuration) contain with **zero** initial capacity

- ``StorageUnits`` of carrier 'H2' and/or 'battery'. If this option is chosen, every bus is given an extendable ``StorageUnit`` of the corresponding carrier. The energy and power capacities are linked through a parameter that specifies the energy capacity as maximum hours at full dispatch power and is configured in ``electricity: max_hours:``. This linkage leads to one investment variable per storage unit. The default ``max_hours`` lead to long-term hydrogen and short-term battery storage units.

- ``Stores`` of carrier 'H2' and/or 'battery' in combination with ``Links``. If this option is chosen, the script adds extra buses with corresponding carrier where energy ``Stores`` are attached and which are connected to the corresponding power buses via two links, one each for charging and discharging. This leads to three investment variables for the energy capacity, charging and discharging capacity of the storage unit.
"""
import os

import numpy as np
import pandas as pd
import pypsa
from _helpers import configure_logging, create_logger, read_csv_nafix
from add_electricity import (
    _add_missing_carriers_from_costs,
    add_nice_carrier_names,
    calculate_annuity,
    load_costs,
)

idx = pd.IndexSlice

logger = create_logger(__name__)


def attach_storageunits(n, costs, config):
    elec_opts = config["electricity"]
    carriers = elec_opts["extendable_carriers"]["StorageUnit"]
    max_hours = elec_opts["max_hours"]

    _add_missing_carriers_from_costs(n, costs, carriers)

    buses_i = n.buses.index

    lookup_store = {"H2": "electrolysis", "battery": "battery inverter"}
    lookup_dispatch = {"H2": "fuel cell", "battery": "battery inverter"}

    for carrier in carriers:
        n.madd(
            "StorageUnit",
            buses_i,
            " " + carrier,
            bus=buses_i,
            carrier=carrier,
            p_nom_extendable=True,
            capital_cost=costs.at[carrier, "capital_cost"],
            marginal_cost=costs.at[carrier, "marginal_cost"],
            efficiency_store=costs.at[lookup_store[carrier], "efficiency"],
            efficiency_dispatch=costs.at[lookup_dispatch[carrier], "efficiency"],
            max_hours=max_hours[carrier],
            cyclic_state_of_charge=True,
        )


def attach_stores(n, costs, config):
    elec_opts = config["electricity"]
    carriers = elec_opts["extendable_carriers"]["Store"]

    _add_missing_carriers_from_costs(n, costs, carriers)

    buses_i = n.buses.index
    bus_sub_dict = {k: n.buses[k].values for k in ["x", "y", "country"]}

    if "H2" in carriers:
        h2_buses_i = n.madd("Bus", buses_i + " H2", carrier="H2", **bus_sub_dict)

        n.madd(
            "Store",
            h2_buses_i,
            bus=h2_buses_i,
            carrier="H2",
            e_nom_extendable=True,
            e_cyclic=True,
            capital_cost=costs.at["hydrogen storage tank", "capital_cost"],
        )

        n.madd(
            "Link",
            h2_buses_i + " Electrolysis",
            bus0=buses_i,
            bus1=h2_buses_i,
            carrier="H2 electrolysis",
            p_nom_extendable=True,
            efficiency=costs.at["electrolysis", "efficiency"],
            capital_cost=costs.at["electrolysis", "capital_cost"],
            marginal_cost=costs.at["electrolysis", "marginal_cost"],
        )

        n.madd(
            "Link",
            h2_buses_i + " Fuel Cell",
            bus0=h2_buses_i,
            bus1=buses_i,
            carrier="H2 fuel cell",
            p_nom_extendable=True,
            efficiency=costs.at["fuel cell", "efficiency"],
            capital_cost=costs.at["fuel cell", "capital_cost"]
            * costs.at["fuel cell", "efficiency"],
            marginal_cost=costs.at["fuel cell", "marginal_cost"],
        )

    if "battery" in carriers:
        b_buses_i = n.madd(
            "Bus", buses_i + " battery", carrier="battery", **bus_sub_dict
        )

        n.madd(
            "Store",
            b_buses_i,
            bus=b_buses_i,
            carrier="battery",
            e_cyclic=True,
            e_nom_extendable=True,
            capital_cost=costs.at["battery storage", "capital_cost"],
            marginal_cost=costs.at["battery", "marginal_cost"],
        )

        n.madd(
            "Link",
            b_buses_i + " charger",
            bus0=buses_i,
            bus1=b_buses_i,
            carrier="battery charger",
            efficiency=costs.at["battery inverter", "efficiency"],
            capital_cost=costs.at["battery inverter", "capital_cost"],
            p_nom_extendable=True,
            marginal_cost=costs.at["battery inverter", "marginal_cost"],
        )

        n.madd(
            "Link",
            b_buses_i + " discharger",
            bus0=b_buses_i,
            bus1=buses_i,
            carrier="battery discharger",
            efficiency=costs.at["battery inverter", "efficiency"],
            p_nom_extendable=True,
            marginal_cost=costs.at["battery inverter", "marginal_cost"],
        )

    if ("csp" in config["renewable"].keys()) and (
        config["renewable"]["csp"]["csp_model"] == "advanced"
    ):
        # add buses for csp
        n.madd("Bus", buses_i + " csp", carrier="csp", **bus_sub_dict)

        csp_buses_i = n.buses.index[n.buses.index.str.contains("csp")]

        # change bus of existing csp generators
        old_csp_bus_vector = buses_i + " csp"
        n.generators.loc[old_csp_bus_vector, "bus"] = csp_buses_i

        # add stores for csp
        n.madd(
            "Store",
            csp_buses_i,
            bus=csp_buses_i,
            carrier="csp",
            e_cyclic=True,
            e_nom_extendable=True,
            capital_cost=costs.at["csp-tower TES", "capital_cost"],
            marginal_cost=costs.at["csp-tower TES", "marginal_cost"],
        )

        # add links for csp
        n.madd(
            "Link",
            csp_buses_i,
            bus0=csp_buses_i,
            bus1=buses_i,
            carrier="csp",
            efficiency=costs.at["csp-tower", "efficiency"],
            capital_cost=costs.at["csp-tower", "capital_cost"],
            p_nom_extendable=True,
            marginal_cost=costs.at["csp-tower", "marginal_cost"],
        )


def attach_cooking_technologies(n, cooking_costs, config):
    if config["clean_cooking"]["enable"] != True:
        return

    carriers = config["clean_cooking"]["fuel"]
    cooking_costs = cooking_costs
    buses_i = n.buses.index
    buses_i = [
        bus for bus in buses_i if not (bus.endswith("battery") or bus.endswith("H2"))
    ]

    bus_sub_dict = {k: n.buses[k].values for k in ["x", "y", "country"]}
    for key in bus_sub_dict:
        bus_sub_dict[key] = bus_sub_dict[key][: len(buses_i)]

    cooking_buses_i = None
    if "heat" in carriers:
        cooking_buses_i = n.madd(
            "Bus", [bus + " cooking" for bus in buses_i], carrier="heat", **bus_sub_dict
        )

    for fuel in carriers:
        if fuel == "heat":
            continue

        if fuel == "AC" and "AC" in n.buses.carrier.values:
            fuel_buses_i = n.buses.index[n.buses.carrier == "AC"]
        else:
            fuel_buses_i = n.madd(
                "Bus",
                [bus + f" {fuel}" for bus in buses_i],
                carrier=fuel,
                **bus_sub_dict,
            )

            n.madd(
                "Store",
                fuel_buses_i,
                bus=fuel_buses_i,
                carrier=fuel,
                e_cyclic=fuel == "AC",
                e_initial=cooking_costs.at[fuel, "e_initial"],
                capital_cost=cooking_costs.at[fuel, "capital_cost"],
                marginal_cost=cooking_costs.at[fuel, "marginal_cost"],
            )

        if cooking_buses_i is not None:
            min_length = min(len(fuel_buses_i), len(cooking_buses_i))
            fuel_buses_i = fuel_buses_i[:min_length]
            cooking_buses_i = cooking_buses_i[:min_length]

            n.madd(
                "Link",
                fuel_buses_i + " stove",
                bus0=fuel_buses_i,
                bus1=cooking_buses_i,
                carrier=fuel,
                efficiency=cooking_costs.at[f"{fuel} stove", "efficiency"],
                capital_cost=cooking_costs.at[f"{fuel} stove", "capital_cost"],
                marginal_cost=cooking_costs.at[
                    f"{fuel} stove", "marginal_cost"
                ],  # differentiate between store and link
                p_nom=cooking_costs.at[f"{fuel} stove", "p_nom"],
            )


def attach_cooking_load(n, demand_cooking):
    demand_df = read_csv_nafix(demand_cooking, index_col=0, parse_dates=True)
    cooking_bus = n.buses.loc[n.buses.index.str.endswith("cooking")].index
    n.madd("Load", demand_df.columns, bus=cooking_bus, p_set=demand_df)


def load_cooking_costs(cooking_fuel_costs, config, Nyears=1):
    """
    Set all cooking costs and other parameters.
    """

    cooking_costs = pd.read_csv(
        cooking_fuel_costs, index_col=["technology", "parameter"]
    ).sort_index()

    cooking_costs.loc[cooking_costs.unit.str.contains("/kW"), "value"] *= 1e3
    cooking_costs.unit = cooking_costs.unit.str.replace("/kW", "/MW")

    cooking_costs = cooking_costs.value.unstack().fillna(config["costs"]["fill_values"])

    cooking_costs["capital_cost"] = (
        (
            calculate_annuity(cooking_costs["lifetime"], cooking_costs["discount rate"])
            + cooking_costs["FOM"] / 100.0
        )
        * cooking_costs["investment"]
        * Nyears
    )

    cooking_costs["marginal_cost"] = (
        cooking_costs["VOM"] + cooking_costs["fuel"] / cooking_costs["efficiency"]
    )

    cooking_costs = cooking_costs.rename(
        columns={"CO2 intensity": "co2_emissions", "capacity": "p_nom"}
    )

    def costs_for_storage(store, link, max_hours=1.0):
        capital_cost = link["capital_cost"] + max_hours * store["capital_cost"]
        return pd.Series(
            dict(capital_cost=capital_cost, marginal_cost=0.0, co2_emissions=0.0)
        )

    for i in config["clean_cooking"]["fuel"]:
        if i != "heat":
            cooking_costs.loc[i] = costs_for_storage(
                cooking_costs.loc[i],
                cooking_costs.loc[f"{i} stove"],
            )

    return cooking_costs


def attach_hydrogen_pipelines(n, costs, config):
    elec_opts = config["electricity"]
    ext_carriers = elec_opts["extendable_carriers"]
    as_stores = ext_carriers.get("Store", [])

    if "H2 pipeline" not in ext_carriers.get("Link", []):
        return

    assert "H2" in as_stores, (
        "Attaching hydrogen pipelines requires hydrogen "
        "storage to be modelled as Store-Link-Bus combination. See "
        "`config.yaml` at `electricity: extendable_carriers: Store:`."
    )

    # determine bus pairs
    attrs = ["bus0", "bus1", "length"]
    candidates = pd.concat(
        [n.lines[attrs], n.links.query('carrier=="DC"')[attrs]]
    ).reset_index(drop=True)

    # remove bus pair duplicates regardless of order of bus0 and bus1
    h2_links = candidates[
        ~pd.DataFrame(np.sort(candidates[["bus0", "bus1"]])).duplicated()
    ]
    h2_links.index = h2_links.apply(lambda c: f"H2 pipeline {c.bus0}-{c.bus1}", axis=1)

    # add pipelines
    n.madd(
        "Link",
        h2_links.index,
        bus0=h2_links.bus0.values + " H2",
        bus1=h2_links.bus1.values + " H2",
        p_min_pu=-1,
        p_nom_extendable=True,
        length=h2_links.length.values,
        capital_cost=costs.at["H2 pipeline", "capital_cost"] * h2_links.length,
        efficiency=costs.at["H2 pipeline", "efficiency"],
        carrier="H2 pipeline",
    )


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        snakemake = mock_snakemake("add_extra_components", simpl="", clusters=10)
    configure_logging(snakemake)

    n = pypsa.Network(snakemake.input.network)
    Nyears = n.snapshot_weightings.objective.sum() / 8760.0
    config = snakemake.config

    costs = load_costs(
        snakemake.input.tech_costs,
        config["costs"],
        config["electricity"],
        Nyears,
    )

    attach_storageunits(n, costs, config)
    attach_stores(n, costs, config)
    cooking_costs = load_cooking_costs(snakemake.input.cooking_costs, config, Nyears=1)
    attach_cooking_technologies(n, cooking_costs, config)
    attach_cooking_load(n, snakemake.input.demand_cooking)
    attach_hydrogen_pipelines(n, costs, config)

    add_nice_carrier_names(n, config=snakemake.config)

    n.meta = dict(snakemake.config, **dict(wildcards=dict(snakemake.wildcards)))
    n.export_to_netcdf(snakemake.output[0])

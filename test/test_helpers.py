# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import pathlib

import numpy as np
import pandas as pd

from scripts._helpers import (
    aggregate_fuels,
    country_name_2_two_digits,
    get_conv_factors,
    modify_commodity,
    safe_divide,
    sets_path_to_root,
    three_2_two_digits_country,
    two_2_three_digits_country,
    two_digits_2_name_country,
)

path_cwd = pathlib.Path.cwd()

original_commodity_data = [
    "Biogases",
    "Fuelwood",
    "of which: fishing",
    "Natural gas liquids",
    "Naphtha",
    "Motor Gasoline",
    "Motor gasoline",
    "Gasoline-type jet fuel",
    "Peat products",
    "Peat Products",
    "Direct use of geothermal heat",
    "Additives and Oxygenates",
    "Electricity",
    "Animal waste",
    "animal waste",
    "Refinery gas",
    "Refinery Gas",
    "Fuel oil",
    "Oil shale",
    "Oil Shale",
    "Lignite",
    "Falling water",
    "Petroleum coke",
    "Petroleum Coke",
    "Aviation gasoline",
    "Ethane",
    "Natural gas (including LNG)",
    "Natural gas",
    "Natural Gas (including LNG)",
    "Other bituminous coal",
    "Paraffin waxes",
    "Hard coal",
    "Coal",
    "Hrad coal",
    "Coke Oven Gas",
    "Gasworks Gas",
    "Brown coal briquettes",
    "Brown Coal Briquettes",
    "Liquefied petroleum gas (LPG)",
    "Liquified Petroleum Gas (LPG)",
    "Sub-bituminous coal",
    "Kerosene-type Jet Fuel",
    "Charcoal",
    "Heat",
    "Gas coke",
    "Gas Coke",
    "Patent fuel",
    "Peat (for fuel use)",
    "Peat",
    "Coal Tar",
    "Biogasoline",
    "Coking coal",
    "Electricity generating capacity",
    "Anthracite",
    "Coke oven coke",
    "Coke-oven coke",
    "Coke Oven Coke",
    "Conventional crude oil",
    "Crude petroleum",
    "Brown coal",
    "Lignite brown coal",
    "Lignite brown coal- recoverable resources",
    "Biodiesel",
    "Lubricants",
    "Black Liquor",
    "Gas Oil/ Diesel Oil",
    "Gas Oil/ Diesel Oil ",
    "Gas Oil/Diesel Oil",
    "Bagasse",
    "Direct use of solar thermal heat",
    "Bio jet kerosene",
    "Blast Furnace Gas",
    "Blast furnace gas",
    "Bitumen",
]

modified_commodity_data = [
    "biogases",
    "fuelwood",
    "of which: fishing",
    "natural gas liquids",
    "naphtha",
    "motor gasoline",
    "gasoline-type jet fuel",
    "peat products",
    "direct use of geothermal heat",
    "additives and oxygenates",
    "electricity",
    "animal waste",
    "refinery gas",
    "fuel oil",
    "oil shale",
    "lignite",
    "falling water",
    "petroleum coke",
    "aviation gasoline",
    "ethane",
    "natural gas (including lng)",
    "natural gas",
    "other bituminous coal",
    "paraffin waxes",
    "hard coal",
    "coal",
    "coke-oven gas",
    "gasworks gas",
    "brown coal briquettes",
    "liquefied petroleum gas (lpg)",
    "sub-bituminous coal",
    "kerosene-type jet fuel",
    "charcoal",
    "heat",
    "gas coke",
    "patent fuel",
    "peat (for fuel use)",
    "peat",
    "coal tar",
    "biogasoline",
    "coking coal",
    "electricity generating capacity",
    "anthracite",
    "coke-oven coke",
    "conventional crude oil",
    "crude petroleum",
    "brown coal",
    "lignite brown coal",
    "lignite brown coal - recoverable resources",
    "biodiesel",
    "lubricants",
    "black liquor",
    "gas oil/ diesel oil",
    "bagasse",
    "direct use of solar thermal heat",
    "bio jet kerosene",
    "blast furnace gas",
    "bitumen",
]

original_commodity_dataframe = pd.DataFrame(
    original_commodity_data, columns=["Commodity"]
)
modified_commodity_dataframe = pd.DataFrame(
    modified_commodity_data, columns=["Commodity"]
)


def test_sets_path_to_root():
    """
    Verify that the root folder returned by sets_path_to_root is pypsa-earth.
    """
    sets_path_to_root("pypsa-earth")
    current_path = pathlib.Path.cwd()
    assert current_path == path_cwd


def test_two_2_three_digits_country():
    """
    Verify the conversion from two-digit to three-digit country code.
    """
    # Afghanistan
    assert two_2_three_digits_country("AF") == "AFG"
    # American Samoa
    assert two_2_three_digits_country("AS") == "ASM"
    # Aruba
    assert two_2_three_digits_country("AW") == "ABW"
    # Germany
    assert two_2_three_digits_country("DE") == "DEU"
    # Micronesia (Federated States of)
    assert two_2_three_digits_country("FM") == "FSM"


def test_three_2_two_digits_country():
    """
    Verify the conversion from three-digit to two-digit country code.
    """
    # Afghanistan
    assert "AF" == three_2_two_digits_country("AFG")
    # American Samoa
    assert "AS" == three_2_two_digits_country("ASM")
    # Aruba
    assert "AW" == three_2_two_digits_country("ABW")
    # Germany
    assert "DE" == three_2_two_digits_country("DEU")
    # Micronesia (Federated States of)
    assert "FM" == three_2_two_digits_country("FSM")


def test_two_digits_2_name_country():
    """
    Verify the conversion from two-digit country code to country name.
    """
    # Micronesia (Federated States of)
    assert "Micronesia, Fed. Sts." == two_digits_2_name_country("FM")
    assert "Federated States of Micronesia" == two_digits_2_name_country(
        "FM", name_string="name_official"
    )
    assert "States of Micronesia" == two_digits_2_name_country(
        "FM", name_string="name_official", remove_start_words=["Federated "]
    )
    # Democratic Republic of the Congo
    assert "DR Congo" == two_digits_2_name_country("CD")
    assert "Democratic Republic of the Congo" == two_digits_2_name_country(
        "CD", name_string="name_official"
    )
    assert "Republic of the Congo" == two_digits_2_name_country(
        "CD", name_string="name_official", remove_start_words=["Democratic "]
    )


def test_country_name_2_two_digits():
    """
    Verify the conversion from country name to two-digit country code.
    """
    # Afghanistan
    assert "AF" == country_name_2_two_digits("Afghanistan")
    # American Samoa
    assert "AS" == country_name_2_two_digits("American Samoa")
    # Aruba
    assert "AW" == country_name_2_two_digits("Aruba")
    # Germany
    assert "DE" == country_name_2_two_digits("Germany")
    # Micronesia (Federated States of)
    assert "FM" == country_name_2_two_digits("Micronesia")


def test_safe_divide():
    """
    Verify that the method safe_divide prevents divisions by vanishing
    denominator.
    """
    assert safe_divide(3.0, 2.0) == 1.5
    assert np.isnan(safe_divide(3.0, 0.0))


def test_get_conv_factors():
    """
    Verify that the conversion factors returned by get_conv_factors are
    correct.
    """
    conversion_factors_dict = get_conv_factors("industry")
    assert conversion_factors_dict["additives and oxygenates"] == 0.008333
    assert conversion_factors_dict["anthracite"] == 0.005
    assert conversion_factors_dict["aviation gasoline"] == 0.01230
    assert conversion_factors_dict["bagasse"] == 0.002144
    assert conversion_factors_dict["biodiesel"] == 0.01022
    assert conversion_factors_dict["biogasoline"] == 0.007444
    assert conversion_factors_dict["bio jet kerosene"] == 0.011111
    assert conversion_factors_dict["bitumen"] == 0.01117
    assert conversion_factors_dict["brown coal"] == 0.003889
    assert conversion_factors_dict["brown coal briquettes"] == 0.00575
    assert conversion_factors_dict["charcoal"] == 0.00819
    assert conversion_factors_dict["coal tar"] == 0.007778
    assert conversion_factors_dict["coke-oven coke"] == 0.0078334
    assert conversion_factors_dict["coke-oven gas"] == 0.000277
    assert conversion_factors_dict["coking coal"] == 0.007833
    assert conversion_factors_dict["conventional crude oil"] == 0.01175
    assert conversion_factors_dict["crude petroleum"] == 0.011750
    assert conversion_factors_dict["ethane"] == 0.01289
    assert conversion_factors_dict["fuel oil"] == 0.01122
    assert conversion_factors_dict["fuelwood"] == 0.00254
    assert conversion_factors_dict["gas coke"] == 0.007326
    assert conversion_factors_dict["gas oil/ diesel oil"] == 0.01194
    assert conversion_factors_dict["gasoline-type jet fuel"] == 0.01230
    assert conversion_factors_dict["hard coal"] == 0.007167
    assert conversion_factors_dict["kerosene-type jet fuel"] == 0.01225
    assert conversion_factors_dict["lignite"] == 0.003889
    assert conversion_factors_dict["liquefied petroleum gas (lpg)"] == 0.01313
    assert conversion_factors_dict["lubricants"] == 0.011166
    assert conversion_factors_dict["motor gasoline"] == 0.01230
    assert conversion_factors_dict["naphtha"] == 0.01236
    assert conversion_factors_dict["natural gas liquids"] == 0.01228
    assert conversion_factors_dict["oil shale"] == 0.00247
    assert conversion_factors_dict["other bituminous coal"] == 0.005556
    assert conversion_factors_dict["paraffin waxes"] == 0.01117
    assert conversion_factors_dict["patent fuel"] == 0.00575
    assert conversion_factors_dict["peat"] == 0.00271
    assert conversion_factors_dict["peat products"] == 0.00271
    assert conversion_factors_dict["petroleum coke"] == 0.009028
    assert conversion_factors_dict["refinery gas"] == 0.01375
    assert conversion_factors_dict["sub-bituminous coal"] == 0.005555
    assert np.isnan(get_conv_factors("non-industry"))


def test_modify_commodity():
    """
    Verify that modify_commodity returns the commodities in wished format.
    """
    new_commodity_dataframe = pd.DataFrame()
    new_commodity_dataframe["Commodity"] = (
        original_commodity_dataframe["Commodity"].map(modify_commodity).unique()
    )
    df = new_commodity_dataframe.compare(modified_commodity_dataframe)
    boolean_flag = df.empty
    if not boolean_flag:
        assert False


def test_aggregate_fuels():
    """
    Verify what is returned by aggregate_fuels.
    """
    assert np.isnan(aggregate_fuels("non-industry"))

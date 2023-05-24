# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
Prepares network files with monte-carlo parameter sweeps for solving process.

Relevant Settings
-----------------

.. code:: yaml

    monte_carlo:
    options:
        add_to_snakefile:
        samples:
        sampling_strategy:
    pypsa_standard:
        <use dynamically the PyPSA object and define uncertainty ranges>
        Examples...
        loads_t.p_set: [0.9, 1.1]
        generators_t.p_max_pu.loc[:, n.generators.carrier == "wind"]: [0.9, 1.1]
        generators_t.p_max_pu.loc[:, n.generators.carrier == "solar"]: [0.9, 1.1]

.. seealso::
    Documentation of the configuration file ``config.yaml`` at :ref:`_monte_cf`

Inputs
------
- ``networks/elec_s_10_ec_lcopt_Co2L-24H.nc``

Outputs
-------
- ``networks/elec_s_10_ec_lcopt_Co2L-24H_{unc}.nc``
e.g.    networks/elec_s_10_ec_lcopt_Co2L-24H_m0.nc
        networks/elec_s_10_ec_lcopt_Co2L-24H_m1.nc
        ...

Description
-----------
PyPSA-Earth is deterministic which means that a set of inputs give a set of outputs.
Parameter sweeps can help to explore the uncertainty of the outputs cause by parameter changes.
Many are familiar with the classical "sensitivity analysis" that can be applied by varying the
input of only one feature, while exploring its outputs changes. Here implemented is a
"global sensitivity analysis" that can help to explore the multi-dimensional uncertainty space
when more than one feature are changed at the same time. 

To do so, the scripts is separated in two building blocks: One creates the experimental design,
the other, modifies and outputs the network file. Building the experimental design is currently
supported by the packages pyDOE2, chaospy and scipy. This should give users the freedom to
explore alternative approaches. The orthogonal latin hypercube sampling is thereby found as most
performant, hence, implemented here. Sampling the multi-dimensional uncertainty space is relatively
easy. It only requires two things: The number of *samples* (e.g. PyPSA networks) and *features* (e.g.
load or solar timeseries). This results in an experimental design of the dimension (samples X features).

Additionally, upper and lower bounds *per feature* need to be provided such that the experimental
design can be scaled accordingly. Currently the user can define uncertainty ranges e.g. bounds,
for all PyPSA objects that are `int` or `float`. Boolean values could be used but require testing.
The experimental design `lhs_scaled` (dimension: sample X features) is then used to modify the PyPSA
networks. Thereby, this script creates samples x amount of networks. The iterators comes from the
wildcard {unc}, which is described in the config.yaml and created in the Snakefile as a range from
0 to (total number of) SAMPLES. 
"""
import logging
import os

import chaospy
import numpy as np
import pandas as pd
import pypsa
from _helpers import configure_logging
from pyDOE2 import lhs
from scipy.stats import qmc
from solve_network import *

logger = logging.getLogger(__name__)


def wildcard_creator(config, method=None):
    """
    Creates wildcard for monte-carlo simulations.
    """
    method = config["monte_carlo"]["options"].get("method")
    if method == "global_sensitivity":
        return [f"g{i}" for i in range(config["monte_carlo"]["options"]["samples"])]

    elif method == "single_best_in_worst":
        return [
            f"a{i}"
            for i in range(len(config["electricity"]["extendable_carriers"]["Store"]))
        ]


def monte_carlo_sampling_pydoe2(
    N_FEATURES,
    SAMPLES,
    criterion=None,
    iteration=None,
    random_state=42,
    correlation_matrix=None,
):
    """
    Creates Latin Hypercube Sample (LHS) implementation from PyDOE2 with various options. Additionally all "corners" are simulated.

    Adapted from Disspaset: https://github.com/energy-modelling-toolkit/Dispa-SET/blob/master/scripts/build_and_run_hypercube.py
    Documentation on PyDOE2: https://github.com/clicumu/pyDOE2 (fixes latin_cube errors)
    """

    # Generate a Nfeatures-dimensional latin hypercube varying between 0 and 1:
    lh = lhs(
        N_FEATURES,
        samples=SAMPLES,
        criterion=criterion,
        iterations=iteration,
        random_state=random_state,
        correlation_matrix=correlation_matrix,
    )
    discrepancy = qmc.discrepancy(lh)
    logger.info("Hypercube discrepancy is:", discrepancy)

    return lh


def monte_carlo_sampling_chaospy(N_FEATURES, SAMPLES, rule="latin_hypercube", seed=42):
    """
    Creates Latin Hypercube Sample (LHS) implementation from chaospy.

    Documentation on Chaospy: https://github.com/clicumu/pyDOE2 (fixes latin_cube errors)
    Documentation on Chaospy latin-hyper cube (quasi-Monte Carlo method): https://chaospy.readthedocs.io/en/master/user_guide/fundamentals/quasi_random_samples.html#Quasi-random-samples

    """
    # Generate a Nfeatures-dimensional latin hypercube varying between 0 and 1:
    N_FEATURES = "chaospy.Uniform(0, 1), " * N_FEATURES
    uniform_cube = eval(
        f"chaospy.J({N_FEATURES})"
    )  # writes Nfeatures times the chaospy.uniform... command)
    lh = uniform_cube.sample(SAMPLES, rule=rule, seed=seed).T
    discrepancy = qmc.discrepancy(lh)
    logger.info("Hypercube discrepancy is:", discrepancy)

    return lh


def monte_carlo_sampling_scipy(
    N_FEATURES, SAMPLES, centered=False, strength=2, optimization=None, seed=42
):
    """
    Creates Latin Hypercube Sample (LHS) implementation from SciPy with various options:
    - Center the point within the multi-dimensional grid, centered=True
    - optimization scheme, optimization="random-cd"
    - strength=1, classical LHS
    - strength=2, performant orthogonal LHS, requires the sample to be a prime or square of a prime e.g. sqr(121)=11

    Options could be combined to produce an optimized centered orthogonal array
    based LHS. After optimization, the result would not be guaranteed to be of strength 2.

    Documentation for Quasi-Monte Carlo approaches: https://docs.scipy.org/doc/scipy/reference/stats.qmc.html
    Documentation for Latin Hypercube: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html#scipy.stats.qmc.LatinHypercube
    Orthogonal LHS is better than basic LHS: https://github.com/scipy/scipy/pull/14546/files, https://en.wikipedia.org/wiki/Latin_hypercube_sampling
    """
    sampler = qmc.LatinHypercube(
        d=N_FEATURES,
        centered=centered,
        strength=strength,
        optimization=optimization,
        seed=seed,
    )
    lh = sampler.random(n=SAMPLES)
    discrepancy = qmc.discrepancy(lh)
    logger.info("Hypercube discrepancy is:", discrepancy)

    return lh


def single_best_in_worst_list(worst_list, best_list):
    """
    Return list with single best value per list of worst values

    The goal is to create a list of scenarios where each scenario
    has one best value and the rest are worst cases. This is useful for
    assessing the impact of a single technology on the system.
    E.g. if a technology is not optimised in any best case, it is
    likely not relevant to include in the optimization or
    global sensitivity analysis.

    What is good and what is bad is determined by the user.
    See example below for clarification of use cases.

    Input:
    ------
    worst_list: 1D array, represents the worst value per technology
    best_list: 1D array, represents the best value per technology

    Output:
    -------
    new_list: 2D array

    Example:
    --------
    Let's create a scenario set with 3 technologies (creates 3 scenarios)
    # Scenario set when low values are good e.g. costs
    >>> single_best_in_worst_list([4, 4, 4], [1, 1, 1])
    [[1, 4, 4], [4, 1, 4], [4, 4, 1]]
    # Scenario set when high values are good e.g. efficiency
    >>> single_best_in_worst_list([1, 1, 1], [4, 4, 4])
    [[4, 1, 1], [1, 4, 1], [1, 1, 4]]
    """
    new_list = []
    for i in range(len(worst_list)):
        l = worst_list.copy()
        l[i] = best_list[i]
        new_list.append(l)

    return new_list


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        snakemake = mock_snakemake(
            "monte_carlo",
            simpl="",
            clusters="10",
            ll="copt",
            opts="Co2L-24H",
            unc="m0",
        )
    configure_logging(snakemake)
    config = snakemake.config
    n = pypsa.Network(snakemake.input[0])

    PYPSA_FEATURES = {
        k: v for k, v in config["monte_carlo"]["pypsa_standard"].items() if v
    }  # removes key value pairs with empty value e.g. []
    OPTIONS = config["monte_carlo"]["options"]
    L_BOUNDS = [item[0] for item in PYPSA_FEATURES.values()]
    U_BOUNDS = [item[1] for item in PYPSA_FEATURES.values()]
    N_FEATURES = len(PYPSA_FEATURES)  # only counts features when specified in config

    ### SCENARIO CREATION
    ###
    if OPTIONS.get("method") == "global_sensitivity":
        SAMPLES = OPTIONS.get(
            "samples"
        )  # TODO: What is the optimal sampling? Fabian Neumann answered that in "Broad ranges" paper
        SAMPLING_STRATEGY = OPTIONS.get("sampling_strategy")

        if SAMPLING_STRATEGY == "pydoe2":
            lh = monte_carlo_sampling_pydoe2(
                N_FEATURES,
                SAMPLES,
                criterion=None,
                iteration=None,
                random_state=42,
                correlation_matrix=None,
            )
        if SAMPLING_STRATEGY == "scipy":
            lh = monte_carlo_sampling_scipy(
                N_FEATURES,
                SAMPLES,
                centered=False,
                strength=2,
                optimization=None,
                seed=42,
            )
        if SAMPLING_STRATEGY == "chaospy":
            lh = monte_carlo_sampling_chaospy(
                N_FEATURES,
                SAMPLES,
                rule="latin_hypercube",
                seed=42,
            )
        scenarios = qmc.scale(lh, L_BOUNDS, U_BOUNDS)

    elif OPTIONS.get("method") == "single_best_in_worst":
        carrier_no = len(n.stores.carrier.unique())
        worst_list = U_BOUNDS * carrier_no
        best_list = L_BOUNDS * carrier_no
        scenarios = single_best_in_worst_list(worst_list, best_list)

    ### NETWORK MODIFICATION
    ###
    unc_wildcards = snakemake.wildcards[-1]
    i = int(unc_wildcards[1:])
    j = 0

    if OPTIONS.get("method") == "global_sensitivity":
        for k, v in PYPSA_FEATURES.items():
            # this loop sets in one scenario each "i" feature assumption
            # k is the config input key "loads_t.p_set"
            # v is the lower and upper bound [0.8,1.3], that was used for scenarios
            # i, j interation number to pick values of experimental setup
            # Example: n.loads_t.p_set = n.loads_t.p_set * scenarios[0,0]
            exec(f"n.{k} = n.{k} * {scenarios[i,j]}")
            logger.info(f"Scaled n.{k} by factor {scenarios[i,j]} in the {i} scenario")
            j = j + 1

    if OPTIONS.get("method") == "single_best_in_worst":
        for k, _ in PYPSA_FEATURES.items():
            type = k.split(".")[0]  # "stores", "generators", ...
            feature = k.split(".")[1]  # "capital_cost", "efficiency", ...

        # TODO: Generalize for other features. Currently this scales the whole storage-chain
        if type == "stores":
            # scales the whole storage-chain
            carrier_list = n.stores.carrier.unique()
            for c in carrier_list:
                n.stores.loc[n.stores.carrier == c, feature] *= scenarios[i][j]
                n.links.loc[n.links.carrier.str.contains("H2"), feature] *= scenarios[
                    i
                ][j]
                logger.info(
                    f"Scaled {feature} for carrier={c} of store and links by factor {scenarios[i][j]} in the {i} scenario"
                )
                j += 1

    ### EXPORT AND METADATA
    ###
    scenario_dict = (
        pd.DataFrame(scenarios).rename_axis("iteration").add_suffix("_feature")
    ).to_dict()
    n.meta.update(scenario_dict)
    n.export_to_netcdf(snakemake.output[0])

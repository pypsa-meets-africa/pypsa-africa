# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-

import logging

import yaml

logger = logging.getLogger(__name__)

# definitions of output blocks ------------------------------------------------
# model_keys = [
#   "version", "tutorial", "foresight", "countries",
#   "scenario", "snapshots", "enable", "run",
#   "clean_osm_data_options", "build_osm_network", "base_network",
#   "build_shape_options",
#   "electricity", "lines", "links", "transformers",
#   "load_options", "demand_data",
#   "augmented_line_connection",
#   "cluster_options",
#   "atlite", "renewable", "solar_thermal",
#   "policy_config", "fossil_reserves",
#   "sector", "export", "industry"
#   "custom_data", "existing_capacities", "costs",
#   "monte_carlo", "solving",
#   "plotting", "crs",
# ]

major_run_keys = [
    "version",
    "tutorial",
    "foresight",
    "countries",
    "enable",
    "run",
]
major_model_keys = [
    "scenario",
    "snapshots",
]
grid_model_keys = [
    "clean_osm_data_options",
    "build_osm_network",
    "base_network",
]
electrycity_model_keys = ["electricity"]

# visual settings -------------------------------------------------------------
style = """<style type='text/css'>
html {
  font-family: Georgia;
}
r {
  color: #ff0000;
  background-color: coral;
}
g {
  color: #00ff00;
  background-color: coral;
}
b {
  color: #0000ff;
  background-color: grey;
}
blue_bg {
  color: #36454F;
  background-color: #A7C8FF;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
mint_bg {
  color: #36454F;
  background-color: #B7E5D5;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
coral_bg {
  color: #36454F;
  background-color: #FF9E9E;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
lavend_bg {
  color: #36454F;
  background-color: #D8ADEF;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
gold_bg {
  color: #36454F;
  background-color: #F9C6A1;
  width: 100%;
  background-size: contain;
  display:inline-block;
}

blue_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #A7C8FF;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
mint_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #B7E5D5;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
coral_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #FF9E9E;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
lavend_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #D8ADEF;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
gold_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #F9C6A1;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
</style>"""


def write_html(style, fl, type, str_):
    fl.write("<%(type)s>%(str)s</%(type)s>" % {"type": type, "str": str_})


def write_dict_key(
    header, dict, style_text, style_header, style_def=style, fl_name="out.html"
):

    # define styles to be used in htmls generated below
    coral_bg = "coral_bg"
    mint_bg = "mint_bg"
    blue_bg = "blue_bg"

    content_str = yaml.dump(dict)

    clean_str = (
        content_str.replace("\t", "     ")
        .replace("\n", "<br />")
        .replace("\r", "<br />")
    )
    # clean_str = content_str.replace("\n", ", ")#.replace("\r", "<br />")

    # f = open(fl_name, "w")
    f = open(fl_name, "a")

    f.write("<html>")
    f.write(style)

    write_html(
        style=style_def,
        fl=f,
        type=style_text,
        str_="------------------------------------------ <br />",
    )
    write_html(style=style_def, fl=f, type=style_header, str_=header + "<br />")
    write_html(
        style=style_def,
        fl=f,
        type=style_text,
        str_="------------------------------------------ <br />",
    )
    write_html(style=style_def, fl=f, type=style_text, str_=clean_str)

    write_html(style=style_def, fl=f, type=mint_bg, str_="<br />")
    # write_html(
    #     style=style_def,
    #     fl=f,
    #     type=style_text,
    #     str_="------------------------------------------ <br /><br />",
    # )

    f.write("</html>")

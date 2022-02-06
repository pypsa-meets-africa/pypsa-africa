# Copyright 2019-2020 Fabian Hofmann (FIAS)
# SPDX-FileCopyrightText: : 2017-2020 The PyPSA-Eur Authors, 2021 PyPSA-Africa
#
# SPDX-License-Identifier: MIT
"""
.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.3517935.svg
   :target: https://doi.org/10.5281/zenodo.3517935

The data bundle (1.4 GB) contains common GIS datasets like NUTS3 shapes, EEZ shapes, CORINE Landcover, Natura 2000 and also electricity specific summary statistics like historic per country yearly totals of hydro generation, GDP and POP on NUTS3 levels and per-country load time-series.

This rule downloads the data bundle from `zenodo <https://doi.org/10.5281/zenodo.3517935>`_ and extracts it in the ``data`` sub-directory, such that all files of the bundle are stored in the ``data/bundle`` subdirectory.

The :ref:`tutorial` uses a smaller `data bundle <https://zenodo.org/record/3517921/files/pypsa-eur-tutorial-data-bundle.tar.xz>`_ than required for the full model (19 MB)

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.3517921.svg
    :target: https://doi.org/10.5281/zenodo.3517921

**Relevant Settings**

.. code:: yaml

    tutorial:

.. seealso::
    Documentation of the configuration file ``config.yaml`` at
    :ref:`toplevel_cf`

**Outputs**

- ``cutouts/bundle``: input data collected from various sources

"""
import logging
import os
import tarfile
from pathlib import Path
import yaml
from zipfile import ZipFile

from _helpers import _sets_path_to_root
from _helpers import configure_logging
from _helpers import progress_retrieve
from download_osm_data import create_country_list
from google_drive_downloader import GoogleDriveDownloader as gdd

logger = logging.getLogger(__name__)

def load_databundle_config(path):
    "Load databundle configurations from path file"

    config = yaml.load(path, Loader=yaml.FullLoader)

    # parse the "countries" list specified in the file before processing
    for bundle_name in config:
        config["countries"] = create_country_list(config["countries"])
    
    return config

def download_and_unzip(host, resource, url, file_path, remove_file=True):
    """
    Function to download and unzip data depending on the hosting platform.
    Currently, hosts accepted: zenodo and google
    """

    if host=="zenodo":
        progress_retrieve(url, file_path)
        logger.info(f"Extracting resources")
        with ZipFile(file_path, "r") as zipObj:
            # Extract all the contents of zip file in current directory
            zipObj.extractall()
        if remove_file:
            os.remove(file_path)
        logger.info(f"Download data to '{destination}' from cloud '{url}'.")
    elif host=="google":

        # retrieve file_id from path
        partition_view = str(url).split("/view", 1)  # cut the part before the ending \view
        if len(partition_view) < 2:
            logger.error(f"Resource {resource} cannot be downloaded: \"\\view\" not found in url {url}")
            return
        
        code_split = partition_view[0].rsplit("\\", 1)  # split url to get the file_id

        if len(partition_view) < 2:
            logger.error(f"Resource {resource} cannot be downloaded: character \"\\\" not found in {partition_view[0]}")
            return
        
        # get file id
        file_id = code_split[1]

        gdd.download_file_from_google_drive(
            file_id=file_id,
            dest_path=file_path,
            showsize=True,
            unzip=True,
        )
        if remove_file:
            os.remove(file_path)
        logger.info(f"Download data to '{destination}' from cloud '{url}'.")
        
    else:
        logger.error(f"Host {host} not implemented")

if __name__ == "__main__":
    if "snakemake" not in globals():
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        from _helpers import mock_snakemake

        snakemake = mock_snakemake("retrieve_databundle_light")
    # TODO Make logging compatible with progressbar (see PR #102, PyPSA-Eur)
    configure_logging(snakemake)

    _sets_path_to_root("pypsa-africa")
    
    # resources to download
    resources_to_download=["resources", "data", "cutouts"]

    rootpath = os.getcwd()
    tutorial = snakemake.config["tutorial"]
    countries = snakemake.config["countries"]
    host = "zenodo"  # hard coded for now. Could be a snakemake rule param./attri
    logger.info(f"Retrieving data from {host}.")

    # load databundle configuration
    config_bundles = load_databundle_config(snakemake.input)

    # list of bundles to download
    bundles_to_download = []

    # dictionary of best data

    for bname in config_bundles:
        # idenfify matched countries for every bundle
        config_bundles[bname]["matched_countries"] = [
            c for c in config_bundles["countries"] if c in countries]
        n_matched = len(config_bundles[bname]["matched_countries"])
        config_bundles[bname]["n_matched"] = n_matched

        # if countries are matched
        if n_matched > 0:
            # when the data is necessary, append to the list of bundles to download
            if config_bundles[bname].get("necessary", False):
                bundles_to_download.append(n_matched)


    if host == "zenodo":
        # BUNDLE 1
        destination = Path(f"{rootpath}/resources")
        file_path = Path(f"{rootpath}/resources.zip")
        url = "https://zenodo.org/record/5894972/files/resources.zip"
        progress_retrieve(url, file_path)
        logger.info(f"Extracting resources")
        with ZipFile(file_path, "r") as zipObj:
            # Extract all the contents of zip file in current directory
            zipObj.extractall()
        os.remove(file_path)
        logger.info(f"Download data to '{destination}' from cloud '{url}'.")

        if tutorial == True:
            # BUNDLE 2
            destination = Path(f"{rootpath}/data")
            file_path = Path(f"{rootpath}/data-tutorial.zip")
            url = "https://zenodo.org/record/5895010/files/data-tutorial.zip"
            progress_retrieve(url, file_path)
            logger.info(f"Extracting data")
            with ZipFile(file_path, "r") as zipObj:
                zipObj.extractall()
            os.remove(file_path)
            logger.info(f"Download data to '{destination}' from cloud '{url}'.")

            # BUNDLE 3
            destination = Path(f"{rootpath}/cutouts")
            file_path = Path(f"{rootpath}/cutouts/africa-2013-era5-tutorial.nc")
            url = "https://zenodo.org/record/5894926/files/africa-2013-era5-tutorial.nc"
            progress_retrieve(url, file_path)
            logger.info(f"Download cutouts to '{destination}' from cloud '{url}'.")

        elif tutorial == False:
            # BUNDLE 2
            destination = Path(f"{rootpath}/data")
            file_path = Path(f"{rootpath}/data.zip")
            url = "https://zenodo.org/record/5895010/files/data.zip"
            progress_retrieve(url, file_path)
            logger.info(f"Extracting data")
            with ZipFile(file_path, "r") as zipObj:
                zipObj.extractall()
            os.remove(file_path)
            logger.info(f"Download data to '{destination}' from cloud '{url}'.")

            # BUNDLE 3
            destination = Path(f"{rootpath}/cutouts")
            file_path = Path(f"{rootpath}/cutouts/africa-2013-era5.nc")
            url = "https://zenodo.org/record/5894926/files/africa-2013-era5.nc"
            progress_retrieve(url, file_path)
            logger.info(f"Download cutouts to '{destination}' from cloud '{url}'.")

    if host == "google":
        if tutorial == False:
            # BUNDLE 1
            destination = "./resources"
            zip_path = destination + ".zip"
            url = "https://drive.google.com/file/d/1hklbiRLyb_rx6WTvgCJ1Dx_9rooA85y1/view?usp=sharing"
            gdd.download_file_from_google_drive(
                file_id="1hklbiRLyb_rx6WTvgCJ1Dx_9rooA85y1",
                dest_path=zip_path,
                showsize=True,
                unzip=True,
            )
            os.remove(zip_path)
            logger.info(f"Download data to '{destination}' from cloud '{url}'.")

            # BUNDLE 2
            destination = "./data"
            zip_path = destination + ".zip"
            url = "https://drive.google.com/file/d/1IfSofV2PWUkAD_7yY-Xqv1X4duma2NkJ/view?usp=sharing"
            gdd.download_file_from_google_drive(
                file_id="1IfSofV2PWUkAD_7yY-Xqv1X4duma2NkJ",
                dest_path=zip_path,
                showsize=True,
                unzip=True,
            )
            os.remove(zip_path)
            logger.info(f"Download data to '{destination}' from cloud '{url}'.")

            # BUNDLE 3
            destination = "./cutouts"
            zip_path = destination + ".zip"
            url = "https://drive.google.com/file/d/1kyOH8wxm_cvnS7OoahCrFFVP-U7kWr_O/view?usp=sharing"
            gdd.download_file_from_google_drive(
                file_id="1kyOH8wxm_cvnS7OoahCrFFVP-U7kWr_O",
                dest_path=zip_path,
                showsize=True,
                unzip=True,
            )
            os.remove(zip_path)
            logger.info(f"Download data to '{destination}' from cloud '{url}'.")

        if tutorial == True:
            # BUNDLE 1
            destination = "./resources"
            zip_path = destination + ".zip"
            url = "https://drive.google.com/file/d/1he31BBLtdemZt2dmBOwUCbP_jVuI3KS8/view?usp=sharing"
            gdd.download_file_from_google_drive(
                file_id="1he31BBLtdemZt2dmBOwUCbP_jVuI3KS8",
                dest_path=zip_path,
                showsize=False,
                unzip=True,
            )
            os.remove(zip_path)
            logger.info(f"Download data to '{destination}' from cloud '{url}'.")

            # BUNDLE 2
            destination = "./data"
            zip_path = destination + ".zip"
            url = "https://drive.google.com/file/d/1Jv4UMw7CoinZwIzl5nm1Z5oIuK7dG7gu/view?usp=sharing"
            gdd.download_file_from_google_drive(
                file_id="1Jv4UMw7CoinZwIzl5nm1Z5oIuK7dG7gu",
                dest_path=zip_path,
                showsize=False,
                unzip=True,
            )
            os.remove(zip_path)
            logger.info(f"Download data to '{destination}' from cloud '{url}'.")

            # BUNDLE 3
            destination = "./cutouts"
            zip_path = destination + ".zip"
            url = "https://drive.google.com/file/d/1-Njs7BqG0YE5QwBHj0zgkdicb5IQvQCh/view?usp=sharing"
            gdd.download_file_from_google_drive(
                file_id="1-Njs7BqG0YE5QwBHj0zgkdicb5IQvQCh",
                dest_path=zip_path,
                showsize=False,
                unzip=True,
            )
            os.remove(zip_path)
            logger.info(f"Download data to '{destination}' from cloud '{url}'.")

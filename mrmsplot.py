#!/usr/bin/env python3
# Multi-Radar Multi-Sensor based mosaicing for python-based HDWX
# Created 19 April 2022 by Sam Gardner <stgardner4@tamu.edu>

from os import path, listdir, remove, system
import xarray as xr
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import colors as pltcolors
from cartopy import crs as ccrs
from cartopy import feature as cfeat
from io import StringIO
from metpy.units import pandas_dataframe_to_unit_arrays
from metpy.io import parse_metar_file
from metpy import calc as mpcalc
from metpy import plots as mpplots
from metpy.units import units
from metpy.cbook import get_test_data
from matplotlib.patheffects import withStroke
from pandas import Timestamp
from datetime import datetime as dt
from pathlib import Path
import atexit
from siphon.catalog import TDSCatalog
import pandas as pd


basePath = path.abspath(path.dirname(__file__))
hasHelpers = False
if path.exists(path.join(basePath, "HDWX_helpers.py")):
    import HDWX_helpers
    hasHelpers = True
axExtent = [-129, -65, 23.5, 51]

@atexit.register
def exitFunc():
    print("Plotting complete!")
    remove(path.join(basePath, "plotter-lock.txt"))
    system("bash generate.sh --no-cleanup &")

def set_size(w,h, ax=None):
    if not ax: ax=plt.gca()
    l = ax.figure.subplotpars.left
    r = ax.figure.subplotpars.right
    t = ax.figure.subplotpars.top
    b = ax.figure.subplotpars.bottom
    figw = float(w)/(r-l)
    figh = float(h)/(t-b)
    ax.figure.set_size_inches(figw, figh)

def addStationPlot(ax, validTime):
    metarTime = validTime.replace(minute=0, second=0, microsecond=0)
    stationCatalog = TDSCatalog("https://thredds.ucar.edu/thredds/catalog/noaaport/text/metar/catalog.xml")
    airports = pd.read_csv(get_test_data("airport-codes.csv"))
    airports = airports[(airports["type"] == "large_airport") | (airports["type"] == "medium_airport") | (airports["type"] == "small_airport")]
    try:
        dataset = stationCatalog.datasets.filter_time_nearest(metarTime)
        dataset.download()
        [remove(file) for file in sorted(listdir) if "metar_" in file and file != dataset.name]
    except Exception as e:
        print(stationCatalog.datasets.filter_time_nearest(metarTime).remote_open().read())
    if path.exists(dataset.name):
        metarData = parse_metar_file(dataset.name, year=metarTime.year, month=metarTime.month)
    else:
        return
    metarUnits = metarData.units

    metarDataFilt = metarData[metarData["station_id"].isin(airports["ident"])]
    metarDataFilt = metarDataFilt.dropna(how="any", subset=["longitude", "latitude", "station_id", "wind_speed", "wind_direction", "air_temperature", "dew_point_temperature", "air_pressure_at_sea_level", "current_wx1_symbol", "cloud_coverage"])
    metarDataFilt = metarDataFilt.drop_duplicates(subset=["station_id"], keep="last")
    metarData = pandas_dataframe_to_unit_arrays(metarDataFilt, metarUnits)
    metarData["u"], metarData["v"] = mpcalc.wind_components(metarData["wind_speed"], metarData["wind_direction"])
    locationsInMeters = ccrs.epsg(3857).transform_points(ccrs.PlateCarree(), metarData["longitude"].m, metarData["latitude"].m)
    overlap_prevent = mpcalc.reduce_point_density(locationsInMeters[:, 0:2], 50000)
    stations = mpplots.StationPlot(ax, metarData["longitude"][overlap_prevent], metarData["latitude"][overlap_prevent], clip_on=True, transform=ccrs.PlateCarree(), fontsize=6)
    stations.plot_parameter("NW", metarData["air_temperature"][overlap_prevent].to(units.degF), path_effects=[withStroke(linewidth=1, foreground="white")])
    stations.plot_parameter("SW", metarData["dew_point_temperature"][overlap_prevent].to(units.degF), path_effects=[withStroke(linewidth=1, foreground="white")])
    stations.plot_parameter("NE", metarData["air_pressure_at_sea_level"][overlap_prevent].to(units.hPa), formatter=lambda v: format(10 * v, '.0f')[-3:])
    stations.plot_symbol((-1.5, 0), metarData['current_wx1_symbol'][overlap_prevent], mpplots.current_weather, path_effects=[withStroke(linewidth=1, foreground="white")], fontsize=9)
    if validTime.minute % 10 == 0:
        stations.plot_text((2, 0), metarData["station_id"][overlap_prevent], path_effects=[withStroke(linewidth=2, foreground="white")])
    stations.plot_symbol("C", metarData["cloud_coverage"][overlap_prevent], mpplots.sky_cover)
    stations.plot_barb(metarData["u"][overlap_prevent], metarData["v"][overlap_prevent])
    return ax

def plotRadar(radarFilePath):
    radarDS = xr.open_dataset(radarFilePath, engine="cfgrib")
    radarDS = radarDS.sel(latitude=slice(axExtent[3], axExtent[2]), longitude=slice(axExtent[0]+360, axExtent[1]+360))
    validTime = Timestamp(radarDS.time.data).to_pydatetime()
    fig = plt.figure()
    px = 1/plt.rcParams["figure.dpi"]
    fig.set_size_inches(2560*px, 1440*px)
    ax = plt.axes(projection=ccrs.epsg(3857))
    specR = plt.cm.Spectral_r(np.linspace(0, 0.95, 200))
    pink = plt.cm.PiYG(np.linspace(0, 0.25, 40))
    purple = plt.cm.PRGn_r(np.linspace(0.75, 1, 40))
    cArr = np.vstack((specR, pink, purple))
    cmap = pltcolors.LinearSegmentedColormap.from_list("cvd-reflectivity", cArr)
    vmin=10
    vmax=80
    dataMask = np.where(np.logical_and(radarDS.unknown.data>=10, radarDS.unknown.data<=80), 0, 1)
    rdr = ax.pcolormesh(radarDS.longitude, radarDS.latitude, np.ma.masked_array(radarDS.unknown, mask=dataMask), cmap=cmap, vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree(), zorder=1)
    ax.add_feature(cfeat.STATES.with_scale("50m"), linewidth=0.5, zorder=4)
    ax.add_feature(cfeat.COASTLINE.with_scale("50m"), linewidth=0.5, zorder=5)
    set_size(2560*px, 1440*px, ax=ax)
    ax.set_extent([-129, -65, 23.5, 51], crs=ccrs.PlateCarree())
    extent = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
    Path(path.join(basePath, "output", "gisproducts", "radar", "RALA", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "gisproducts", "radar", "RALA", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")), transparent=True, bbox_inches=extent)
    if hasHelpers:
        HDWX_helpers.writeJson(basePath, 0, validTime, validTime.strftime("%M.png"), validTime, ["23.5,-129", "51,-65"], 60)
        HDWX_helpers.dressImage(fig, ax, "National MRMS Reflectivity At Lowest Altitude", validTime=validTime, notice="Data provided by NOAA/NSSL", plotHandle=rdr, colorbarLabel="Reflectivity (dBZ)")
        title = fig.axes[2].get_children()[0]
    else:
        title = None
    Path(path.join(basePath, "output", "products", "radar", "national", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "products", "radar", "national", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")))
    if hasHelpers:
        HDWX_helpers.writeJson(basePath, 1, validTime, validTime.strftime("%M.png"), validTime, ["0,0", "0,0"], 60)
    
    addStationPlot(ax, validTime)
    ax.add_feature(mpplots.USCOUNTIES.with_scale("5m"), edgecolor="green", linewidth=0.25, zorder=2)
    ax.set_extent([-110, -85, 23.5, 37])
    ax.set_box_aspect(9/16)
    if title is not None:
        title.set_text("Regional MRMS Reflectivity At Lowest Altitude\nValid: "+validTime.strftime("%-d %b %Y %H%MZ"))
    Path(path.join(basePath, "output", "products", "radar", "regional", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "products", "radar", "regional", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")))
    if hasHelpers:
        HDWX_helpers.writeJson(basePath, 2, validTime, validTime.strftime("%M.png"), validTime, ["0,0", "0,0"], 60)
    roads = cfeat.NaturalEarthFeature("cultural", "roads_north_america", "10m", facecolor="none")
    ax.add_feature(roads, edgecolor="red", linewidth=0.25, zorder=3)
    ax.set_extent([-101, -92.4, 28.6, 32.5])
    ax.set_box_aspect(9/16)
    if title is not None:
        title.set_text("Local MRMS Reflectivity At Lowest Altitude\nValid: "+validTime.strftime("%-d %b %Y %H%MZ"))
    Path(path.join(basePath, "output", "products", "radar", "local", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "products", "radar", "local", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")))
    if hasHelpers:
        HDWX_helpers.writeJson(basePath, 3, validTime, validTime.strftime("%M.png"), validTime, ["0,0", "0,0"], 60)


if __name__ == "__main__":
    inputDir = path.join(basePath, "input")
    for file in listdir(inputDir):
        if "idx" in file:
            idxFilePath = path.join(inputDir, file)
            remove(idxFilePath)
    for file in reversed(sorted(listdir(inputDir))):
        radarFilePath = path.join(inputDir, file)
        print(">>>PLOTTING>>> "+file)
        plotRadar(radarFilePath)
        remove(radarFilePath)

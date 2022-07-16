#!/usr/bin/env python3
# Multi-Radar Multi-Sensor based mosaicing for python-based HDWX
# Created 19 April 2022 by Sam Gardner <stgardner4@tamu.edu>

from os import path, listdir, remove, chmod, system
import xarray as xr
from matplotlib import pyplot as plt
from matplotlib import image as mpimage
from cartopy import crs as ccrs
from cartopy import feature as cfeat
from metpy.plots import ctables
from metpy.plots import USCOUNTIES
from pandas import Timestamp
from datetime import datetime as dt
from pathlib import Path
import json
from atomicwrites import atomic_write
import atexit

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

def plotRadar(radarFilePath):
    radarDS = xr.open_dataset(radarFilePath, engine="cfgrib")
    radarDS = radarDS.sel(latitude=slice(axExtent[3], axExtent[2]), longitude=slice(axExtent[0]+360, axExtent[1]+360))
    validTime = Timestamp(radarDS.time.data).to_pydatetime()
    fig = plt.figure()
    px = 1/plt.rcParams["figure.dpi"]
    fig.set_size_inches(2560*px, 1440*px)
    ax = plt.axes(projection=ccrs.epsg(3857))
    norm, cmap = ctables.registry.get_with_steps("NWSReflectivity", 5, 5)
    cmap.set_under("#00000000")
    cmap.set_over("black")
    rdr = ax.pcolormesh(radarDS.longitude, radarDS.latitude, radarDS.unknown, cmap=cmap, norm=norm, transform=ccrs.PlateCarree(), zorder=1)
    ax.add_feature(cfeat.STATES.with_scale("50m"), linewidth=0.5, zorder=4)
    ax.add_feature(cfeat.COASTLINE.with_scale("50m"), linewidth=0.5, zorder=5)
    set_size(2560*px, 1440*px, ax=ax)
    ax.set_extent([-129, -65, 23.5, 51], crs=ccrs.PlateCarree())
    extent = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
    Path(path.join(basePath, "output", "gisproducts", "radar", "RALA", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "gisproducts", "radar", "RALA", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")), transparent=True, bbox_inches=extent)
    if hasHelpers:
        HDWX_helpers.writeJson(basePath, 0, validTime, validTime.strftime("%M.png"), validTime, ["23.5,-129", "51,-65"], 60)
    fig.set_size_inches(1920*px, 1080*px)
    ax.set_box_aspect(9/16)
    cbax = fig.add_axes([.01,0.075,(ax.get_position().width/3),.02])
    fig.colorbar(rdr, cax=cbax, orientation="horizontal", extend="max")
    cbax.set_xlabel("Reflectivity (dBZ)")
    tax = fig.add_axes([ax.get_position().x0+cbax.get_position().width+.01,0.045,(ax.get_position().width/3),.05])
    title = tax.text(0.5, 0.5, "National MRMS Reflectivity At Lowest Altitude\nValid: "+validTime.strftime("%-d %b %Y %H%MZ"), horizontalalignment="center", verticalalignment="center", fontsize=16)
    tax.set_xlabel("Python HDWX -- Send bugs to stgardner4@tamu.edu\nData provided by NOAA/NSSL")
    plt.setp(tax.spines.values(), visible=False)
    tax.tick_params(left=False, labelleft=False)
    tax.tick_params(bottom=False, labelbottom=False)
    lax = fig.add_axes([(.99-(ax.get_position().width/3)),0,(ax.get_position().width/3),.1])
    lax.set_aspect(2821/11071)
    lax.axis("off")
    plt.setp(lax.spines.values(), visible=False)
    atmoLogo = mpimage.imread(path.join(basePath, "assets", "atmoLogo.png"))
    lax.imshow(atmoLogo)
    ax.set_position([.005, cbax.get_position().y0+cbax.get_position().height+.005, .99, (.99-(cbax.get_position().y0+cbax.get_position().height))])
    Path(path.join(basePath, "output", "products", "radar", "national", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "products", "radar", "national", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")))
    if hasHelpers:
        HDWX_helpers.writeJson(basePath, 1, validTime, validTime.strftime("%M.png"), validTime, ["0,0", "0,0"], 60)
    ax.add_feature(USCOUNTIES.with_scale("5m"), edgecolor="green", linewidth=0.25, zorder=2)
    ax.set_extent([-110, -85, 23.5, 37])
    ax.set_box_aspect(9/16)
    title.set_text("Regional MRMS Reflectivity At Lowest Altitude\nValid: "+validTime.strftime("%-d %b %Y %H%MZ"))
    Path(path.join(basePath, "output", "products", "radar", "regional", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "products", "radar", "regional", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")))
    if hasHelpers:
        HDWX_helpers.writeJson(basePath, 2, validTime, validTime.strftime("%M.png"), validTime, ["0,0", "0,0"], 60)
    roads = cfeat.NaturalEarthFeature("cultural", "roads_north_america", "10m", facecolor="none")
    ax.add_feature(roads, edgecolor="red", linewidth=0.25, zorder=3)
    ax.set_extent([-101, -92.4, 28.6, 32.5])
    ax.set_box_aspect(9/16)
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
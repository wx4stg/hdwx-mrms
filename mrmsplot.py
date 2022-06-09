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

axExtent = [-129, -65, 23.5, 51]

@atexit.register
def exitFunc():
    print("Plotting complete!")
    remove(path.join(basePath, "plotter-lock.txt"))
    system("bash generate.sh &")

def set_size(w,h, ax=None):
    if not ax: ax=plt.gca()
    l = ax.figure.subplotpars.left
    r = ax.figure.subplotpars.right
    t = ax.figure.subplotpars.top
    b = ax.figure.subplotpars.bottom
    figw = float(w)/(r-l)
    figh = float(h)/(t-b)
    ax.figure.set_size_inches(figw, figh)

def writeJson(productID, validTime):
    if productID == 0:
        productDesc = "MRMS Reflectivity At Lowest Altitude"
        gisInfo = ["23.5,-129", "51,-65"]
    elif productID == 1:
        productDesc = "MRMS National Reflectivity At Lowest Altitude"
        dirname = "national/"
        gisInfo = ["0,0", "0,0"]
    elif productID == 2:
        productDesc = "MRMS Regional Reflectivity At Lowest Altitude"
        dirname = "regional/"
        gisInfo = ["0,0", "0,0"]
    elif productID == 3:
        productDesc = "MRMS Local Reflectivity At Lowest Altitude"
        dirname = "local/"
        gisInfo = ["0,0", "0,0"]
    if gisInfo == ["0,0", "0,0"]:
        isGIS = False
        productPath = "products/radar/"+dirname
    else:
        isGIS = True
        productPath = "gisproducts/radar/RALA/"
    runPathExtension = validTime.strftime("%Y/%m/%d/%H00/")
    publishTime = dt.utcnow()
    productDict = {
        "productID" : productID,
        "productDescription" : productDesc,
        "productPath" : productPath,
        "productReloadTime" : 60,
        "lastReloadTime" : publishTime.strftime("%Y%m%d%H%M"),
        "isForecast" : True,
        "isGIS" : isGIS,
        "fileExtension" : "png",
        "displayFrames" : 60
    }
    # Target path for the product json is just output/metadata/<productID>.json
    productDictJsonPath = path.join(basePath, "output", "metadata", str(productID)+".json")
    # Create output/metadata/ if it doesn't already exist
    Path(path.dirname(productDictJsonPath)).mkdir(parents=True, exist_ok=True)
    with atomic_write(productDictJsonPath, overwrite=True) as jsonWrite:
        json.dump(productDict, jsonWrite, indent=4)
    chmod(productDictJsonPath, 0o644)
    # Now we need to write a json for the product run in output/metadata/products/<productID>/<runTime>.json
    productRunDictPath = path.join(basePath, "output", "metadata", "products", str(productID), validTime.strftime("%Y%m%d%H00")+".json")
    # Create parent directory if it doesn't already exist.
    Path(path.dirname(productRunDictPath)).mkdir(parents=True, exist_ok=True)
    # If the json file already exists, read it in to to discover which frames have already been generated
    if path.exists(productRunDictPath):
        with open(productRunDictPath, "r") as jsonRead:
            oldData = json.load(jsonRead)
        # Add previously generated frames to a list, framesArray
        framesArray = oldData["productFrames"]
    else:
        # If that file didn't exist, then create an empty list instead
        framesArray = list()
    # Now we need to add the frame we just wrote, as well as any that exist in the output directory that don't have metadata yet. 
    # To do this, we first check if the output directory is not empty.
    productRunPath = path.join(basePath, "output", productPath, runPathExtension)
    if len(listdir(productRunPath)) > 0:
        # If there are files inside, list them all
        frameNames = listdir(productRunPath)
        # get an array of integers representing the minutes past the hour of frames that have already been generated
        frameMinutes = [int(framename.replace(".png", "")) for framename in frameNames if ".png" in framename]
        # Loop through the previously-generated minutes and generate metadata for each
        for frameMin in frameMinutes:
            frmDict = {
                "fhour" : 0, # forecast hour is 0 for non-forecasts
                "filename" : str(frameMin)+".png",
                "gisInfo" : gisInfo,
                "valid" : str(int(validTime.strftime("%Y%m%d%H00"))+frameMin)
            }
            # If this dictionary isn't already in the framesArray, add it
            if frmDict not in framesArray:
                framesArray.append(frmDict)
    productRunDict = {
        "publishTime" : publishTime.strftime("%Y%m%d%H%M"),
        "pathExtension" : runPathExtension,
        "runName" : validTime.strftime("%d %b %Y %HZ"),
        "availableFrameCount" : len(framesArray),
        "totalFrameCount" : len(framesArray),
        "productFrames" : sorted(framesArray, key=lambda dict: int(dict["valid"])) # productFramesArray, sorted by increasing valid Time
    }
    # Write productRun dictionary to json
    with atomic_write(productRunDictPath, overwrite=True) as jsonWrite:
        json.dump(productRunDict, jsonWrite, indent=4)
    chmod(productRunDictPath, 0o644)
    # Now we need to create a dictionary for the product type (TAMU)
    productTypeID = 1
    # Output for this json is output/metadata/productTypes/1.json
    productTypeDictPath = path.join(basePath, "output/metadata/productTypes/"+str(productTypeID)+".json")
    # Create output directory if it doesn't already exist
    Path(path.dirname(productTypeDictPath)).mkdir(parents=True, exist_ok=True)
    # Create empty list that will soon hold a dict for each of the products generated by this script
    productsInType = list()
    # If the productType json file already exists, read it in to discover which products it contains
    if path.exists(productTypeDictPath):
        with open(productTypeDictPath, "r") as jsonRead:
            oldProductTypeDict = json.load(jsonRead)
        # Add all of the products from the json file into the productsInType list...
        for productInOldDict in oldProductTypeDict["products"]:
            # ...except for the one that's currently being generated (prevents duplicating it)
            if productInOldDict["productID"] != productID:
                productsInType.append(productInOldDict)
    # Add the productDict for the product we just generated
    productsInType.append(productDict)
    # Create productType Dict
    productTypeDict = {
        "productTypeID" : productTypeID,
        "productTypeDescription" : "TAMU",
        "products" : sorted(productsInType, key=lambda dict: dict["productID"]) # productsInType, sorted by productID
    }
    # Write productType dict to json
    with atomic_write(productTypeDictPath, overwrite=True) as jsonWrite:
        json.dump(productTypeDict, jsonWrite, indent=4)
    chmod(productTypeDictPath, 0o644)

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
    writeJson(0, validTime)
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
    writeJson(1, validTime)
    ax.add_feature(USCOUNTIES.with_scale("5m"), edgecolor="green", linewidth=0.25, zorder=2)
    ax.set_extent([-110, -85, 23.5, 37])
    ax.set_box_aspect(9/16)
    title.set_text("Regional MRMS Reflectivity At Lowest Altitude\nValid: "+validTime.strftime("%-d %b %Y %H%MZ"))
    Path(path.join(basePath, "output", "products", "radar", "regional", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "products", "radar", "regional", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")))
    writeJson(2, validTime)
    roads = cfeat.NaturalEarthFeature("cultural", "roads_north_america", "10m", facecolor="none")
    ax.add_feature(roads, edgecolor="red", linewidth=0.25, zorder=3)
    ax.set_extent([-101, -92.4, 28.6, 32.5])
    ax.set_box_aspect(9/16)
    title.set_text("Local MRMS Reflectivity At Lowest Altitude\nValid: "+validTime.strftime("%-d %b %Y %H%MZ"))
    Path(path.join(basePath, "output", "products", "radar", "local", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"))).mkdir(parents=True, exist_ok=True)
    fig.savefig(path.join(basePath, "output", "products", "radar", "local", validTime.strftime("%Y"), validTime.strftime("%m"), validTime.strftime("%d"), validTime.strftime("%H00"), validTime.strftime("%M.png")))
    writeJson(3, validTime)


if __name__ == "__main__":
    basePath = path.realpath(path.dirname(__file__))
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
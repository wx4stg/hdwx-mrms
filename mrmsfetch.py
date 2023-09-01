#!/usr/bin/env python3
# MRMS grib2 data fetching script for python-based HDWX
# Created 29 April 2022 by Sam Gardner <stgardner4@tamu.edu>

from os import path, remove, listdir
from pathlib import Path
import pandas as pd
from datetime import datetime as dt, timedelta
import json
import requests
import gzip
import shutil
import urllib

basePath = path.realpath(path.dirname(__file__))

def downloadFile(fileName):
    output = path.join(basePath, "input", fileName)
    print("Downloading "+fileName)
    urlToFetch = "https://mrms.ncep.noaa.gov/data/2D/ReflectivityAtLowestAltitude/"+fileName
    try:
        mrmsData = requests.get(urlToFetch)
        if mrmsData.status_code == 200:
            mrmsData = mrmsData.content
    except requests.exceptions.SSLError:
        import subprocess
        mrmsDataProc = subprocess.run(["curl", urlToFetch], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        mrmsData = mrmsDataProc.stdout
    with open(output, "wb") as fileWrite:
        fileWrite.write(mrmsData.content)
    with gzip.open(output, "rb") as f_in:
        with open(output.replace(".gz", ""), "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    remove(output)


if __name__ == "__main__":
    Path(path.join(basePath, "input")).mkdir(parents=True, exist_ok=True)
    gribList = pd.read_html("https://mrms.ncep.noaa.gov/data/2D/ReflectivityAtLowestAltitude/")[0].dropna(how="any")
    try:
        gribList = pd.read_html("https://mrms.ncep.noaa.gov/data/2D/ReflectivityAtLowestAltitude/")[0].dropna(how="any")
    except urllib.error.URLError:
        import subprocess
        from io import BytesIO
        gribListCurlProc = subprocess.run(["curl", "https://mrms.ncep.noaa.gov/data/2D/ReflectivityAtLowestAltitude/"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        gribList = pd.read_html(BytesIO(gribListCurlProc.stdout))[0].dropna(how="any")
    gribList = gribList[~gribList.Name.str.contains("latest") == True].reset_index()
    gribList["pyDateTimes"] = [dt.strptime(filename, "MRMS_ReflectivityAtLowestAltitude_00.50_%Y%m%d-%H%M%S.grib2.gz") for filename in gribList["Name"]]
    gribList = gribList.set_index(["pyDateTimes"])
    alreadyDownloaded = listdir(path.join(basePath, "input"))
    for mosaicTime in reversed(gribList.index):
        if mosaicTime > dt.utcnow() - timedelta(hours=1):
            runFile = path.join(basePath, "output", "metadata", "products", "3", mosaicTime.strftime("%Y%m%d%H00.json"))
            if path.exists(runFile):
                with open(runFile) as jsonLoad:
                    runData = json.load(jsonLoad)
                alreadyHavePlotted = False
                for productFrame in runData["productFrames"]:
                    if mosaicTime.strftime("%Y%m%d%H%M") == productFrame["valid"]:
                        alreadyHavePlotted = True
                if not alreadyHavePlotted:
                    fileToDownload = gribList[gribList.index == mosaicTime]["Name"][0]
                    if fileToDownload.replace(".gz", "") not in alreadyDownloaded:
                        downloadFile(fileToDownload)
            else:
                fileToDownload = gribList[gribList.index == mosaicTime]["Name"][0]
                if fileToDownload.replace(".gz", "") not in alreadyDownloaded:
                    downloadFile(fileToDownload) 
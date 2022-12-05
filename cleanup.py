#!/usr/bin/env python3
# Purges no-longer-needed files from mrms plotting
# Created on 1 May 2022 by Sam Gardner <stgardner4@tamu.edu>

from datetime import datetime as dt, timedelta
from os import path, walk, remove

if __name__ == "__main__":
    basePath = path.dirname(path.abspath(__file__))
    now = dt.now()
    if path.exists(path.join(basePath, "lastCleanDT.txt")):
        readLastCleanFile = open(path.join(basePath, "lastCleanDT.txt"), "r")
        lastCleanTime = dt.strptime(readLastCleanFile.read(), "%Y%m%d%H%M")
        readLastCleanFile.close()
    else:
        lastCleanTime = dt.utcnow()
        writeLastCleanFile = open(path.join(basePath, "lastCleanDT.txt"), "w")
        writeLastCleanFile.write(lastCleanTime.strftime("%Y%m%d%H%M"))
        writeLastCleanFile.close()
    if lastCleanTime < dt.utcnow() - timedelta(hours=2):
        outputPath = path.join(basePath, "output")
        if path.exists(outputPath):
            for root, dirs, files in walk(outputPath):
                for name in files:
                    filepath = path.join(path.join(basePath, root), name)
                    if filepath.endswith(".json"):
                        deleteAfter = timedelta(days=2)
                    else:
                        deleteAfter = timedelta(minutes=20)
                    createTime = dt.fromtimestamp(path.getmtime(filepath))
                    if createTime < now - deleteAfter:
                        remove(filepath)
        remove(path.join(basePath, "cached_lats.csv"))
        remove(path.join(basePath, "cached_lons.csv"))
        remove(path.join(basePath, "status.txt"))
        remove(path.join(basePath, "lastCleanDT.txt"))
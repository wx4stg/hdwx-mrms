#!/usr/bin/env python3
# Purges no-longer-needed files from mrms plotting
# Created on 1 May 2022 by Sam Gardner <stgardner4@tamu.edu>

from datetime import datetime as dt, timedelta
from os import path, walk, remove

if __name__ == "__main__":
    basePath = path.dirname(path.abspath(__file__))
    now = dt.now()
    outputPath = path.join(basePath, "output")
    if path.exists(outputPath):
        for root, dirs, files in walk(outputPath):
            for name in files:
                filepath = path.join(basePath, root, name)
                if filepath.endswith(".json"):
                    deleteAfter = timedelta(days=2)
                else:
                    deleteAfter = timedelta(minutes=20)
                createTime = dt.fromtimestamp(path.getmtime(filepath))
                if createTime < now - deleteAfter:
                    remove(filepath)
    remove(path.join(basePath, "cached_lats.csv"))
    remove(path.join(basePath, "cached_lons.csv"))
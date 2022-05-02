#!/bin/bash
# Product generation script for hdwx-mrms
# Created 29 April 2022 by Sam Gardner <stgardner4@tamu.edu>

if [ ! -d output/ ]
then
    mkdir output/
fi
if [ ! -d input/ ]
then
    mkdir input/
fi

if [ -f status.txt ]
then
  echo "lockfile found, exiting"
  exit
fi
touch status.txt
if [ -f ../config.txt ]
then
    source ../config.txt
else
    condaEnvName="HDWX"
fi

if [ -f $condaRootPath/envs/$condaEnvName/bin/python3 ]
then
    $condaRootPath/envs/$condaEnvName/bin/python3 mrmsfetch.py
    $condaRootPath/envs/$condaEnvName/bin/python3 mrmsplot.py
    $condaRootPath/envs/$condaEnvName/bin/python3 cleanup.py
fi

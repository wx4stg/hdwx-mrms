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
touch status.txt
if [ -f ../config.txt ]
then
    source ../config.txt
else
    condaEnvName="HDWX"
fi

if [ -f $condaRootPath/envs/$condaEnvName/bin/python3 ]
then
    if [ -f fetcher-lock.txt ]
    then
        pidToCheck=`cat fetcher-lock.txt`
        if ! kill -0 $pidToCheck
        then
            echo "Fetching..."
            $condaRootPath/envs/$condaEnvName/bin/python3 mrmsfetch.py &
            echo -n $! > fetcher-lock.txt
        else
            echo "Fetcher locked"
        fi
    else
            echo "Fetching..."
            $condaRootPath/envs/$condaEnvName/bin/python3 mrmsfetch.py &
            echo -n $! > fetcher-lock.txt
    fi
    if [ -f plotter-lock.txt ]
    then
        pidToCheck=`cat plotter-lock.txt`
        if ! kill -0 $pidToCheck
        then
            echo "Plotting..."
            $condaRootPath/envs/$condaEnvName/bin/python3 mrmsplot.py &
            echo -n $! > plotter-lock.txt
        else
            echo "Plotter locked"
        fi
    else
            echo "Plotting..."
            $condaRootPath/envs/$condaEnvName/bin/python3 mrmsplot.py &
            echo -n $! > plotter-lock.txt
    fi
    $condaRootPath/envs/$condaEnvName/bin/python3 cleanup.py
fi

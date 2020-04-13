#!/bin/python
import xarray as xr
import numpy as np
import datetime as dt
import logging
import glob
import argparse
import sys
import os
import pandas as pd
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.cm import get_cmap

# Region masks. Specify name and region domain [western border,eastern border,southern border, eastern border]
#masks = {
# "Northeast US":[-80.0,-70.0,35.0,50.0],
# "Western US":[-125.0,-115.0,33.0,50.0],
# "South US":[-105.0,-85.0,30.0,40.0],
# "East China":[105.0,125.0,18.0,40.0],
# "Western Europe":[0.0,15.0,40.0,55.0],
#}

#masks = {
# "Wuhan, China":[114.0,115.0,30.0,31.0],
# "Milan, Italy":[9.0,10.0,45.0,46.0],
# "Seattle, WA":[-123.0,-122.0,47.0,48.0],
# "Washington, DC":[-78.0,-77.0,38.0,39.0],
#}

masks = {
 "Wuhan":[114.24,114.25,30.6,30.6],
 "Zhengzhou":[113.675,113.675,34.8,34.8],
 "Beijing":[116.36,116.36,40.0,40.0],
 "Shanghai":[121.48,121.48,31.2,31.2],
}

masks = {
 "Milan (IT)":[9.2,9.2,45.5,45.5],
 "Paris (FR)":[2.35,2.35,48.8,48.8],
}
 
masks = {
 "Washington DC":[-77,-77,38.9,38.9],
 "New York":[-73.9,-73.9,40.8,40.8],
 "Seattle":[-122.3,-122.3,47.6,47.6],
 "San Francisco":[-122.4,-122.4,37.8,37.8],
}

masks = {
 "Wuhan, China":[114.24,114.25,30.6,30.6],
 "Paris, France":[2.35,2.35,48.8,48.8],
 "Washington DC, USA":[-77,-77,38.9,38.9],
}


def main(args):
    '''
    Plot time series of the OMISCAL scale factors over set regions (specified above)'
    '''
    # read template file 
    log = logging.getLogger(__name__)
    scals = pd.DataFrame()
    start = dt.datetime(args.year1,1,1)
    end = dt.datetime(args.year2+1,1,1)
    iday = start
    while iday < end:
        iscals = _read_file(args,iday)
        if iscals is not None:
            scals = scals.append(iscals)
        # next day
        iday = iday + dt.timedelta(days=1)
    # plot timeseries
    scals = scals.set_index('date')
    if args.resample is not None:
        scals = scals.resample(args.resample).mean()
    fig = plt.figure(figsize=(12,4)) 
    ax = fig.add_subplot(111)
    scals.plot(ax=ax,color=['orange','blue','red'])
    plt.legend(ncol=3)
    plt.axhline(1.0,color='black',linestyle='dotted',lw=1)
    plt.title('Emissions scale factor ('+args.resample+' moving average)')
    mindate,maxdate = _get_minmaxdate(scals)
    ax.set_xlim([mindate,maxdate])
    fig.savefig(args.ofile,bbox_inches='tight')
    plt.close()
    log.info('Figure saved to {}'.format(args.ofile))
    return


def _get_minmaxdate(scals):
    mindate = min(scals.reset_index()['date'])
    mindate = dt.datetime(mindate.year,mindate.month,1)
    maxdate = max(scals.reset_index()['date'])
    maxdate = dt.datetime(maxdate.year,maxdate.month,1)
    maxdate = maxdate + dt.timedelta(days=35)
    maxdate = dt.datetime(maxdate.year,maxdate.month,1)
    return mindate,maxdate

def _read_file(args,iday):
    log = logging.getLogger(__name__)
    ifile = iday.strftime(args.ifile_template)
    if os.path.isfile(ifile):
        log.info('reading {}'.format(ifile))
        ds = xr.open_dataset(ifile)
        iscals = pd.DataFrame()
        iscals['date'] = [iday]
        for m in masks:
            lon1 = masks[m][0]
            lon2 = masks[m][1]
            lat1 = masks[m][2]
            lat2 = masks[m][3]
            if lon1==lon2 or lat1==lat2:
                iscals[m] = [ds['scal'].sel(lon=lon1,lat=lat1,method='nearest').values.mean()]
            else:
                iscals[m] = [ds['scal'].sel(lon=slice(lon1,lon2),lat=slice(lat1,lat2)).values.mean()]
        ds.close()
    else:
        log.info('file does not exist - skip: {}'.format(ifile))
        iscals = None
    return iscals


def parse_args():
    p = argparse.ArgumentParser(description='Undef certain variables')
    p.add_argument('-i', '--ifile_template',type=str,help='input file template',default='nc/%Y/omiscal_2x2.5_%Y%m%d.nc')
    p.add_argument('-o', '--ofile',type=str,help='output file',default='omiscal_trend.pdf')
    p.add_argument('-y1', '--year1',type=str,help='start year',default=2018)
    p.add_argument('-y2', '--year2',type=str,help='end year',default=2020)
    p.add_argument('-s', '--resample',type=str,help='resample frequency',default='14D')
    return p.parse_args()


if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    main(parse_args())

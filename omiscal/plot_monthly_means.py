#!/bin/python
import xarray as xr
import numpy as np
import datetime as dt
import logging
import glob
import argparse
import sys
import os
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.cm import get_cmap
import cartopy.crs as ccrs
import cartopy.feature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from calendar import monthrange
from mpl_toolkits.axes_grid1 import AxesGrid
from cartopy.mpl.geoaxes import GeoAxes
from multiprocessing.pool import ThreadPool
import dask


def main(args):
    # read template file 
    log = logging.getLogger(__name__)
    dask.config.set(pool=ThreadPool(10))
    nrow = 4
    ncol = 3
    proj = ccrs.PlateCarree()
    axes_class = (GeoAxes, dict(map_projection=proj))
    fig = plt.figure(figsize=(13,8))
    axgr = AxesGrid(fig, 111, axes_class=axes_class, nrows_ncols=(nrow,ncol), axes_pad=0.1, cbar_location='bottom',cbar_mode='single',cbar_pad=0.2,cbar_size='3%',label_mode='')
    for imonth in range(args.nmonths):
        idate = dt.datetime(args.year,imonth+1,1)
        ifiles = idate.strftime(args.ifile_template)
        log.info('Reading {}'.format(ifiles))
        ds = xr.open_mfdataset(ifiles) 
        if args.year_change==1:
            idate_ref = dt.datetime(idate.year-1,idate.month,1)
            ifiles_ref = idate_ref.strftime(args.ifile_template)
            log.info('reading {}'.format(ifiles_ref))
            ds_ref = xr.open_mfdataset(ifiles_ref)
        else:
            ds_ref = None 
        ax = axgr[imonth]
        cp = _make_plot(ax,proj,ds,idate,ds_ref)
        ds.close()
    lab = 'Year-over-year scale factor change' if args.year_change==1 else 'Emission scale factor'
    cbar = axgr.cbar_axes[0].colorbar(cp)
    cbar.ax.set_title(lab)
    ttle = 'Year-over-year change in scale factor, %Y' if args.year_change==1 else 'Scale factors for %Y'
    fig.suptitle(idate.strftime(ttle))
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])
    ofile = idate.strftime(args.ofile_template) 
    plt.savefig(ofile,bbox_inches='tight')
    plt.close()
    log.info('Figure saved to {}'.format(ofile))
    return


def _make_plot(ax,proj,ds,anadate,ds_ref=None):
    log = logging.getLogger(__name__)
    _ = ax.coastlines()
    colormap = get_cmap('bwr')
    lons = np.arange(-180.,180.001,step=ds.lon.values[1]-ds.lon.values[0])
    lats = np.arange(-90.,90.001,step=ds.lat.values[1]-ds.lat.values[0])
    if ds_ref is not None:
        vals = ds['scal'].mean(dim='time') / ds_ref['scal'].mean(dim='time')
    else:
        vals = ds['scal'].mean(dim='time')
    cp = ax.pcolormesh(lons,lats,vals,transform=proj,cmap=colormap,vmin=0.0,vmax=2.0)
    props = dict(facecolor='white',pad=1.0) #, alpha=0.5)
    ax.text(x=0.0,y=-80.0,s=anadate.strftime('%B'),bbox=props,ha='center')
    return cp


def parse_args():
    p = argparse.ArgumentParser(description='Undef certain variables')
    p.add_argument('-y', '--year',type=int,help='year',default=2020)
    p.add_argument('-n', '--nmonths',type=int,help='number of months',default=1)
    p.add_argument('-i', '--ifile_template',type=str,help='input file template',default='nc/%Y/omiscal_2x2.5_%Y%m*.nc')
    p.add_argument('-o', '--ofile_template',type=str,help='output file template',default='png/omiscal_monthly_%Y.png')
    p.add_argument('-yoy', '--year_change',type=int,help='plot the year over year change, instead of the actual scale factor',default=0)
    return p.parse_args()


if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    main(parse_args())

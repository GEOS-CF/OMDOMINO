#!/bin/python
import xarray as xr
import numpy as np
import datetime as dt
import logging
import glob
import argparse
import sys
import os
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.cm import get_cmap
import cartopy.crs as ccrs
import cartopy.feature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from calendar import monthrange
from mpl_toolkits.axes_grid1 import AxesGrid
from cartopy.mpl.geoaxes import GeoAxes


def main(args):
    # read template file 
    log = logging.getLogger(__name__)
    ref = dt.datetime(args.year,args.month,1)
    for imonth in range(args.nmonths):
        current = ref
        cnt = 0
        while cnt < imonth:
            tmp = current + dt.timedelta(days=35)
            current = dt.datetime(tmp.year,tmp.month,1)
            cnt += 1
        nrow = 8
        ncol = 4
        proj = ccrs.PlateCarree()
        axes_class = (GeoAxes, dict(map_projection=proj))
        fig = plt.figure(figsize=(20,15))
        #gs  = GridSpec(nrow,ncol)
        axgr = AxesGrid(fig, 111, axes_class=axes_class, nrows_ncols=(8,4), axes_pad=0.1, cbar_location='bottom',cbar_mode='single',cbar_pad=0.2,cbar_size='3%',label_mode='')
        days_in_month = monthrange(current.year,current.month)[1]
        days_in_month = 28 if current.month==2 else days_in_month
        thisdays = [dt.datetime(current.year,current.month,i+1) for i in range(days_in_month)]
        for i, ax in enumerate(axgr):
            if i >= len(thisdays):
                break
            iday=thisdays[i]
            ifile = iday.strftime(args.ifile_template)
            if not os.path.isfile(ifile):
                log.info('file not found - skip {}'.format(ifile))
                continue
            log.info('reading {}'.format(ifile))
            do = xr.open_dataset(ifile)
            #ax = fig.add_subplot(gs[i,j],projection=proj)
            cp = _make_plot(ax,proj,do,iday)
            do.close()
        axgr.cbar_axes[0].colorbar(cp)
        fig.suptitle(current.strftime('%B %Y'))
        fig.tight_layout(rect=[0, 0.03, 1, 0.97])
        ofile = current.strftime(args.ofile_template) 
        plt.savefig(ofile,bbox_inches='tight')
        plt.close()
        log.info('Figure saved to {}'.format(ofile))
    return


def _make_plot(ax,proj,do,anadate):
    log = logging.getLogger(__name__)
    _ = ax.coastlines()
    colormap = get_cmap('bwr')
    lons = np.arange(-180.,180.001,step=do.lon.values[1]-do.lon.values[0])
    lats = np.arange(-90.,90.001,step=do.lat.values[1]-do.lat.values[0])
    cp = ax.pcolormesh(lons,lats,do['scal'].values[0,:,:],transform=proj,cmap=colormap,vmin=0.0,vmax=2.0)
    #ax.set_title(anadate.strftime('%Y-%m-%d'))
    #props = dict(boxstyle='round', facecolor='lightgray') #, alpha=0.5)
    props = dict(facecolor='white',pad=1.0) #, alpha=0.5)
    ax.text(x=0.0,y=-80.0,s=anadate.strftime('%Y-%m-%d'),bbox=props,ha='center')
    return cp


def parse_args():
    p = argparse.ArgumentParser(description='Undef certain variables')
    p.add_argument('-y', '--year',type=int,help='starting year',default=2020)
    p.add_argument('-m', '--month',type=int,help='starting month',default=1)
    p.add_argument('-n', '--nmonths',type=int,help='number of months',default=1)
    p.add_argument('-i', '--ifile_template',type=str,help='input file template',default='nc/%Y/omiscal_2x2.5_%Y%m%d.nc')
    p.add_argument('-o', '--ofile_template',type=str,help='output file template',default='png/%Y/omiscal_%Y%m.png')
    return p.parse_args()


if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    main(parse_args())

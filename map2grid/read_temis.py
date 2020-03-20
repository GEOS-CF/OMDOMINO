#!/bin/python
import xarray as xr
import numpy as np
import datetime as dt
import logging
import glob
import argparse
import sys


def read_temis(args):
    # read template file 
    log = logging.getLogger(__name__)
    do = xr.open_dataset(args.template)
    do.TroposphericNO2.values[:] = 0.0
    # analysis date
    anadate = dt.datetime(args.year,args.month,args.day)
    # read all files
    ifiles = glob.glob(anadate.strftime(args.idir))
    for ifile in ifiles:
        do = _read_single_file(args,ifile,do)
    # save out
    do.attrs['History'] = dt.datetime.now().strftime('Created by read_temis.py on %Y-%m-%d %H:%M')
    do.attrs['history'] = ""
    do.attrs['Author'] = 'read_temis.py (written by Christoph Keller)' 
    do['time'].values = [anadate]
    ofile = anadate.strftime(args.ofile)
    do.to_netcdf(ofile)
    log.info('OMI NO2 data written to {}'.format(ofile))
    return
 
 
def _read_single_file(args,ifile,do):
    log = logging.getLogger(__name__)
    log.info('Reading {}'.format(ifile))
    df = xr.open_dataset(ifile,group='HDFEOS/SWATHS/DominoNO2/Data Fields')
    gl = xr.open_dataset(ifile,group='HDFEOS/SWATHS/DominoNO2/Geolocation Fields')
    # get lower and upper band index to read
    nrows = df.dims.get('phony_dim_1')
    i1 = args.rows_skip
    i2 = nrows - args.rows_skip + 1
    # get tropospheric NO2
    tno2_all = df.variables['TroposphericVerticalColumn'][:,i1:i2]
    flag = df.variables['TroposphericColumnFlag'][:,i1:i2]
    albd = df.variables['SurfaceAlbedo'][:,i1:i2]
    albd.values[np.isnan(albd.values)] = 0.0
    # get time at beginning of scan 
    ##reftime = dt.datetime(1993,1,1,0,0,0,0)
    ##offsets = gl.variables['Time'].values
    ##scantime = [reftime + dt.timedelta(seconds=i) for i in offsets]
    # get coordinates
    lats_all = gl.variables['Latitude'][:,i1:i2]
    lons_all = gl.variables['Longitude'][:,i1:i2]
    # select valid entries, flatten arrays
    mask = (flag.values==0.0) & (albd.values*0.0001<0.3)
    tno2 = tno2_all.values[mask]
    lats = lats_all.values[mask]
    lons = lons_all.values[mask]
    log.debug('Found {:,} valid values (of {:,} total values = {:.2f}%)'.format(np.sum(mask),flag.shape[0]*flag.shape[1],100.0*np.sum(mask)/(np.float(flag.shape[0]*flag.shape[1]))))
    # ignore negative values
    mask = tno2>0.0
    tno2 = tno2[mask]
    lats = lats[mask]
    lons = lons[mask]
    # output grid
    olons = do.lon.values
    olats = do.lat.values
    # get lat/lon indeces of original data on new grid 
    lonidx = [np.abs(olons-i).argmin() for i in lons] 
    latidx = [np.abs(olats-i).argmin() for i in lats]
    # combine into single lat/lon index
    idx = np.array([i*100000000.0+(10000.0+j) for i,j in zip(lonidx,latidx)])
    unique_idx = np.unique(idx)
    # map onto new array - loop over all unique vlaues
    for i in unique_idx:
        vals = tno2[idx==i]
        if len(vals) > 0:
            ilon = np.int(i//1e8) 
            jlat = np.int(np.mod(i,10000.0))
            do.TroposphericNO2.values[0,jlat,ilon] = do.TroposphericNO2.values[0,jlat,ilon] + np.mean(vals)
    return do


def parse_args():
    p = argparse.ArgumentParser(description='Undef certain variables')
    p.add_argument('-y', '--year',type=int,help='year',default=-1)
    p.add_argument('-m', '--month',type=int,help='month',default=-1)
    p.add_argument('-d', '--day',type=int,help='day',default=-1)
    p.add_argument('-t', '--template',type=str,help='output template file',default='templates/template_5x5.nc')
    p.add_argument('-i', '--idir',type=str,help='input directory',default='he5/%Y/%Y%m%d/*.he5')
    p.add_argument('-o', '--ofile',type=str,help='output file',default='nc_5x5/%Y/OMI-Aura_L2-OMDOMINO_5x5_%Y%m%d.nc')
    p.add_argument('-r', '--rows_skip',type=int,help='number of rows to skip on either side',default=0)
    return p.parse_args()    


if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    read_temis(parse_args())

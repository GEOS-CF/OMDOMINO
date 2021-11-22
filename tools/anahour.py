#!/bin/python
import xarray as xr
import numpy as np
import datetime as dt
import logging
import glob
import argparse
import sys
import pandas as pd
import os


def main(args):
    '''
    Create gridded map indicating observation hour (closest integer hour) for each (NO2) analysis increment. 
    '''
    log = logging.getLogger(__name__)
    # parse date
    anadate = dt.datetime.strptime(args.date,'%Y-%m-%d %H:%M')
    # read analysis & background file 
    ana = _read_file(args.anafile,anadate)
    bkg = _read_file(args.bkgfile,anadate)
#---Get closest integer hour for each OMI observation in the obsfile, mapped onto the same grid as ana/bkg
    # create default array for gridded obs hour
    tno2_hour = np.zeros((1,len(ana.lat),len(ana.lon)))
    cnt = np.zeros((24,tno2_hour.shape[1],tno2_hour.shape[2]))
    # read the preprocessed OMNO2 file
    satfile = anadate.strftime(args.satfile)
    tno2_hour,cnt = _process_omi_file(args,satfile,ana,tno2_hour,cnt)
    # calculate average values
    cntsum = np.sum(cnt,axis=0)
    obshour = cnt.argmax(axis=0)
    msk = cntsum>0.0
    #tno2_hour[0,msk] = tno2_hour[0,msk] / cntsum[msk]
    tno2_hour[0,msk] = obshour[msk]
    # set missing values to nan
    msk = (cntsum<=0.0)
    tno2_hour[0,msk] = np.nan
#---Get map with analysis hour, i.e., a map with the closest integer obs hour for each analysis increment
    ana_hour = _get_ana_hour(args,ana,bkg,tno2_hour)
#---Create new data set and write to netCDF file
    do = xr.Dataset(
       data_vars=dict(ana_hour=(["time","lat","lon"],ana_hour,dict(long_name='analysis_nearest_hour',units='hour'))),
       coords=dict(
           {"time":("time",[anadate.hour+anadate.minute/60.],{"units":anadate.strftime("hours since %Y-%m-%d")})},
           lon=ana.lon,
           lat=ana.lat,
       ),
       attrs=dict(description="Nearest observation hour for analysis"), 
    )
    do.attrs['History'] = dt.datetime.now().strftime('Created by anahour.py on %Y-%m-%d %H:%M')
    do.attrs['Author'] = 'anahour.py (written by Christoph Keller)' 
    #do['time'].values = [anadate]
    ofile = anadate.strftime(args.outfile)
    do.to_netcdf(ofile,unlimited_dims='time')
    log.info('Observation hour written to {}'.format(ofile))
#---Cleanup
    ana.close()
    bkg.close()
    do.close()
    return


def _get_ana_hour(args,ana,bkg,tno2_hour):
    '''
    Create map with analysis hour for each non-zero analysis increment.
    '''
    log = logging.getLogger(__name__)
    ana_hour = np.zeros(tno2_hour.shape)*np.nan
    # count non-zero increments per column
    inc = ana[args.var].values[0,:,:,:] - bkg[args.var].values[0,:,:,:]
    non0 = inc!=0.0
    non0d2 = non0.sum(axis=0)
    if not np.any(non0d2>0.0):
        log.warning('No increments found - ana_hour is empty!')
        return ana_hour
    # get vector of all lat/lons with non-nan observations for more convenient indexing below
    gridlats = ana.lat.values[:].repeat(len(ana.lon))
    gridlons = np.tile(ana.lon.values,len(ana.lat))
    obshour = tno2_hour.flatten()
    obsmsk = ~np.isnan(obshour)
    obshour = obshour[obsmsk]
    obslats = gridlats[obsmsk]
    obslons = gridlons[obsmsk]
    #obslonidx = [np.abs(ana.lon.values-i).argmin() for i in obslons] 
    #obslatidx = [np.abs(ana.lat.values-i).argmin() for i in obslats]
    # go over all lat/lons with an increment and assign the obs hour to it
    non01d = non0d2.flatten()
    anamsk = non01d>0.0
    non01d = non01d[anamsk]
    analats = gridlats[anamsk]
    analons = gridlons[anamsk]
    analonidx = [np.abs(ana.lon.values-i).argmin() for i in analons] 
    analatidx = [np.abs(ana.lat.values-i).argmin() for i in analats]
    # assing hour from tno2 observation 
    idxs = [np.array((obslons-i)**2+(obslats-j)**2).argmin() for i,j in zip(analons,analats)]
    ana_hour[0,analatidx,analonidx] = obshour[idxs]
    return ana_hour
#    ihour = tno2_hour[0,analatidx,analonidx]
#    ana_hour[0,analatidx,analonidx] = ihour
#    # check for nans 
#    imsk = np.isnan(ihour)
#    if np.any(imsk):
#        nanlats = np.array(analats)[imsk]
#        nanlons = np.array(analons)[imsk]
#        nanlatidxs = np.array(analatidx)[imsk]
#        nanlonidxs = np.array(analonidx)[imsk]
#        idxs = [np.array((obslons-i)**2+(obslats-j)**2).argmin() for i,j in zip(nanlons,nanlats)]
#        ana_hour[0,nanlatidxs,nanlonidxs] = obshour[idxs]
#        for i in range(len(nanlats)):
#            #nanlat = nanlats[i]
#            #nanlon = nanlons[i]
#            ilatidx = nanlatidxs[i]
#            ilonidx = nanlonidxs[i]
#            #distance_to_cell = [(nanlon-i)**2+(nanlat-j)**2 for i,j in zip(obslons,obslats)]
#            distance_to_cell = [(ilonidx-i)**2+(ilatidx-j)**2 for i,j in zip(obslonidx,obslatidx)]
#            idx = np.array(distance_to_cell).argmin()
#            ana_hour[0,ilatidx,ilonidx] = obshour[idx]
# old loop:
#    for iana in range(len(non01d)):
#        analon = analons[i]
#        analat = analats[i]
#        ihour = tno2_hour[0,analat,analon]
#        # if nan, get closest non-nan observation
#        if np.isnan(ihour):
#            distance_to_cell = [(analon-i)**2+(analat-j)**2 for i,j in zip(obslons,obslats)]
#            idx = distance_to_cell.argmin()
#            ihour = obshour[idx]
#        ana_hour[0,analat,analon] = ihour

 
def _process_omi_file(args,satfile,ana,tno2_hour,cnt):
    '''
    Read single OMI NO2 file and put nearest hour of (non-nan) observations onto a grid.
    '''
    log = logging.getLogger(__name__)
    if not os.path.isfile(satfile):
        log.error('Satellite file not found: {}'.format(satfile))
        return
    log.info('Reading {}'.format(satfile))
    ds = xr.open_dataset(satfile)
    tno2_all = ds.variables['ColumnAmountNO2Trop'].values[:]
    mask = ~np.isnan(tno2_all)
    tno2 = tno2_all[mask].copy()
    lats = ds.variables['Latitude'].values[mask].copy()
    lons = ds.variables['Longitude'].values[mask].copy()
    hour = ds.variables['Hour'].values[mask].copy()
    mint = ds.variables['Minute'].values[mask].copy()
    # get 'rounded hour'
    rhr = [h if m < 30 else h+1 for h,m in zip(hour,mint)]
    rhr = [0 if h >=24 else h for h in rhr]
    rhr = np.array(rhr)
    log.info('Found {:,} valid values (of {:,} total values = {:.2f}%)'.format(tno2.shape[0],tno2_all.shape[0],tno2.shape[0]/tno2_all.shape[0]*100.))
    # output grid
    olons = ana.lon.values
    olats = ana.lat.values
    # loop over all hours separately
    for h in np.unique(rhr):
        imsk = [rhr==h]
        ilons = lons[tuple(imsk)]
        ilats = lats[tuple(imsk)]
        irhr  = rhr[tuple(imsk)]
        # get lat/lon indeces of original data on new grid 
        lonidx = [np.abs(olons-i).argmin() for i in ilons] 
        latidx = [np.abs(olats-i).argmin() for i in ilats]
        # combine into single lat/lon index
        idx = np.array([i*100000000.0+(10000.0+j) for i,j in zip(lonidx,latidx)])
        unique_idx = np.unique(idx)
        # map onto new array - loop over all unique values
        for i in unique_idx:
            vals = irhr[idx==i]
            if len(vals) > 0:
                ilon = np.int(i//1e8) 
                jlat = np.int(np.mod(i,10000.0))
                tno2_hour[0,jlat,ilon] += np.sum(vals)
                cnt[int(h),jlat,ilon] += np.float(len(vals))
    ds.close()
    return tno2_hour,cnt


def _read_file(template,idate):
    '''Read file from file template for given data'''
    log = logging.getLogger(__name__)
    ifile = idate.strftime(template)
    if not os.path.isfile(ifile):
        log.error('File does not exist: {}'.format(ifile))
        return
    ds = xr.open_dataset(ifile)
    return ds


def parse_args():
    p = argparse.ArgumentParser(description='Undef certain variables')
    p.add_argument('-d', '--date',type=str,help='date in format %Y-%m-%d %H:%M',default='2018-07-01 12:00')
    p.add_argument('-a', '--anafile',type=str,help='analysis file',default='/discover/nobackup/cakelle2/CDAS/runs/omno2_test/scratch/omno2_test.ana.eta.%Y%m%d_%Hz.nc4')
    p.add_argument('-b', '--bkgfile',type=str,help='background file',default='/discover/nobackup/cakelle2/CDAS/runs/omno2_test/temp/omno2_test.cbkg.eta.%Y%m%d_%Hz.nc4')
    p.add_argument('-s', '--satfile',type=str,help='satellite file',default='/discover/nobackup/cakelle2/CDAS/runs/omno2_test/analyze/spool/omno2.%Y%m%d.t%Hz.nc')
    p.add_argument('-v', '--var',type=str,help='file variable of interest',default='NO2')
    p.add_argument('-o', '--outfile',type=str,help='output file',default='ana_hours.%Y%m%d_t%Hz.nc')
    return p.parse_args()    


if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    main(parse_args())



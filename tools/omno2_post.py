#!/usr/local/other/python/GEOSpyD/2019.03_py3.7/2019-04-22/bin/python
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
    Postprocessing script to create netCDF file with background, analysis, and increment fields plus closest 
    (full) observation hour for each grid cell where the increment is non-zero. 
    '''
    log = logging.getLogger(__name__)
    # parse date
    anadate = dt.datetime.strptime(args.date,'%Y%m%d_%H%Mz')
    # read analysis & background file 
    ana = _read_file(args.anafile,anadate)
    bkg = _read_file(args.bkgfile,anadate)
#---Get closest integer hour for each OMI observation in the obsfile, mapped onto the same grid as ana/bkg
    # create default array for gridded obs hour
    tno2_hour = np.zeros((1,len(ana.lat),len(ana.lon)))
    cnt = np.zeros((24,tno2_hour.shape[1],tno2_hour.shape[2]))
    # read the preprocessed OMNO2 file
    tno2_hour,cnt = _process_omi_file(args,anadate,ana,tno2_hour,cnt)
    # calculate average values
    cntsum = np.sum(cnt,axis=0)
    obshour = cnt.argmax(axis=0)
    msk = cntsum>0.0
    tno2_hour[0,msk] = obshour[msk]
    # set missing values to nan
    msk = (cntsum<=0.0)
    tno2_hour[0,msk] = np.nan
#---Get map with analysis hour, i.e., a map with the closest integer obs hour for each analysis increment
    ana_hour = _get_ana_hour(args,ana,bkg,tno2_hour)
#---Calculate analysis increment
    inc = ana['NO2'].values[:,:,:,:] - bkg['NO2'].values[:,:,:,:]
#---data variables to be added to the output dataset
    data_vars=dict(
       ana_no2=(["time","lev","lat","lon"],ana['NO2'],dict(long_name='analysis_no2',units='v/v')),
       bkg_no2=(["time","lev","lat","lon"],bkg['NO2'],dict(long_name='background_no2',units='v/v')),
       inc_no2=(["time","lev","lat","lon"],inc,dict(long_name='no2_analysis_increment',units='v/v')),
       ana_hour=(["time","lat","lon"],ana_hour,dict(long_name='analysis_nearest_hour',units='hour')),
    )
    # mask for each hour of the day (showing the grid cells with observations for a given hour)
    if args.write_mask==1:
        for h in range(24):
            vname = 'ana_mask_H{:02d}'.format(h)
            iarr = np.zeros(ana_hour.shape)
            iarr[ana_hour==h] = 1.0
            data_vars[vname] =(["time","lat","lon"],iarr,dict(long_name='analysis_mask_hour_{:02d}'.format(h),units='1'))
#---Create new data set and write to netCDF file
    do = xr.Dataset(
       data_vars=data_vars,
       coords=dict(
           {"time":("time",[anadate.hour+anadate.minute/60.],{"units":anadate.strftime("hours since %Y-%m-%d 00:00:00")})},
           lev=ana.lev,
           lon=ana.lon,
           lat=ana.lat,
       ),
       attrs=dict(description="Nearest observation hour for analysis"), 
    )
    do.attrs['History'] = dt.datetime.now().strftime('Created by omno2_post.py on %Y-%m-%d %H:%M')
    do.attrs['Author'] = 'omno2_post.py (written by Christoph Keller)' 
    ofile = anadate.strftime(args.outfile)
    do.to_netcdf(ofile,unlimited_dims='time')
    log.info('Postprocessed NO2 data written to {}'.format(ofile))
#---Cleanup
    ana.close()
    bkg.close()
    do.close()
    return


def _get_ana_hour(args,ana,bkg,tno2_hour):
    '''
    Get the analysis hour for each column where at least one model level a non-zero analysis increment.
    The analysis hour is defined as the observation hour of the closest available OMI observation. 
    '''
    log = logging.getLogger(__name__)
    ana_hour = np.zeros(tno2_hour.shape)*np.nan
    # get all lat/lons with at least one non-zero increment in the column
    inc = ana['NO2'].values[0,:,:,:] - bkg['NO2'].values[0,:,:,:]
    non0 = inc!=0.0
    non0d2 = non0.sum(axis=0)
    if not np.any(non0d2>0.0):
        log.warning('No increments found - ana_hour is empty!')
        return ana_hour
    # get vector of all lat/lons with valid entries for more convenient indexing below
    gridlats = ana.lat.values[:].repeat(len(ana.lon))
    gridlons = np.tile(ana.lon.values,len(ana.lat))
    obshour = tno2_hour.flatten()
    obsmsk = ~np.isnan(obshour)
    obshour = obshour[obsmsk]
    obslats = gridlats[obsmsk]
    obslons = gridlons[obsmsk]
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

 
def _process_omi_file(args,anadate,ana,tno2_hour,cnt):
    '''
    Read single OMI NO2 file and put nearest hour of (non-nan) observations onto a grid.
    '''
    log = logging.getLogger(__name__)
    ds = _read_file(args.satfile,anadate) 
    tno2_all = ds.variables['ColumnAmountNO2Trop'].values[:]
    albd_all = ds.variables['TerrainReflectivity'].values[:]
    cldf_all = ds.variables['CloudRadianceFraction'].values[:]
    sza_all  = ds.variables['SolarZenithAngle'].values[:]
    scd_all  = ds.variables['SlantColumnAmountNO2Destriped'].values[:]
    flag_all = ds.variables['VcdQualityFlags'].values[:].astype(int)&1   # bitwise and operation
    albd_all[np.isnan(albd_all)] = 0.0
    cldf_all[np.isnan(cldf_all)] = 0.0
    scd_all[np.isnan(scd_all)]   = -999.0
    #mask = ~np.isnan(tno2_all)
    mask = ( (flag_all==0) & (albd_all<=300.0) & (cldf_all<=500.0) & (scd_all>0.0) & (sza_all<=80.0) )
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
    '''Read file from template for given date'''
    log = logging.getLogger(__name__)
    ifile = idate.strftime(template)
    if not os.path.isfile(ifile):
        log.error('File does not exist: {}'.format(ifile))
        return
    ds = xr.open_dataset(ifile)
    return ds


def parse_args():
    p = argparse.ArgumentParser(description='Undef certain variables')
    p.add_argument('-d', '--date',type=str,help='date in format %Y%m%d_%H%Mz',default='20180701_1200z')
    p.add_argument('-a', '--anafile',type=str,help='analysis file',default='ana.eta.nc4')
    p.add_argument('-b', '--bkgfile',type=str,help='background file',default='cbkg.eta.nc4')
    p.add_argument('-s', '--satfile',type=str,help='satellite file',default='omno2.%Y%m%d.t%Hz.nc')
    p.add_argument('-o', '--outfile',type=str,help='output file',default='ana_no2.after_gsi.%Y%m%d_t%Hz.nc')
    p.add_argument('-m', '--write_mask',type=int,help='write mask file for each hour of day?',default=0)
    return p.parse_args()    


if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    main(parse_args())


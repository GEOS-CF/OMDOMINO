#!/bin/python
import xarray as xr
import numpy as np
import datetime as dt
import logging
import glob
import argparse
import sys
import os
from calendar import monthrange


def get_omiscal(args):
    '''
    Calculate (daily) scale factor based on gridded OMI NO2 column data,
    as prepared by 'read_temis.py'.
    '''
    # read template file 
    log = logging.getLogger(__name__)
    do = xr.open_dataset(args.template.replace('$res',args.res))
    do.scal.values[:] = 1.0
    # analysis date
    if args.year < 0 or args.month < 0 or args.day < 0:
        tdy = dt.datetime.today()
        anadate = dt.datetime(tdy.year,tdy.month,tdy.day)
    else:
        anadate = dt.datetime(args.year,args.month,args.day)
    # read all files
    do = _calc_scal(args,anadate,do)
    # save out
    do.attrs['History'] = dt.datetime.now().strftime('Created by calc_omiscal.py on %Y-%m-%d %H:%M')
    do.attrs['history'] = ""
    do.attrs['Author'] = 'calc_omiscal.py (written by Christoph Keller)' 
    do['time'].values = [anadate]
    ofile = anadate.strftime(args.ofile.replace('$res',args.res))
    do.to_netcdf(ofile)
    log.info('OMI scale factor written to {}'.format(ofile))
    # make a quick plot
    if args.plot==1:
        _make_plot(do,ofile.replace('.nc','.png'),anadate)
    return


def _calc_scal(args,anadate,do):
    '''
    Calculate spatial scale factors by normalizing current OMI NO2 column
    with the equivalent values from a previous time period.
    '''
    log = logging.getLogger(__name__)
    # get background NO2 (from reference year)
    before = 14
    after  = 7
    for i in range(args.nyears):
        # catch Feb 29:
        ndays = monthrange(args.refyear-i,anadate.month)[1] 
        iday = anadate.day if anadate.day <= ndays else ndays
        ref = dt.datetime(args.refyear-i,anadate.month,iday)
        start = ref - dt.timedelta(days=before)
        end = ref + dt.timedelta(days=after)
        tmp = _get_average(args,start,end)
        if i==0:
            bg = tmp.copy()
            cnt = np.zeros(bg.shape)
            cnt[~np.isnan(tmp)] += 1.0
        else:
            bg = np.nansum(np.dstack((bg,tmp)),2)
            cnt[~np.isnan(tmp)] += 1.0
            bg[bg==0.0] = np.nan
    mask = cnt > 0.0
    bg[mask] = bg[mask] / cnt[mask]
    bg[np.isnan(bg)] = 0.0
    # get current NO2 (last 7 days)
    start = anadate - dt.timedelta(days=7)
    end   = anadate
    cr = _get_average(args,start,end)
    cr[np.isnan(cr)] = 0.0
    # get scale factor by normalizing background and current
    scal = np.ones(cr.shape) 
    mask = (bg>0.0) & (cr>0.0)
    scal[mask] = cr[mask] / bg[mask]
    # limit to minimum/maximum values
    scal[scal<args.minval] = args.minval 
    scal[scal>args.maxval] = args.maxval 
    do.scal.values[0,:,:] = scal
    return do


def _get_average(args,start,end):
    '''
    Read gridded OMI NO2 files and compute average trop. NO2 column for the
    specified time range. Only pixels with a valid observation (>0.0) are
    used. Pixels with high active fire (according to QFED) are ignored. An
    additional data mask (e.g., based on bottom up emissions or population
    density) can be provided in the input argument list to filter out
    additional cells.
    '''
    log = logging.getLogger(__name__)
    days = [start + dt.timedelta(days=i) for i in range((end-start).days)]
    mfile = args.maskfile.replace('$res',args.res)
    log.info('Reading {}'.format(mfile))
    mf = xr.open_dataset(mfile,decode_times=False)
    maskvals = mf[args.maskpara].values[0,:,:]
    maskvals[np.isnan(maskvals)] = 0.0
    olons = mf.lon.values
    olats = mf.lat.values
    nread = 0
    for i,d in enumerate(days):
        ifile = d.strftime(args.ifile.replace('$res',args.res))
        if not os.path.isfile(ifile):
            log.warning('File does not exist - skip: {}'.format(ifile))
            continue
        log.info('Reading {}'.format(ifile))
        ids = xr.open_dataset(ifile)
        iarr = ids['TroposphericNO2'].values[0,:,:]
        if nread==0:
            arr = np.zeros(iarr.shape)
            cnt = np.zeros(iarr.shape)
            nread += 1
        # create fire mask 
        firemask = np.zeros(iarr.shape)
        ffile = d.strftime(args.firefile)
        log.info('reading {}'.format(ffile))
        fd = xr.open_dataset(ffile)
        hasfire = fd[args.firepara].values[0,:,:] > args.firethreshold
        idxs = np.where(hasfire)
        lonidx = [np.abs(olons-i).argmin() for i in fd.lon.values[idxs[1]]]
        latidx = [np.abs(olats-i).argmin() for i in fd.lat.values[idxs[0]]]
        idx = tuple((np.array(latidx),np.array(lonidx)))
        firemask[idx] = 1.0
        mask = np.where( (iarr>args.no2_threshold) & (firemask==0.0) & (maskvals>args.maskvalue) )
        arr[mask] = arr[mask] + iarr[mask]
        cnt[mask] += 1.0 
    # calculate average
    mask = cnt > 0.0
    arr[mask] = arr[mask] / cnt[mask]
    arr[~mask] = np.nan
    return arr 


def _make_plot(do,ofile_png,anadate):
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from matplotlib.cm import get_cmap
    import cartopy.crs as ccrs
    import cartopy.feature
    from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
    log = logging.getLogger(__name__)
    fig = plt.figure(figsize=(6,3))
    gs  = GridSpec(1,1)
    proj = ccrs.PlateCarree()
    ax = fig.add_subplot(gs[0,0],projection=proj)
    _ = ax.coastlines()
    colormap = get_cmap('bwr')
    #cp = ax.contourf(do.lon.values,do.lat.values,do['scal'].values[0,:,:],transform=proj,cmap=colormap,vmin=0.0,vmax=2.0)
    lons = np.arange(-180.,180.001,step=do.lon.values[1]-do.lon.values[0])
    lats = np.arange(-90.,90.001,step=do.lat.values[1]-do.lat.values[0])
    cp = ax.pcolormesh(lons,lats,do['scal'].values[0,:,:],transform=proj,cmap=colormap,vmin=0.0,vmax=2.0)
    #do['scal'].plot(vmin=args.minval,vmax=args.maxval)
    cbar = fig.colorbar(cp,ax=ax,shrink=0.8)
    fig.suptitle(anadate.strftime('%Y-%m-%d'))
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])
    plt.savefig(ofile_png,bbox_inches='tight')
    plt.close()
    log.info('OMI scale factor map saved to {}'.format(ofile_png))
    return


def parse_args():
    p = argparse.ArgumentParser(description='Undef certain variables')
    p.add_argument('-y', '--year',type=int,help='year',default=2020)
    p.add_argument('-m', '--month',type=int,help='month',default=1)
    p.add_argument('-d', '--day',type=int,help='day',default=1)
    p.add_argument('-t', '--template',type=str,help='output template file',default='templates/omiscal_template_$res.nc')
    p.add_argument('-n', '--no2_threshold',type=float,help='NO2 threshold for summing values',default=0.0)
    p.add_argument('-i', '--ifile',type=str,help='input directory',default='/discover/nobackup/projects/gmao/geos_cf_dev/obs/OMDOMINO/map2grid/nc_$res/%Y/OMI-Aura_L2-OMDOMINO_$res_%Y%m%d.nc')
    p.add_argument('-mf', '--maskfile',type=str,help='mask file',default='templates/HTAP_NO_mean.$res.nc')
    p.add_argument('-mp', '--maskpara',type=str,help='mask parameter',default='emi_no')
    p.add_argument('-mv', '--maskvalue',type=float,help='mask value',default=5.0e-13)
#    p.add_argument('-mf', '--maskfile',type=str,help='mask file',default='templates/gpw.mask.$res.nc')
#    p.add_argument('-mp', '--maskpara',type=str,help='mask parameter',default='Population Density, v4.10 (2000, 2005, 2010, 2015, 2020): 2.5 arc-minutes')
#    p.add_argument('-mv', '--maskvalue',type=float,help='mask value',default=1.0)
    p.add_argument('-mn', '--minval',type=float,help='minimum scale value',default=0.1)
    p.add_argument('-mx', '--maxval',type=float,help='maximum scale value',default=1.5)
    p.add_argument('-o', '--ofile',type=str,help='output file',default='test.nc')
    p.add_argument('-ff', '--firefile',type=str,help='fire file',default='/discover/nobackup/projects/gmao/share/dao_ops/fvInput_nc3/PIESA/sfc/QFED/NRT/v2.5r1_0.1_deg/Y%Y/M%m/qfed2.emis_no.006.%Y%m%d.nc4')
    p.add_argument('-fp', '--firepara',type=str,help='biomass',default='biomass')
    p.add_argument('-ft', '--firethreshold',type=float,help='fire mask threshold',default=1.0e-9) #1.0e-12)
    p.add_argument('-r', '--res',type=str,help='resolution',default='5x5')
    p.add_argument('-ny', '--nyears',type=int,help='number of previous years to include',default=1)
    p.add_argument('-ry', '--refyear',type=int,help='reference year for normalization',default=2017)
    p.add_argument('-p', '--plot',type=int,help='make plot',default=1)
    return p.parse_args()    


if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    get_omiscal(parse_args())

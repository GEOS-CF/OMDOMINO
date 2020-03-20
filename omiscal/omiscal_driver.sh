#!/bin/bash
# this is the driver routine to download and process DOMINO NO2 data

odir="/discover/nobackup/projects/gmao/geos_cf_dev/gcc_inputs/OMISCAL/v0"
srcdir="/discover/nobackup/projects/gmao/geos_cf_dev/obs/OMDOMINO"

# parse input arguments
Ymd=$1
ForceRead=$2

# extract date
Y=`echo ${Ymd} | cut -c1-4`
M=`echo ${Ymd} | cut -c5-6`
D=`echo ${Ymd} | cut -c7-8`

# get temis data and produce 5x5 gridded fields
cd ${srcdir}/map2grid
./get_temis_and_remap.sh $Ymd $ForceRead

# calculate scale factors at 5x5, then regrid to 2x2.5
cd ${srcdir}/omiscal
/usr/local/other/python/GEOSpyD/2019.03_py3.7/2019-04-23/bin/python calc_omiscal.py -y $Y -m $M -d $D -p 0 -r '5x5' -o "workdir/tmp.nc"
ofile="${srcdir}/omiscal/nc/$Y/omiscal_2x2.5_${Ymd}.nc"
if [ ! -d nc/$Y ]; then
    /bin/mkdir -p nc/$Y
fi
./regrid.sh $Ymd workdir/tmp.nc $ofile
rm -r workdir/*.nc

# update to latest scale factor 
if [ -e $ofile ]; then
    if [ -d ${odir}/${Y} ]; then
        /bin/mkdir -p ${odir}/${Y}
    fi
    tfile="${odir}/${Y}/omiscal_2x2.5_${Ymd}.nc"
    if [ -e $tfile ]; then
         /bin/rm $tfile
    fi
    /bin/ln -s $ofile $tfile 
fi 

# also make a copy of 10 days into the future
end=$(/bin/date -I -d "${Ymd} + 10 day")
d=${Ymd}
while [ "$d" != $end ]; do
 iYmd=$(date -d "$d" +%Y%m%d)
 iY=$(date -d "$d" +%Y)
 if [ -d ${odir}/${iY} ]; then
  /bin/mkdir -p ${odir}/${iY}
 fi
 tfile="${odir}/${iY}/omiscal_2x2.5_${iYmd}.nc"
 if [ -e $tfile ]; then
  /bin/rm $tfile
 fi
 /bin/ln -s $ofile $tfile
 d=$(date -I -d "$d + 1 day")
done

# visualize
if [ ! -d png/$Y ]; then
    /bin/mkdir -p png/$Y
fi
/usr/local/other/python/GEOSpyD/2019.03_py3.7/2019-04-23/bin/python plot_omiscal.py -y $Y -m $M
/usr/local/other/python/GEOSpyD/2019.03_py3.7/2019-04-23/bin/python plot_monthly_means.py -y $Y -n $M 


#!/bin/bash
# Download OMI NO2 data (produced by KNMI) and map it onto a daily file

if [[ $# -eq 0 ]]; then
 tYmd=$(/bin/date -d "yesterday" +%Y%m%d)
# use input args otherwise
else
 tYmd=$1
fi
sY=`echo ${tYmd} | cut -c1-4`
sM=`echo ${tYmd} | cut -c5-6`
sD=`echo ${tYmd} | cut -c7-8`
echo "Working on ${sY}-${sM}-${sD}"

# data directory
idir="he5/${sY}/${sY}${sM}${sD}"

# Force (re)reading of data?
if [[ $# -eq 2 ]]; then
 ForceRead=$2
else
 ForceRead=$0
fi

if [ $ForceRead -eq 1 ]; then
 if [ -d $idir ]; then
  /bin/rm -r $idir
 fi
fi

# check if data exists
if [ ! -d $idir ]; then
    /usr/bin/wget "http://www.temis.nl/airpollution/no2col/data/omi/data_v2/${sY}/omi_no2_he5_${sY}${sM}${sD}.tar"
    /bin/tar -xf omi_no2_he5_${sY}${sM}${sD}.tar
    /bin/mkdir -p $idir
    /bin/mv *.he5 $idir
    /bin/rm -r omi_no2_he5_${sY}${sM}${sD}.tar
fi 

/usr/local/other/python/GEOSpyD/2019.03_py3.7/2019-04-23/bin/python read_temis.py -y $sY -m $sM -d $sD -i 'he5/%Y/%Y%m%d/*.he5'

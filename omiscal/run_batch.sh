#!/bin/bash

# set startdate and enddate
d=2018-01-01
end=2020-03-19

# loop over all days
while [ "$d" != $end ]; do
 Ymd=$(date -d "$d" +%Y%m%d)
 Y=`echo ${Ymd} | cut -c1-4`
 M=`echo ${Ymd} | cut -c5-6`
 D=`echo ${Ymd} | cut -c7-8`
 /usr/local/other/python/GEOSpyD/2019.03_py3.7/2019-04-23/bin/python calc_omiscal.py -y $Y -m $M -d $D -p 0
 # go to next day
 d=$(date -I -d "$d + 1 day")
done

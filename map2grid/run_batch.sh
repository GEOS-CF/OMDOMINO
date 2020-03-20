#!/bin/bash

# set startdate and enddate
d=2018-01-01
end=2020-03-19

# loop over all days
while [ "$d" != $end ]; do
 Ymd=$(date -d "$d" +%Y%m%d)
 ./get_temis_and_remap.sh $Ymd
 # go to next day
 d=$(date -I -d "$d + 1 day")
done

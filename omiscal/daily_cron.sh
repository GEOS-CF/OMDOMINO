#!/bin/bash

# Yesterday
Ymd=$(/bin/date -d "yesterday" +%Y%m%d)

# Recalculate scale factors from the day before
d=$(date -d "$Ymd" +%Y%m%d)
pd=$(date -I -d "$d - 1 day")
pYmd=$(/bin/date -d $pd +%Y%m%d)
./omiscal_driver.sh $pYmd 1

# Calculate scale factors for yesterday 
./omiscal_driver.sh $Ymd 1

#!/bin/bash
# Download DOMINO NO2 data, map it onto regular grid, and calculate
# emission scale factors for yesterday and the day before

# Output directory (for symbolic link)
odir="/discover/nobackup/projects/gmao/geos_cf_dev/gcc_inputs/OMISCAL/v0"

# Yesterday
Ymd=$(/bin/date -d "yesterday" +%Y%m%d)

# Recalculate scale factors from the day before yesterday
d=$(date -d "$Ymd" +%Y%m%d)
pd=$(date -I -d "$d - 1 day")
pY=$(/bin/date -d $pd +%Y)
pYmd=$(/bin/date -d $pd +%Y%m%d)
./omiscal_driver.sh $pYmd 1

# Calculate scale factors for yesterday 
./omiscal_driver.sh $Ymd 1

# Update symbolic links
pofile="/discover/nobackup/projects/gmao/geos_cf_dev/obs/OMDOMINO/omiscal/nc/$pY/omiscal_2x2.5_${pYmd}.nc"
if [ -e $pofile ]; then
 # Remove all symbolic links 
 end=$(/bin/date -I -d "${pYmd} + 11 day")
 iday=${pYmd}
 while [ "${iday}" != $end ]; do
  iYmd=$(date -d "${iday}" +%Y%m%d)
  iY=$(date -d "${iday}" +%Y)
  tfile="${odir}/${iY}/omiscal_2x2.5_${iYmd}.nc"
  /bin/rm -r $tfile
  iday=$(date -I -d "${iday} + 1 day")
 done
 # Now set symbolic link
 tfile="${odir}/${pY}/omiscal_2x2.5_${pYmd}.nc"
 /bin/ln -s $pofile $tfile
fi

# Set symbolic link for latest file 
ofile="/discover/nobackup/projects/gmao/geos_cf_dev/obs/OMDOMINO/omiscal/nc/$Y/omiscal_2x2.5_${Ymd}.nc"
if [ -e $pofile ]; then
 rfile=${pofile}
fi 
if [ -e $ofile ]; then
 rfile=${ofile}
fi 

# also make a copy of 10 days into the future
iday=${Ymd}
while [ "${iday}" != $end ]; do
 iYmd=$(date -d "${iday}" +%Y%m%d)
 iY=$(date -d "${iday}" +%Y)
 if [ -d ${odir}/${iY} ]; then
  /bin/mkdir -p ${odir}/${iY}
 fi
 tfile="${odir}/${iY}/omiscal_2x2.5_${iYmd}.nc"
 if [ -e $tfile ]; then
  /bin/rm $tfile
 fi
 /bin/ln -s $rfile $tfile
 iday=$(date -I -d "${iday} + 1 day")
done

# Make figures
sbatch omiscal_plot.j

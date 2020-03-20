#!/bin/bash
ymd=$1
ifile=$2
ofile=$3
/usr/local/other/SLES11.3/cdo/1.9.1/gcc-5.3-sp3/bin/cdo remapdis,grid.2x25 $ifile $ofile
/discover/nobackup/projects/gmao/share/gmao_ops/Baselibs/v4.0.3_build1/x86_64-unknown-linux-gnu/ifort_13.1.2.183-intelmpi-5.0.1.035/Linux/bin/ncatted -a time_increment,time,o,i,240000 $ofile
/discover/nobackup/projects/gmao/share/gmao_ops/Baselibs/v4.0.3_build1/x86_64-unknown-linux-gnu/ifort_13.1.2.183-intelmpi-5.0.1.035/Linux/bin/ncatted -a begin_date,time,o,i,$ymd $ofile
/discover/nobackup/projects/gmao/share/gmao_ops/Baselibs/v4.0.3_build1/x86_64-unknown-linux-gnu/ifort_13.1.2.183-intelmpi-5.0.1.035/Linux/bin/ncatted -a begin_time,time,o,i,000000 $ofile

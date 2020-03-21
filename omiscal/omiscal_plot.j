#!/bin/csh
#SBATCH --time=00:15:00
#SBATCH --ntasks=1
#SBATCH --job-name=omiscalp
#SBATCH --output=log/omiscalp_%j
#SBATCH --account=s1866
#SBATCH --qos=chmdev

module load other/python/GEOSpyD/Ana2019.03_py3.7

set Ymd = `/bin/date -d "yesterday" '+%Y%m%d'`
set Y = `echo ${Ymd} | cut -c1-4`
set M = `echo ${Ymd} | cut -c5-6`
if (! -d png/$Y ) mkdir -p png/$Y
python plot_omiscal.py -y $Y -m $M
python plot_monthly_means.py -y $Y -n $M

import xarray as xr
import numpy as np
import os
import datetime as dt




"""
python calculateGRP.py

Purpose: Calculate GRP from corrected brightness temperature data to detect Rain-on-snow event in the Arctic
Dolant at al., 2016
Sasseville et al., 2024


Revisions:
date     |               reason

"""
__author__ = "Josée-Anne Langlois"
__version__ = "01"
__maintainer__ = "Josée-Anne Langlois"
__email__ = "josee-anne.langlois@usherbrooke.ca"
__status__ = "Dvp"
__date__ = "6.2024"


if __name__ == '__main__':
    folder_project = 'D:/JALANGLOIS/'
    start_date = dt.datetime(2023, 1, 1)
    end_date = dt.datetime(2023, 1, 31)
    year = start_date.year
    hemisphere = 'N'
    select_region = 'aac'

    yeardoy_start = start_date.strftime('%Y%j')
    yeardoy_end = end_date.strftime('%Y%j')

    output_folder = os.path.join(folder_project, 'ROS_NC')
    #create output folder if it does not exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    file = os.path.join(folder_project, 'Measure', 'combined', str(year), 'corr_tb_%s_%s_%s.nc'%(str(yeardoy_start), str(yeardoy_end), select_region))
    #get filename from file path
    filename = os.path.basename(file)

    ds = xr.open_dataset(file)

    #calculate GRP from corrected brightness temperature and create a new variables

    grv3719 = (ds['TB_37V'] - ds['TB_19V']) / (ds['TB_37V'] + ds['TB_19V'])
    grh3719 = (ds['TB_37H'] - ds['TB_19H']) / (ds['TB_37H'] + ds['TB_19H'])

    grp = grv3719 / grh3719


    # Propagate error for TB_std_dev (example using simple error propagation)
    # This needs to be adapted based on the specific error propagation method you use
    std_dev_grp = grp * np.sqrt(
        (ds['TB_std_dev_37V'] / ds['TB_37V'])**2 +
        (ds['TB_std_dev_37H'] / ds['TB_37H'])**2 +
        (ds['TB_std_dev_19V'] / ds['TB_19V'])**2 +
        (ds['TB_std_dev_19H'] / ds['TB_19H'])**2
    )

    # add GRP and GRP_std_dev to the dataset as a new variable
    ds['GRP'] = grp
    ds['GRP_std_dev'] = std_dev_grp

    #write as netcdf
    ds.to_netcdf(os.path.join(output_folder, 'grp_%s_%s_%s.nc'%(str(yeardoy_start), str(yeardoy_end), select_region)))


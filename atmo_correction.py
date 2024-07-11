import os
import datetime as dt
import xarray as xr
from pyproj import CRS


"""
python atmo_correction.py

Purpose: apply atmospheric correction to brightness temperature data using precipitable water 


Revisions:
date     |               reason

"""
__author__ = "Josée-Anne Langlois, Vincent Sasseville"
__version__ = "01"
__maintainer__ = "Josée-Anne Langlois"
__email__ = "josee-anne.langlois@usherbrooke.ca"
__status__ = "Dvp"
__date__ = "6.2024"

def atm_tb_up(freq):
    '''This function provide the parameters to calculate the upwelling atmospheric brightness temperature for a given frequency
    Roy, A., 2014: Modélisation de l,émission micro-onde hivernale en foret boréale Canadienne. Ph.D. thesis, Université de 
    Sherbrooke, 242 pp., http://savoirs.usherbrooke.ca/handle/11143/70.
    See also Sasseville, et al., 2024'''
    if abs(freq - 11) <= 2 :
        return [0.10808, 7.2343]
    elif abs(freq - 19) <= 2:
        return [1.0291, 8.7212]
    elif abs(freq - 37) <= 2:
        return [0.62725, 25.04]
    elif abs(freq - 89) <= 2:
        return [2.3766, 47.37]


def atm_trans(freq):
    '''This function provide the parameters to calculate the atmospheric transmittance for a given frequency'''
    if abs(freq - 11) <= 2 :
        return [1.2204e-6, 0.97925]
    elif abs(freq - 19) <= 2:
        return[-0.0033509, 0.97666]
    elif abs(freq - 37) <= 2:
        return [-0.0017882, 0.91335]
    elif abs(freq - 89) <= 2:
        return [-0.0080878, 0.8178]
    


if __name__ == '__main__':
    
    #read precipitable water from NARR file (one nc file per year)
    folder_project = 'D:/JALANGLOIS/'
    pwat_folder = os.path.join(folder_project, 'pwat')
    tb_folder = os.path.join(folder_project, 'Measure','combined')
    output_folder = os.path.join(folder_project, 'Measure','combined')
    years = [2020]
    
    #create output folder if it does not exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    
    for year in years:
        pwat_file = os.path.join(pwat_folder, 'pr_wtr.%s.nc'%(str(year)))
        hemisphere = 'N'
        select_region = 'aac'
        

        # Define the CRS for NARR (Northern Lambert Conformal Conic)
        narr_crs = CRS.from_proj4 ('+proj=lcc +lat_0=50 +lon_0=-107 +lat_1=50 +lat_2=50 +x_0=5632642.22547 +y_0=4612545.65137 +datum=WGS84 +units=m +no_defs +type=crs')


        #Path to the file with brightness temperature that needs to be corrected
        tb_file = os.path.join(tb_folder, 'tb_%s_%s.nc'%(str(year), select_region))

        #open precipitable water in the atmosphere file from NARR
        # Load the datasets 
        print("opening file with precipitable water variable: ", pwat_file)
        pr_wtr_ds = xr.open_dataset(pwat_file)


        # load brightness temperature file
        print("opening file with brightness temperature data: ", tb_file)
        tb_ds = xr.open_dataset(tb_file)

        #assign projection to tb_ds
        tb_ds = tb_ds.rio.write_crs(CRS.from_epsg(6931))


        #drop lat lon coordinates to keep only x and y
        pr_wtr_ds = pr_wtr_ds.drop(['lat', 'lon'])


        # Assign CRS to pr_wtr and reproject to EPSG:6931
        pr_wtr_ds = pr_wtr_ds.rio.write_crs(narr_crs.to_string())


        print("reprojecting precipitable water data to EPSG:6931")
        pr_wtr_reprojected = pr_wtr_ds['pr_wtr'].rio.reproject('EPSG:6931')

        # Use the correct coordinates for spatial alignment with the file for Brightness Temperature
        pr_wtr_aligned = pr_wtr_reprojected.interp_like(tb_ds, method='nearest')

        # Resample pr_wtr to match TB's temporal resolution
        pr_wtr_resampled = pr_wtr_aligned.interp(time=tb_ds.time)

        #add precipitable water as a variable in the dataset of the Brightness temperature
        tb_ds['pr_wtr'] = pr_wtr_resampled.sel(time=tb_ds.time)
        
        #Calculate a new TB_corr variables with atmospheric correction using precipitable water

        #create a list of the variable names including TB, but without std_dev
        tb_vars = [var for var in tb_ds.data_vars if 'TB' in var and 'std_dev' not in var]

        for tb_var in tb_vars:
            #extract the frequency of the channel and remove H or V
            freq = tb_var.split('_')[1].replace('H','').replace('V','')

            
            #get the atmospheric correction parameters
            atm_tb_up_params = atm_tb_up(int(freq))
            atm_trans_params = atm_trans(int(freq))
            
            #calculate the atmospheric correction
            print("Calculating atmospheric correction for frequency %s"%(freq))
            atm_tb_up_ds = atm_tb_up_params[0] * tb_ds['pr_wtr'] + atm_tb_up_params[1]
            atm_trans_ds = atm_trans_params[0] * tb_ds['pr_wtr'] + atm_trans_params[1]

            #calculate the corrected TB and replace the original TB
            tb_ds[tb_var] = tb_ds[tb_var] - atm_tb_up_ds/atm_trans_ds

        #write as netcdf
        output_file = os.path.join(output_folder, 'corr_tb_%s_%s.nc'%(str(year), select_region))
        print("writing to file: ", output_file)
        tb_ds.to_netcdf(output_file)
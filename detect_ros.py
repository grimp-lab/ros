import os
import xarray as xr
import numpy as np


"""
python detect_ros.py

Purpose: Load snow cover data, calculate GRP from corrected brightness temperature data to detect Rain-on-snow event in the Arctic
Dolant at al., 2016
Sasseville et al., 2024


Revisions:
2024-11-14     |               add snow condition with weekly snow map for year before 1997

"""
__author__ = "Josée-Anne Langlois"
__version__ = "01"
__maintainer__ = "Josée-Anne Langlois"
__email__ = "josee-anne.langlois@usherbrooke.ca"
__status__ = "Dvp"
__date__ = "7.2024"

if __name__ == '__main__':
    #Parameters to be set by user

    start_year = 1995
    end_year = 1996
    years = range(start_year, end_year+1)
    region = 'aac'
    snowcon = True
    
    
    #path to folder where the corrected TB data is
    input_folder = 'E:/Measure/combined/%s'%region
    
    
    #path to folder where the snow cover data is
    snow_folder = 'E:/SNOW_COVER'

    output_folder = 'E:/ROS_NC'
    #create output folder if it does not exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for year in years:

        #open the file with the GRP
        file = os.path.join(input_folder, 'corr_tb_%s_%s.nc'%(str(year), region))
        print("opening file with corrected TB data: ", file)
        ds = xr.open_dataset(file)
    
        if snowcon:
            #open the file with the snow cover
            if year >=1997:
                if year > 2004:
                    snow_product = 'NOAA-IMS-4km'
                    file_snow = os.path.join(snow_folder, snow_product, 'combined','ims_%s_%s.nc'%(str(year),region))
                elif year >1997 and year <= 2004:
                    snow_product = 'NOAA-IMS-24km'
                    file_snow = os.path.join(snow_folder, snow_product, 'combined','ims_%s_%s.nc'%(str(year),region))
                elif year == 1997:
                    snow_product = 'NOAA-IMS-24km'
                    file_snow = os.path.join(snow_folder, snow_product, 'combined','ims_%s_%s_filled.nc'%(str(year),region))
                print("opening file with snow cover data: ", file_snow)
                ds_snow = xr.open_dataset(file_snow)

                #extract proj4 string from ds_snow (in variable projection)
                proj4 = ds_snow.projection.attrs['proj4']
                #set crs of ds_snow to proj4
                ds_snow.rio.write_crs(proj4, inplace=True)

                #reproject ds_snow to EPSG:6931
                print("reprojecting snow cover data to EPSG:6931")
                ds_snow_reprojected = ds_snow.rio.reproject('EPSG:6931')

                # Use the correct coordinates for spatial alignment with the file for GRP and Brightness Temperature
                ds_snow_aligned = ds_snow_reprojected.interp_like(ds, method='nearest')

                # Resample snow data to match TB's temporal resolution
                ds_snow_resampled = ds_snow_aligned.interp(time=ds.time)

                #add IMS_Surface_Values to ds
                ds['IMS_Surface_Values'] = ds_snow_resampled['IMS_Surface_Values'].sel(time=ds.time)

            elif year < 1997:
                snow_product = 'NOAA-G10035'
                file_snow = os.path.join(snow_folder, snow_product, 'G10035-rutgers-nh-24km-weekly-sce-v01r00-19800826-20231002.nc')
                ds_snow = xr.open_dataset(file_snow)
                #define proj
                proj4 = '+proj=stere +lat_0=90 +lat_ts=60 +lon_0=-80 +k_0=1 +x_0=0 +y_0=0 +a=6371200 +b=6371200 +units=km'
                #set crs of ds_snow to proj4
                ds_snow.rio.write_crs(proj4, inplace=True)

                #drop latitude and longitude variables
                ds_snow = ds_snow.drop(['latitude', 'longitude'])

                #reproject ds_snow to EPSG:6931
                print("reprojecting snow cover data to EPSG:6931")
                ds_snow_reprojected = ds_snow.rio.reproject('EPSG:6931')

                # Use the correct coordinates for spatial alignment with the file for GRP and Brightness Temperature
                ds_snow_aligned = ds_snow_reprojected.interp_like(ds, method='nearest')

                # Resample snow data to match TB's temporal resolution (Assign the values to all day in the week before the timestep (forward filling) (as specified in documentation of the dataset))
                ds_snow_resampled = ds_snow_aligned.reindex(time=ds.time, method="ffill")

                #add snow_cover_extent to ds
                ds['snow_cover_extent'] = ds_snow_resampled['snow_cover_extent'].sel(time=ds.time)
            
            

        # Calculate GRP first, then apply the mask
        grv3719 = (ds['TB_37V'] - ds['TB_19V']) / (ds['TB_37V'] + ds['TB_19V'])
        grh3719 = (ds['TB_37H'] - ds['TB_19H']) / (ds['TB_37H'] + ds['TB_19H'])
        grp = grv3719 / grh3719

        valid_mask = (
            (ds['TB_37V'] > 100) &
            (ds['TB_37H'] > 100) &
            (ds['TB_19V'] > 100) &
            (ds['TB_19H'] > 100)
        )
        grp = grp.where(valid_mask, drop=True)


        # Propagate error for TB_std_dev (using simple error propagation)
        std_dev_grp = grp * np.sqrt(
            (ds['TB_std_dev_37V'] / ds['TB_37V'])**2 +
            (ds['TB_std_dev_37H'] / ds['TB_37H'])**2 +
            (ds['TB_std_dev_19V'] / ds['TB_19V'])**2 +
            (ds['TB_std_dev_19H'] / ds['TB_19H'])**2
        )

        # add GRP and GRP_std_dev to the dataset as a new variable
        ds['GRP'] = grp
        ds['GRP_std_dev'] = std_dev_grp
        
        #Add a variable ROS to 1 if IMS_Surface_Values is 4 (meaning snow is on the ground) and GRP < -10 (Dolant et al., 2016, Sasseville et al., 2024)
        print("detecting Rain-on-Snow event")
        if snowcon:
            if year < 1997:
                print("detecting Rain-on-Snow event with snow condition")
                ds['ROS_10'] = xr.where((ds['snow_cover_extent'].isin([1])) & (ds['GRP'] < -10), 1, 0)
                ds['ROS_2'] = xr.where((ds['snow_cover_extent'].isin([1])) & (ds['GRP'] < -2), 1, 0)
                file_out = os.path.join(output_folder,'ros_%s_%s.nc'%(str(year), region))
                ds_towrite = ds[['ROS_10', 'ROS_2', 'GRP', 'GRP_std_dev', 'snow_cover_extent']]
            if year >=1997:
                print("detecting Rain-on-Snow event with snow condition")
                ds['ROS_10'] = xr.where((ds['IMS_Surface_Values'].isin([3,4,164,165,364,365])) & (ds['GRP'] < -10), 1, 0)
                ds['ROS_2'] = xr.where((ds['IMS_Surface_Values'].isin([3,4,164,165,364,365])) & (ds['GRP'] < -2), 1, 0)
                file_out = os.path.join(output_folder,'ros_%s_%s.nc'%(str(year), region))
                ds_towrite = ds[['ROS_10', 'ROS_2', 'GRP', 'GRP_std_dev', 'IMS_Surface_Values']]
           
        else:
            print("detecting Rain-on-Snow event without snow condition")
            ds['ROS_10'] = xr.where(ds['GRP'] < -10, 1, 0)
            ds['ROS_2'] = xr.where(ds['GRP'] < -2, 1, 0)
            file_out = os.path.join(output_folder,'ros_%s_%s_without_snowcon.nc'%(str(year), region))
            ds_towrite = ds[['ROS', 'GRP', 'GRP_std_dev']]
        
        #write to netcdf
        
        print("writing to file: ", file_out)
        ds_towrite.to_netcdf(file_out)
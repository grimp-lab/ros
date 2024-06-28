import xarray as xr
import pandas as pd
import geopandas as gpd
import os
from datetime import datetime, timedelta
from multiprocessing import Pool
import re
import numpy as np
import cftime
import rasterio.features
import rioxarray
from shapely.geometry import mapping
from pyproj import CRS
import rasterio
import warnings


"""
python build_netcdf_cetb.py

Purpose: Load brightness temperature from the CETB data set for a period of time, sensor, hemisphere, etc.


Revisions:
date     |               reason

"""
__author__ = "Josée-Anne Langlois"
__version__ = "01"
__maintainer__ = "Josée-Anne Langlois"
__email__ = "josee-anne.langlois@usherbrooke.ca"
__status__ = "Dvp"
__date__ = "6.2024"

def load_file(task):
    """Load a NetCDF file and return the dataset."""
    filepath = task['filepath']
    print(filepath)
    # #read the data using xarray
    grid3125 = xr.open_dataset(task['geo_file3125'], decode_times=False)

    
    grid3125 = grid3125.sel(x=slice(task['minx'], task['maxx']), y=slice(task['maxy'], task['miny']))



    try:
        # Suppress specific warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            warnings.simplefilter("ignore", category=UserWarning)
            ds = xr.load_dataset(filepath, decode_times=False)

        
        
        # Files contain two values for NAN (one for missing and one for fill_value), explicitly set nan to avoid error in writing netcdf files
        ds['TB'] = ds['TB'].where((ds['TB'] != 60000) & (ds['TB'] != 0), np.nan)
        ds['TB_std_dev'] = ds['TB_std_dev'].where((ds['TB_std_dev'] != 65535) & (ds['TB_std_dev'] != 65534), np.nan)
        ds['TB_time'] = ds['TB_time'].where(ds['TB_time'] >=0, np.nan)
        # Manually decode the time coordinate to be in a datetime format
        # Extract the time coordinate
        time_var = ds.coords['time']  # Change 'time' to the actual name of your time coordinate

        #Manually decode the time coordinate
        time_units = time_var.attrs['units']  # e.g., 'minutes since 2023-01-02 00:00:00'
        calendar = time_var.attrs.get('calendar', 'standard')  # Default to 'standard' if not specified

        # Convert numerical time values to cftime objects
        decoded_times = cftime.num2date(time_var.values, units=time_units, calendar=calendar)

        # Convert cftime objects to numpy datetime64 objects
        datetime_times = np.array([np.datetime64(dt.strftime('%Y-%m-%dT%H:%M:%S')) for dt in decoded_times])

        # Assign the decoded times back as the time coordinate
        # Suppress specific warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            ds = ds.assign_coords(time=datetime_times)

        #rename variables TB to TB_channel
        
        # add a new dimension to the dataset and assign a value from task 'orbit' key
        #ds = ds.expand_dims({'channel': [task['channel']]})
        ds = ds.expand_dims({'orbit': [task['orbit']]})
        ds = ds.sel(x=slice(task['minx'], task['maxx']), y=slice(task['maxy'], task['miny']))

        '''19 GHz data have a resolution of 6.25 so np.repeat is used to downscale the data to 3.125 
        (we are just repeating the tb values 4 times each in both axis to have the same grid of 37 
        Ghz tb at 3.125 resolution)'''
        ds = ds.interp_like(grid3125, method='nearest')

        #keep only crs, TB, TB_std_dev and TB_time variables
        ds = ds[['crs', 'TB', 'TB_std_dev']]
        #rename TB to TB_channel and TB_std_dev to TB_std_dev_channel and TB_time to TB_time_channel and TB_num_samples to TB_num_samples_channel
        ds = ds.rename({'TB': 'TB_%s'%task['channel'], 'TB_std_dev': 'TB_std_dev_%s'%task['channel']})
        
        return ds
    except FileNotFoundError:
         # If the new file also doesn't exist, print a message
        print("File not found:", filename)
        # You can choose to return None or any other value as needed
        pass
            

# Define the regular expression pattern for the filenames of cetb netcdf files as defined in the user guide
#https://doi.org/10.5067/MEASURES/CRYOSPHERE/NSIDC0630.001.
pattern = re.compile(
    r"NSIDC-0630-EASE2_"
    r"(?P<grid>[\w.]+km)-"
    r"(?P<platform_sensor>[\w_]+)-"
    r"(?P<date>\d{7})-"
    r"(?P<channel>\w+)-"
    r"(?P<orbit>\w+)-"
    r"(?P<algorithm>\w+)-"
    r"(?P<input>\w+)-"
    r"(?P<version>v[\d.]+)\.nc"
)
    

if __name__ == '__main__':
    #Parameters to be set by user
    folder_project = 'D:/JALANGLOIS/'
    platform = 'F18_SSMIS'
    hemisphere = 'N'
    select_region = 'aac'
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 31)
    channels = ['19H','19V','37V','37H', '91V', '91H']
    geo_file3125 = os.path.join(folder_project, 'Measure', 'tool','EASE2_%s3.125km.geolocation.v0.9.nc'%(hemisphere))
    #Define the path to the shapefile that defines the region of interest
    region_path = os.path.join(folder_project,'regions', select_region, '%s_moins_1500m.shp'%(select_region))  #"/mnt/f/Input/%s/%s.shp"%(select_region, select_region)
    
    #extract year and yeardoy (with 3digits) from start_date and end_date
    year = start_date.year
    yeardoy_start = start_date.strftime('%Y%j')
    yeardoy_end = end_date.strftime('%Y%j')
     
    #output_folder = os.path.join(folder_project, 'Measure', 'combined', select_region, str(year))
    output_folder = os.path.join(folder_project, 'Measure', 'combined', str(year))


    #define the path to the file that contains precipitable water in order to perform the atmospheric correction
    pwat_file = os.path.join(folder_project, 'pr_wtr.%s.nc'%(str(year)))

    #create directory if it does not exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # read the shapefile and reproject to EPSG:6931
    region = gpd.read_file(region_path)
    region = region.to_crs(6931)

    # Use the region shapefile to extract the Bounding Box of the data to keep
    area_gdf = gpd.read_file(region_path)
                
    # Reproject the GeoDataFrame to EPSG:6931
    gdf_6931 = area_gdf.to_crs(6931) 

    # Get the bounding box of the GeoDataFrame
    bbox = gdf_6931.total_bounds  # returns (minx, miny, maxx, maxy)
    minx, miny, maxx, maxy = bbox

    
    #create a list of the files in a directory
    measure_folder = os.path.join(folder_project,"Measure",platform, str(year))


    # Create a list of file paths for the NetCDF files
    file_paths = [os.path.join(measure_folder, fname) for fname in sorted(os.listdir(measure_folder)) if fname.endswith('.nc')]

    # Extract components from filenames
    extracted_info = []
    for filepath in file_paths:
        filename = os.path.basename(filepath)
        match = pattern.match(filename)
        if match:
            extracted_info.append(match.groupdict())
            #add file path as a key to the dictionary
            extracted_info[-1]['filepath'] = filepath

    # Convert to DataFrame for easy manipulation
    df = pd.DataFrame(extracted_info)
    df['geo_file3125'] = geo_file3125
    df['minx'] = minx
    df['maxx'] = maxx
    df['miny'] = miny
    df['maxy'] = maxy
   
    
    #filter the dataframe between yeardoy_start and yeardoy_end and for specific channels
    filtered_df = df[(df['date'].between(yeardoy_start, yeardoy_end)) & (df['channel'].isin(channels))]

    #print number of files to process (number of rows in the dataframe)
    #print(filtered_df)
    print('Nb of files to process : ',filtered_df.shape[0])

 
    # Convert DataFrame to a list of dictionaries
    tasks = filtered_df.to_dict(orient='records')        
 
 
    # Define the number of processes to use
    num_processes = 6  # You can adjust this based on your system's capabilities

    # Create a multiprocessing pool
    with Pool(num_processes) as pool:
        # Load and process data in parallel
        datasets = pool.map(load_file, tasks)

    #print(datasets)
    # Combine the datasets
    datasets = [ds for ds in datasets if ds is not None]
    #print(datasets)
    combined_ds = xr.combine_by_coords(datasets, combine_attrs='override')

    
    #Mask data outside the islands (from the shapefile of the region of interest, which is a buffer in of the islands of 1500m to remove coastal and big lakes)
    # # Create a mask from the polygons
    # mask = region.geometry.apply(mapping)   # Convert the GeoDataFrame to a format that rasterio understands

    # # Rasterize the mask
    # mask_array = rasterio.features.geometry_mask(mask, transform=combined_ds.rio.transform(), invert=True, out_shape=(combined_ds.dims['y'], combined_ds.dims['x']))
    
    # # Expand the mask to match the dimensions of the xarray dataset
    # mask_xr = xr.DataArray(mask_array, coords=[combined_ds.coords['y'], combined_ds.coords['x']], dims=['y', 'x'])
    
    # # Apply the mask to the xarray dataset
    # ds_masked = combined_ds.where(mask_xr, drop=True)
    
    # #write the data to a netcdf file
    # ds_masked.to_netcdf(os.path.join(output_folder, 'tb_%s_%s_%s_masked.nc'%(str(yeardoy_start), str(yeardoy_end), select_region)))
    combined_ds.to_netcdf(os.path.join(output_folder, 'tb_%s_%s_%s.nc'%(str(yeardoy_start), str(yeardoy_end), select_region)))
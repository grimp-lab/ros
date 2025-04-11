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
#import rioxarray
#from shapely.geometry import mapping
#from pyproj import CRS
import rasterio
import warnings
import time


"""
python build_netcdf_cetb.py

Purpose: Load brightness temperature from the CETB data set for a period of time, sensor, hemisphere, etc.


Revisions:
09-08-2024     |               Adapt to the structure of the CETB data downloaded for the previous years

"""
__author__ = "Josée-Anne Langlois"
__version__ = "01"
__maintainer__ = "Josée-Anne Langlois"
__email__ = "josee-anne.langlois@usherbrooke.ca"
__status__ = "Dvp"
__date__ = "6.2024"


def find_missing_channels(df, year):
    # Define the expected channels and orbits
    expected_channels = set(['19H', '19V', '37H', '37V'])
    expected_orbits = set(['M', 'E'])

    # Generate a list of all days in the year
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        total_days = 366
    else:
        total_days = 365
    days = list(range(1, total_days + 1))

    # Initialize a list to collect missing channel info
    missing_info = []

    # Extract the DOY from the YYYYDOY format
    df['DOY'] = df['date'].astype(str).str[-3:].astype(int)
    
    # Iterate over each day and orbit to check for missing channels
    for day in days:
        for orbit in expected_orbits:
            # Filter the dataframe for the specific day and orbit
            day_orbit_df = df[(df['DOY'] == day) & (df['orbit'] == orbit)]
            
            if day_orbit_df.empty:
                # If there's no data for this day and orbit, all channels are missing
                missing_channels = expected_channels
            else:
                # Get the available channels for the day and orbit
                available_channels = set(day_orbit_df['channel'])
                
                # Identify the missing channels
                missing_channels = expected_channels - available_channels
            
            # If there are missing channels, add the info to the list
            if missing_channels:
                missing_info.append({'day': day, 'orbit': orbit, 'missing_channels': list(missing_channels)})
    
    # Convert the list to a dataframe for better readability
    missing_df = pd.DataFrame(missing_info)
    
    return missing_df

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
            ds = xr.load_dataset(filepath,  engine='netcdf4', decode_times=False)

        
        
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

        '''19 GHz data have a resolution of 6.25 so interpolation is done to downscale the data to 3.125 '''
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
    hemisphere = 'N'
    region = 'tuk'


    start_year = 1987
    end_year = 2000
    years = range(start_year, end_year+1)
    
    channels_625 = ['19H','19V']
    channels_3125 = ['37V','37H']

    # Define the number of processes to use to parallel the processing of daily files
    num_processes = 6  # You can adjust this based on your system's capabilities


    #path to folder where the Measure directory is with daily netcdf TB data
    input_folder = 'D:/Measure'
    #paht to the folder where to find the grid file
    grid_folder = 'D:/Measure/tool'
    #path where the combined netcdf will be written
    output_base_folder = input_folder

    #Define the path to the shapefile that defines the region of interest
    region_path = os.path.join('D:/regions', region, '%s_moins_1500m.shp'%(region))  
        
           
    # get the path to the file with the grid information for the 3.125 km resolution (all data will be align to this grid)
    geo_file3125 = os.path.join(grid_folder,'EASE2_%s3.125km.geolocation.v0.9.nc'%(hemisphere))
        
    
    #folder where the combined netcdf file of TB aligned with 3.125 grid will be written
    output_folder = os.path.join(output_base_folder, 'combined', region)
    

    # Use the region shapefile to extract the Bounding Box of the data to keep
    area_gdf = gpd.read_file(region_path)

    # Reproject the GeoDataFrame to EPSG:6931
    gdf_6931 = area_gdf.to_crs(6931) 

    # Get the bounding box of the GeoDataFrame
    bbox = gdf_6931.total_bounds  # returns (minx, miny, maxx, maxy)
    minx, miny, maxx, maxy = bbox


    #create directory if it does not exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    start = time.time()

    for year in years:
        #extract year and yeardoy (with 3digits) from start_date and end_date
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        yeardoy_start = start_date.strftime('%Y%j')
        yeardoy_end = end_date.strftime('%Y%j')
        channels = channels_3125 + channels_625

        #Define the sensor for the year and if there are multiple sensors for the year define the break date
        multiplesensor = False
        if year <1991:
            sensor = 'F08'
        elif year == 1991:
            multiplesensor = True
            sensors = ['F08', 'F11']
            break_date = datetime(1991,8,31)
        elif year >1991 and year <1998:
            sensor = 'F11'
        elif year == 1998:
            multiplesensor = True
            sensors = ['F11', 'F13']
            break_date = datetime(1998,8,31)
        elif year >1998 and year <2008:
            sensor = 'F13'
        elif year == 2008:  
            multiplesensor = True
            sensors = ['F13', 'F17']
            break_date = datetime(2008,4,1)
        elif year >2008 and year <2016:
            sensor = 'F17'
        elif year >=2016:
            sensor = 'F18'
        else:
            print(f"Sensor not found for year {year}")

        if multiplesensor:
            files_list = []
            before_break = True
            yeardoy_break = break_date.strftime('%Y%j')
            df = pd.DataFrame()
            for sensor in sensors:
                
                for channel in channels:
                    measure_folder = os.path.join(input_folder, channel + '_' + sensor)
                    #print(measure_folder)
                    try:
                        #Create a list of file paths for the NetCDF files
                        files = [os.path.join(measure_folder, fname) for fname in sorted(os.listdir(measure_folder)) if fname.endswith('.nc')]


                        files_list.extend(files)
                    except FileNotFoundError:
                        print(f"Directory not found: {measure_folder}")
                    except PermissionError:
                        print(f"Permission denied: {measure_folder}")
                
                # Extract components from filenames
                extracted_info = []
                for filepath in files_list:
                    #print(filepath)
                    filename = os.path.basename(filepath)
                    #print(filename)
                    match = pattern.match(filename)
                    if match:
                        extracted_info.append(match.groupdict())
                        #add file path as a key to the dictionary
                        extracted_info[-1]['filepath'] = filepath

                # Convert to DataFrame for easy manipulation
                df_temp = pd.DataFrame(extracted_info)

                if before_break:
                    df_temp = df_temp[df_temp['date'].between(yeardoy_start,yeardoy_break)]
                    before_break = False
                else:
                    df_temp = df_temp[df_temp['date'].between(yeardoy_break,yeardoy_end)]

                #add df_temp content to df
                df = pd.concat([df, df_temp], ignore_index=True)
        else:
            if year < 2016:
                files_list = []
                for channel in channels:
                    measure_folder = os.path.join(input_folder, channel + '_' + sensor)
                    #print(measure_folder)
                    try:
                        #Create a list of file paths for the NetCDF files
                        files = [os.path.join(measure_folder, fname) for fname in sorted(os.listdir(measure_folder)) if fname.endswith('.nc')]


                        files_list.extend(files)
                    except FileNotFoundError:
                        print(f"Directory not found: {measure_folder}")
                    except PermissionError:
                        print(f"Permission denied: {measure_folder}")
                

            elif year >= 2016:
                #create a list of the files in a directory
                measure_folder = os.path.join(input_folder, str(year))
                # Create a list of file paths for the NetCDF files
                try:
                    files_list = [os.path.join(measure_folder, fname) for fname in sorted(os.listdir(measure_folder)) if fname.endswith('.nc')]
                except FileNotFoundError:
                    print(f"Directory not found: {measure_folder}")
                except PermissionError:
                    print(f"Permission denied: {measure_folder}")
            
            else:
                    print('Year not supported')
            
            # Extract components from filenames
            extracted_info = []
            for filepath in files_list:
                #print(filepath)
                filename = os.path.basename(filepath)
                #print(filename)
                match = pattern.match(filename)
                if match:
                    extracted_info.append(match.groupdict())
                    #add file path as a key to the dictionary
                    extracted_info[-1]['filepath'] = filepath

            # Convert to DataFrame for easy manipulation
            df = pd.DataFrame(extracted_info)

            #filter the dataframe between yeardoy_start and yeardoy_end
            df = df[df['date'].between(yeardoy_start,yeardoy_end)]
        
        
        #add the grid file path and the bounding box to the dataframe
        df['geo_file3125'] = geo_file3125
        df['minx'] = minx
        df['maxx'] = maxx
        df['miny'] = miny
        df['maxy'] = maxy


        
        # keep only 37V and 37H channels with 3.125 km resolution and  19V and 19H with 6.25 km resolution
        filtered_df_37 = df[(df['channel'].isin(channels_3125)) & (df['grid'].isin(['N3.125km']))]
        filtered_df_19 = df[(df['channel'].isin(channels_625)) & (df['grid'].isin(['N6.25km']))]
        
        filtered_df = pd.concat([filtered_df_37, filtered_df_19])
 
        # In some cases, there might be some data duplication, so we order the dataframe by date, orbit and channel and remove the duplicates
        # Sort by date, orbit, and input (descending)
        df_sorted = filtered_df.sort_values(by=['date', 'orbit', 'channel','input'], ascending=[True, True, True, True])

        # Drop duplicates based on date, orbit, and channel
        df_unique = df_sorted.drop_duplicates(subset=['date', 'orbit','channel'], keep='first')

        
        #print number of files to process (number of rows in the dataframe)
        print('Nb of files to process : ',df_unique.shape[0])

        #write info on files as csv file and save it in the input folder
        df_unique.to_csv(os.path.join(output_folder, 'list_of_files_%s_%s.csv'%(str(year), region)))
        
        # extract missing dates
        missing_channels = find_missing_channels(df_unique, year)

        #write as csv
        missing_channels.to_csv(os.path.join(output_folder, f'missing_channels_{year}_{region}.csv'), index=False)

        
    
        # Convert DataFrame to a list of dictionaries
        tasks = filtered_df.to_dict(orient='records')        
    
        
        # Create a multiprocessing pool
        with Pool(num_processes) as pool:
            # Load and process data in parallel
            datasets = pool.map(load_file, tasks)

        #print(datasets)
        # Combine the datasets
        datasets = [ds for ds in datasets if ds is not None]
        #print(datasets)
        combined_ds = xr.combine_by_coords(datasets, combine_attrs='override')

        
        # Write the combined dataset to a NetCDF file
        combined_ds.to_netcdf(os.path.join(output_folder, 'tb_%s_%s.nc'%(str(year), region)))
        
    end = time.time()
    print("from %s to %s "%(start_year, end_year))
    print("Temps total = " + str(round(end - start, 1)) + " sec")
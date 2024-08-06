import xarray as xr
import pandas as pd
import geopandas as gpd
import os
from datetime import datetime, timedelta
from multiprocessing import Pool
import re
import numpy as np
import rasterio
import time
import gzip
import shutil


"""
python build_netcdf_ims.py

Purpose: Unzip, read and combine daily snow cover data from NOAA IMS 4km resolution to create a single netcdf file for a specific year and region


Revisions:
date     |               reason

"""
__author__ = "Josée-Anne Langlois"
__version__ = "01"
__maintainer__ = "Josée-Anne Langlois"
__email__ = "josee-anne.langlois@usherbrooke.ca"
__status__ = "Dvp"
__date__ = "7.2024"


def decompress_gz(input_gz_path, output_nc_path):
    print("Decompressing %s " % (input_gz_path))
    with gzip.open(input_gz_path, 'rb') as f_in:
        with open(output_nc_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

            

# Regular expression pattern
pattern = re.compile(r"ims(?P<date>\d{7})_(?P<resolution>\d+km)_v(?P<version>\d+\.\d+)\.nc\.gz")

if __name__ == '__main__':
    #Parameters to be set by user
    resolution = '4km'
    region = 'aac'
    snow_product = 'NOAA-IMS-4km'
    start_year = 2004
    end_year = 2015
    years = range(start_year, end_year+1)

    for year in years:

        #path to folder where the Measure directory is with daily netcdf TB data
        input_folder = 'D:/JALANGLOIS/'

        #path where the combined netcdf will be written
        output_base_folder = 'D:/JALANGLOIS/'

        #create a list of the files in a directory
        snow_cover_folder = os.path.join(input_folder,"SNOW_COVER", snow_product ,str(year))
        
        # Create a list of file paths for the NetCDF files
        files_list = [os.path.join(snow_cover_folder, fname) for fname in sorted(os.listdir(snow_cover_folder)) if fname.endswith('.nc.gz')]
        
        #Define the path to the shapefile that defines the region of interest
        region_path = os.path.join(input_folder,'regions', region, '%s_moins_1500m.shp'%(region))  #"/mnt/f/Input/%s/%s.shp"%(select_region, select_region)


        #folder where the combined netcdf file of TB aligned with 3.125 grid will be written
        output_folder = os.path.join(output_base_folder, "SNOW_COVER", snow_product, 'combined')

        #create output folder if it does not exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Use the region shapefile to extract the Bounding Box of the data to keep
        area_gdf = gpd.read_file(region_path)

        ims_proj = '+proj=stere +lat_0=90 +lat_ts=60 +lon_0=-80 +k=1 +x_0=0 +y_0=0 +a=6378137 +b=6356257 +units=m +no_defs'
        
        # Reproject the GeoDataFrame to ims_proj
        area_gdf = area_gdf.to_crs(ims_proj)

        # Get the bounding box of the GeoDataFrame
        bbox = area_gdf.total_bounds  # returns (minx, miny, maxx, maxy)
        minx, miny, maxx, maxy = bbox


        #create directory if it does not exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

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
        df['minx'] = minx
        df['maxx'] = maxx
        df['miny'] = miny
        df['maxy'] = maxy
        #print(df)


        #print number of files to process (number of rows in the dataframe)
        #print(filtered_df)
        print('Nb of files to process : ',df.shape[0])
        start = time.time()
    
        # Convert DataFrame to a list of dictionaries
        tasks = df.to_dict(orient='records')    

        combined_ds = {}
        # unzip files
        for task in tasks:
            filepath = task['filepath']
            try:
                if os.path.exists(filepath[:-3]):
                    # If the new file already exists, print a message
                    print("File already exists: %s" % filepath[:-3])
                else:
                    decompress_gz(filepath, filepath[:-3])
                ds = xr.open_dataset(filepath[:-3])
                ds = ds.sel(x=slice(minx, maxx), y=slice(miny, maxy))

                #print(ds)
                #if this is the first file, create the dataset
                if combined_ds == {}:
                    combined_ds = ds
                else:
                    combined_ds = xr.combine_by_coords([combined_ds,ds], combine_attrs='override')
                    
            except FileNotFoundError:
                # If the new file also doesn't exist, print a message
                print("File not found:", filename)
                # You can choose to return None or any other value as needed
                pass
        

        #print(combined_ds)
        print("Writing combined snow cover data for the year %s netcdf file"%(str(year)))
        combined_ds.to_netcdf(os.path.join(output_folder, 'ims_%s_%s.nc'%(str(year), region)))
        
        end = time.time()
        print("Processing time for year %s = "%(str(year)) + str(round(end - start, 1)) + " sec")
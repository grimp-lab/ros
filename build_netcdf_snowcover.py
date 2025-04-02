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
from rasterio.crs import CRS
import rioxarray


"""
python build_netcdf_ims.py

Purpose: Unzip, read and combine daily snow cover data from NOAA IMS to create a single netcdf file for a specific year and region


Revisions:
8.2024     |               Adjust the code to be able to process both 4km and 24km resolution data

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

if __name__ == '__main__':
    #Parameters to be set by user
    region = 'aac'
    start_year = 2013
    end_year = 2023
    years = range(start_year, end_year+1)
    #path to folder where the snow cover data is
    input_folder = 'D:/JALANGLOIS'

    #path where the combined netcdf will be written
    output_base_folder = 'E:/'


    
    #Define the path to the shapefile that defines the region of interest
    region_path = os.path.join('E:/regions', region, '%s_bbox.shp'%(region))  #"/mnt/f/Input/%s/%s.shp"%(select_region, select_region)
    # Use the region shapefile to extract the Bounding Box of the data to keep
    area_gdf = gpd.read_file(region_path)

    


    for year in years:
        print(year)
        if year > 2004:
            resolution = '4km'
            snow_product = 'NOAA-IMS-%s'%(resolution)
            input_folder = 'D:/JALANGLOIS'
            pattern = re.compile(
                r"ims(?P<date>\d{7})_(?P<resolution>\d+km)_v(?P<version>\d+\.\d+)\.(?P<extension>\w+)(?:\.gz)?"
            )
            ims_proj = '+proj=stere +lat_0=90 +lat_ts=60 +lon_0=-80 +k=1 +x_0=0 +y_0=0 +a=6378137 +b=6356257 +units=m +no_defs'

            
        elif year >=1997 and year <= 2004:
            resolution = '24km'
            snow_product = 'NOAA-IMS-%s'%(resolution)
            input_folder = 'E:/'
            pattern = re.compile(
                r"ims(?P<date>\d{7})_00UTC_(?P<resolution>\d+km)_v(?P<version>\d+\.\d+)\.(?P<extension>\w+)(?:\.gz)?"
            )
            ims_proj ='+proj=stere +lat_0=90 +lon_0=-80 +lat_ts=60 +x_0=511.5 +y_0=511.5 +datum=WGS84 +units=m +no_defs'

        print(snow_product)
        #create a list of the files in a directory
        snow_cover_folder = os.path.join(input_folder,"SNOW_COVER", snow_product ,str(year))
        #print(os.listdir(snow_cover_folder))
        
        # Create a list of file paths for the NetCDF files
        files_list = [os.path.join(snow_cover_folder, fname) for fname in sorted(os.listdir(snow_cover_folder)) if fname.endswith('.gz')]
        
        #folder where the combined netcdf file of TB aligned with 3.125 grid will be written
        output_folder = os.path.join(output_base_folder, "SNOW_COVER", snow_product, 'combined')

        #create output folder if it does not exist
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
        
        # Reproject the GeoDataFrame to ims_proj
        area_gdf = area_gdf.to_crs(ims_proj)

        # # Get the bounding box of the GeoDataFrame
        # bbox = area_gdf.total_bounds  # returns (minx, miny, maxx, maxy)
        # minx, miny, maxx, maxy = bbox 
        
        # df['minx'] = minx
        # df['maxx'] = maxx
        # df['miny'] = miny
        # df['maxy'] = maxy
        


        #print number of files to process (number of rows in the dataframe)
        #print(filtered_df)
        print('Nb of files to process : ',df.shape[0])
        start = time.time()
    
        # Convert DataFrame to a list of dictionaries
        tasks = df.to_dict(orient='records')    
        #print(tasks)

        # Initialize an empty list to store the datasets
        datasets = []

        # unzip files
        for task in tasks:
            print(task)
            filepath = task['filepath']
            print(filepath)
            try:
                if os.path.exists(filepath[:-3]):
                    # If the new file already exists, print a message
                    print("File already exists: %s" % filepath[:-3])
                else:
                    decompress_gz(filepath, filepath[:-3])
                
                    
                #open the file
                if snow_product == 'NOAA-IMS-4km':
                    print("Opening file: ", filepath[:-3])
                    ds = xr.open_dataset(filepath[:-3])
                elif snow_product == 'NOAA-IMS-24km':
                    date = int(task['date'])
                    if date in [1997036, 1997037, 1997038, 1997139,1997156,1997159,1997162,1997164,1997165,1997167,1997168,1997170,1997172,1997173,1997174,1997177, 1997179,1997181,1997182,1997187,1997188,1997190,1997191,1997192,1997194,1997195,1997199,1997202,1997204,1997205,1997206,1997209,1997212,1997216,1997217,1997218,1997219,1997221,1997224,1997225,1997226,1997228,1997234,1997235]:
                        start_line = 31
                        split = False
                    elif date >= 1997240 and date < 1997252 or date in [1997253,1997254,1997270,1997271,1997272,1997280,1997283,1997284,1997285,1997288,1997291,1997293]:
                        start_line = 31
                        split = False
                    elif date > 1997038 and date < 1998023:
                        start_line = 23
                        split = True
                    elif date >= 1998023 and date < 1998146 or date>=1998147 and date < 1998150 or date>=1998152 and date < 1998159 or date>=1998160 and date < 1998255 or date>=1998160 and date < 1998255 or date==1998272 or date>=1998275 and date < 1998292:
                        start_line = 25
                        split = True
                    

                    else:
                        start_line = 31
                        split = False
                    # Initialize a list to store the data
                    data = []
                    print("Opening file: ", filepath[:-3])  
                    # Open the file for reading
                    with open(filepath[:-3], 'r') as f:
                        # Use enumerate to keep track of line numbers
                        
                            for i, line in enumerate(f, start=1):
                                #Start processing from line 31
                                if i >= start_line:

                                    if split:
                                        # Split the line based on any whitespace and convert each part to an integer
                                        data.extend([int(num) for num in line.split()])

                                    else:
                                        # Strip the end-line character and add each character to the data list
                                        data.extend([int(char) for char in line.strip()])
                                
                            
                    # Convert the list to a NumPy array and reshape it to 1024 x 1024
                    data_array = np.reshape(np.asarray(data), [1024, 1024])
                    date = pd.to_datetime(task['date'], format='%Y%j')
                    da = xr.DataArray(data_array, dims=["y", "x"],coords={"time": date})

                    # Define CRS using Proj4 string
                    crs = CRS.from_proj4(ims_proj)

                    # Assign projection and georeferencing information
                    ncols = 1024
                    nrows = 1024
                    xllcorner = -12126597.0
                    yllcorner = -12126840.0
                    cellsize = 23684.997
                    

                    # Calculate coordinates
                    x_coords = xllcorner + np.arange(ncols) * cellsize
                    y_coords = yllcorner + np.arange(nrows) * cellsize

                    # Assign coordinates and CRS to the DataArray
                    da = da.assign_coords(x=("x", x_coords), y=("y", y_coords))
                    da = da.rio.write_crs(crs.to_wkt(), inplace=True)  # Writing CRS to the DataArray

                    # Convert DataArray to Dataset if you want to add metadata or multiple variables
                    ds = da.to_dataset(name="IMS_Surface_Values")
                    # Add global attributes (optional)
                    ds.attrs = {
                        'title': 'IMS Snow Coverage',
                        'institution': 'NOAA',
                        'source': 'IMS 24km Data',
                        'history': 'Created by conversion script',
                        'references': 'https://www.ncdc.noaa.gov/ims/'
                    }
                print(ds)
                    
                 # Clip ros to the extent of gdf_6931
                ds = ds.rio.write_crs(ims_proj)
                ds = ds.rio.clip(area_gdf.geometry.apply(lambda x: x.buffer(0)), area_gdf.crs, drop=True)

                #ds = ds.sel(x=slice(minx, maxx), y=slice(miny, maxy))
                #print(ds)

                datasets.append(ds)
                
                


            except FileNotFoundError:
                # If the new file also doesn't exist, print a message
                print("File not found:", filename)
                # You can choose to return None or any other value as needed
                pass
        
        combined_ds = xr.concat(datasets, dim='time')

        # add projection.attrs['proj4'] to the dataset
        combined_ds['projection'] = xr.DataArray([ims_proj], attrs={'proj4': ims_proj})        
        #print(combined_ds)
        print("Writing combined snow cover data for the year %s netcdf file"%(str(year)))
        combined_ds.to_netcdf(os.path.join(output_folder, 'ims_%s_%s_bbox.nc'%(str(year), region)))
        
        end = time.time()
        print("Processing time for year %s = "%(str(year)) + str(round(end - start, 1)) + " sec")
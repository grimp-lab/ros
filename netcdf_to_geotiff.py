import os
import geopandas as gpd
import xarray as xr
import datetime as dt
import numpy as np
import pandas as pd
import cftime
import matplotlib.pyplot as plt
from shapely.geometry import box
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS

file = 'D:/JALANGLOIS/Measure/F18_SSMIS/2023/ds_2023.nc'
#file = 'D:/JALANGLOIS/Measure/F18_SSMIS/2023/NSIDC-0630-EASE2_N6.25km-F18_SSMIS-2023001-19V-E-SIR-CSU_ICDR-v1.5.nc'
ds = xr.open_dataset(file)
ds


# Select the data to write
#ds_towrite = ds.sel(channel='37V',time='2023-01-01',orbit='M')
ds_towrite = ds.sel(channel='19H',time=0,orbit='M')

# Extract the data to write
tb_data = ds_towrite['TB'].values

# Extract x and y coordinates
x = ds_towrite['x'].values
y = ds_towrite['y'].values
# Adjust origin to the center of the first pixel

# Calculate pixel size
pixel_size_x = np.abs(x[1] - x[0])
pixel_size_y = np.abs(y[1] - y[0])
print(pixel_size_x, pixel_size_y)
print(x[0], y[0])
print(x[-1], y[-1])


# Adjust origin to the center of the first pixel and ensure y-axis decreases downwards
transform = rasterio.transform.Affine.translation(x[0] - pixel_size_x / 2, y[0] + pixel_size_y / 2) * rasterio.transform.Affine.scale(pixel_size_x, -pixel_size_y)
crs = CRS.from_epsg(6931)



# Export to GeoTIFF
with rasterio.open(
    'TB_geotiff_19H.tif',
    'w',
    driver='GTiff',
    height=tb_data.shape[0],
    width=tb_data.shape[1],
    count=1,
    dtype=tb_data.dtype,
    crs=crs,
    transform=transform,
) as dst:
    dst.write(tb_data, 1)


import numpy as np
import os
import xarray as xr
from math import sin, cos, sqrt, atan2, radians


def get_closest_coord(lat, lon, latg, long):
    R = 6373.0

    lat1 = np.radians(lat)
    lon1 = np.radians(lon)
    lat2 = np.radians(latg)
    lon2 = np.radians(long)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance = R * c
    index = np.unravel_index(abs(distance).argmin(), distance.shape)
    return index

def add_coords_NARR(lat, lon, link_dict, infile, outfile):
    NARR_data_file=infile
    grid = xr.open_dataset(NARR_data_file)
    latg = grid.lat.values
    print(latg.shape)
    long = grid.lon.values
    y, x = get_closest_coord(lat, lon, latg, long)
    coord_string = "%s_%s"%(str(round(lon,4)), str(round(lat,4)))
    link_dict.update({coord_string:(x, y)})
    np.save(outfile, link_dict)
    return link_dict

def get_pwat(lat, lon, link_dict=None, data=None):
    coord_string = "%s_%s"%(str(round(lon,4)), str(round(lat,4)))
    # print(link_dict)
    x, y = link_dict.get(coord_string)
    pwat = data.isel(x=x, y=y).pr_wtr.values
    return pwat

def get_pwat2(data_set=None, date=None, lat=None, lon=None):
    pwat_file = os.path.join(data_folder, "pr_wtr.%s.nc"%str(date.year))
    #data = dataset.sel(time=date)
    error = (np.sqrt((data.lat.values-lat)**2 + (data.lon.values-lon)**2))
    index = np.unravel_index(abs(error).argmin(), error.shape)
    return data.isel(x=index[1], y=index[0]).pr_wtr.values



def get_closest_coord(lat, lon, latg, long):
    R = 6373.0

    lat1 = np.radians(lat)
    lon1 = np.radians(lon)
    lat2 = np.radians(latg)
    lon2 = np.radians(long)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance = R * c
    index = np.unravel_index(abs(distance).argmin(), distance.shape)
    return index
    # return latg[index[0], index[1]], long[index[0], index[1]]


def atm_tb_up(pwat, freq):
    if abs(freq - 11e9) <= 2e9 :
        return 0.10808*pwat + 7.2343
    elif abs(freq - 19e9) <= 2e9:
        return 1.0291*pwat + 8.7212
    elif abs(freq - 37e9) <= 2e9:
        return 0.62725*pwat + 25.04
    elif abs(freq - 89e9) <= 2e9:
        return 2.3766*pwat + 47.37


def atm_trans(pwat,freq):
    if abs(freq - 11e9) <= 2e9 :
        return 1.2204e-6*pwat + 0.97925
    elif abs(freq - 19e9) <= 2e9:
        return -0.0033509*pwat + 0.97666
    elif abs(freq - 37e9) <= 2e9:
        return -0.0017882*pwat + 0.91335
    elif abs(freq - 89e9) <= 2e9:
        return -0.0080878*pwat + 0.8178

def atm_tb_down(pwat, freq):
    if abs(freq - 11e9) <= 2e9 :
        return 0.097167*pwat + 4.0454
    elif abs(freq - 19e9) <= 2e9:
        return 0.97685*pwat + 5.189
    elif abs(freq - 37e9) <= 2e9:
        return 0.60846*pwat + 20.656
    elif abs(freq - 89e9) <= 2e9:
        return 2.4985*pwat + 42.762


def correct_tb(tb_mes, freq, pwat):
    return (tb_mes - atm_tb_up(pwat, freq))/atm_trans(pwat, freq)

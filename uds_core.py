"""
python uds_core.py

Run Uni. de Sherbrooke's rain on snow detection algorithm (Dolant et al.) and ice crust algorithm (Montpetit et al.)


Revisions:
date  2024-06   |          Process new Passive microwave data for 2018-2023, remove dependencies with OSSA code     Josée-Anne Langlois and Vincent Sasseville, Université de Sherbrooke

"""
__author__ = "Ludovic Brucker (NASA GSFC, code 615)"
__version__ = "01"
__maintainer__ = "Ludovic Brucker"
__email__ = "ludovic.brucker@nasa.gov"
__status__ = "Dvp"
__date__ = "2.2019"


import datetime as dt
import os
import socket
import sys

#import matplotlib
from matplotlib import pyplot as plt
import numpy as np
from scipy.io import netcdf


from utils_cetb import CETB
import atmo_correction as at
import time
import xarray as xr
import rasterio as rio
from shapely import geometry as geo

from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import box
from pyproj import CRS, Transformer

#matplotlib.use("TkAgg")


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + dt.timedelta(n)

def daterange_backwards(recent_date, older_date):
    for n in range(int((recent_date - older_date).days)):
        yield recent_date - dt.timedelta(n)


def select_sensor(date):
    transition1 = dt.datetime(1987, 7, 1)
    transition2 = dt.datetime(1991, 12, 16)
    transition3 = dt.datetime(1998, 9, 1)
    transition4 = dt.datetime(2008, 3, 30)
    transition5 = dt.datetime(2020, 1, 1)
    if date < transition1:
        platform_sensor = "NIMBUS7_smmr"
        sensor = 'smmr'
    elif date < transition2:
        platform_sensor = 'F08_SSMI'
        sensor = 'SSMI'
    elif date < transition3:
        platform_sensor = 'F11_SSMI'
        sensor = 'SSMI'
    elif date < transition4:
        platform_sensor = 'F13_SSMI'
        sensor = 'SSMI'
    else:
        platform_sensor = 'F17_SSMIS'
        sensor = 'SSMIS'
    return platform_sensor

# def daterange(start_time, end_time, time_delta):
#     timelist = []
#     time = start_time
#     while time < end_time:
#         timelist.append(time)
#         time = time+time_delta
#     return time_list

def uds_ros(v18, h18, v36, h36, grp_threshold = -10):
    '''
    Dolant's rain-on-snow event detection algorithm

    :param v18, h18, v36, h36: brightness temperatures
    :return ros: ros detected (1)
    :return grp: GRP (=grv3618/grh3618) used in the algorithm
    :return dh: delta_TB (=h36-h18) used in the algorithm
    '''
    # Algorithm threshold
    #grp_threshold = -10
    dh_threshold = 14.7

    # Caculate ratio
    grv3618 = np.divide(np.subtract(v36, v18), np.add(v36, v18))
    grh3618 = np.divide(np.subtract(h36, h18), np.add(h36, h18))
    #print("grv3618: " + str(grv3618))
    grp = np.divide(grv3618, grh3618)
    #grp[grp > 50] = 50
    #grp[grp < 50] = -50
    dh = np.subtract(h36, h18)

    # Initialize
    ros = np.zeros(grp.shape)

    # ROS
    ros[grp <= grp_threshold] = 1
    ros[np.isnan(grp)] = np.nan
    #ros[(grp > grp_threshold) & (dh >= dh_threshold)] = 1
    return ros, grp, dh


def transform_bbox(bbox_geom, src_crs, dst_crs):
    """Transforms the bounding box from src_crs to dst_crs."""
    src_crs = CRS.from_user_input(src_crs)
    dst_crs = CRS.from_user_input(dst_crs)
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    
    minx, miny, maxx, maxy = bbox_geom[0], bbox_geom[1], bbox_geom[2], bbox_geom[3]
    minx, miny = transformer.transform(minx, miny)
    maxx, maxy = transformer.transform(maxx, maxy)
    
    return minx, miny, maxx, maxy


dst_crs = 'EPSG:6931'


if __name__ == "__main__":
    # Inputs
    #select_region = sys.argv[1]
    #regions = ["Victoria", "Banks", "BIC", "Boothia", "Mackenzie", "Melville", "Axel_Ellesmere"]
    regions = ["Banks"]
    #Parameter to define if the atmospheric correction is applied or not (True or False)
    correct_tb = False
    #Parameter to define if the algorithm of the ROS detection (GRP from Dolant et al.) is run or not (True or False)
    run_algo = True
    
    run_SAT = False
 
    years = list(range(2023, 2024))
    start_month_day = [1, 1]
    end_month_day = [1, 2]
    #end_month_day = [6, 30] #This is considered the following year
    skip = True 
    version = 'v00'
    print("info:")
    #print(select_region)
    print("Correct tb = %s"%correct_tb)
    print("Years = ")
    print(years)
    print(start_month_day)
    print(end_month_day)
    print("skip = %s"%skip)

    # Paths adjust based on the name of the computer where the code is running
    if socket.gethostname().find('flsh-geoal16') >= 0:
        path_in = '/mnt/f/'
    elif socket.gethostname().find('flsh-geoal30') >= 0:
        path_in = 'D:/JALANGLOIS/'

        
    start = time.time()
    for region in regions:
        select_region = region
        print(region)
        for iyear in years:
            spatial_resolution = 3.125
            start_date = dt.datetime(iyear, start_month_day[0], start_month_day[1])
            end_date = dt.datetime(iyear, end_month_day[0], end_month_day[1])
            #end_date = dt.datetime(iyear+1, end_month_day[0], end_month_day[1])
            start_datep = start_date.strftime('%Y%m%d')
            end_datep = end_date.strftime('%Y%m%d')
            
            # Load coordinates and landcover mask
            cetb = CETB(None, start_date, path_in)

            x, y, lat, lon, landcover = CETB.grid(cetb, resolution=3.125, hemisphere='N')



            print("Region: %s, year=%s"%(select_region,str(iyear)))
            region_path = os.path.join(path_in,'regions', select_region, '%s_moins_1500m.shp'%(select_region))  #"/mnt/f/Input/%s/%s.shp"%(select_region, select_region)
            #region_path = os.path.join(path_in,'regions', select_region, '%s.shp'%(select_region))
            print(region_path)
            
            if region_path:
            
                # """Read the region in the shapefile provided as input"""
                gdf = gpd.read_file(region_path)
                

                # Reproject the GeoDataFrame to EPSG:6931
                gdf_6931 = gdf.to_crs(epsg=6931)   

                # Get the bounding box of the GeoDataFrame
                bbox = gdf_6931.total_bounds  # returns (minx, miny, maxx, maxy)
                #extract bbox to minx, miny, maxx, maxy
                minx, miny, maxx, maxy = bbox[0], bbox[1], bbox[2], bbox[3]
                


                # Extract the geometries
                geometries = gdf_6931.geometry
                
                # Combine geometries into a MultiPolygon
                multipolygon = geo.MultiPolygon([geom for geom in geometries if geom.geom_type == 'Polygon' or geom.geom_type == 'MultiPolygon'])

   

                indexx = np.where((x > minx) & (x < maxx))
                #print(indexx)
                indexy = np.where((y > miny) & (y < maxy))
                #print(indexy)
                rows = [min(indexy[0]), max(indexy[0])+1]
                cols = [min(indexx[0]), max(indexx[0])+1]
                landcover = landcover[rows[0]:rows[1], cols[0]:cols[1]]
                lat = lat[rows[0]:rows[1], cols[0]:cols[1]]
                lon = lon[rows[0]:rows[1], cols[0]:cols[1]]

                corner = (x[cols[0]], y[rows[0]])
                resx = np.abs(x[cols[0]] - x[cols[0]-1])
                resy = np.abs(y[rows[0]] - y[rows[0]-1])
                x = x[cols[0]:cols[1]]
                y = y[rows[0]:rows[1]]
                affine = rio.transform.from_origin(corner[0], corner[1], resx, resy)
                if isinstance(multipolygon, geo.Polygon):
                    multipolygon = geo.MultiPolygon([multipolygon])  # Ensure it's a MultiPolygon if it's a single Polygon

            
                mask = None
                for polygon in multipolygon.geoms:
                    area_mask = rio.features.geometry_mask([polygon], (len(y),len(x)), affine, invert=True)
                if mask is None:
                    mask = area_mask
                else:
                    mask &= area_mask
            


            algo_crust = True
        #     # Run UdS ice crust algorithm, daily
        #     # if algo_crust:
        #     #     # Calculate winter mean Polarization Ration at both 19 and 37 GHz
        #     #     if not os.path.isfile('pr_winter_' + platform_sensor + '_' + str(
        #     #             spatial_resolution) + 'km_winter_' + start_datep + '-' + end_datep + '.nc',
        #     #                           ):
        #     #         pr18_winter, pr36_winter = uds_dpr_winter(2015, platform_sensor, spatial_resolution)
        #     # quit()

        #     ##ps "NIMBUS7_smmr" date < dt.datetime(1987,7,1)
        #     ##ps ""

            # Run UdS ROS algorithm, daily
            for date in daterange(start_date, end_date):
                print("info:")
                print(select_region)
                print("Correct tb = %s"%correct_tb)
                print("Years = ")
                print(years)
                print(start_month_day)
                print(end_month_day)
                print("skip = %s"%skip)
                # try:
                datep = date.strftime('%Y-%m-%d')
                print(datep)
                platform_sensor = select_sensor(date)
                sensor = platform_sensor.split('_')[1]
                cetb.ch_platform_sensor(platform_sensor)
                print("platform_sensor = %s"%platform_sensor)


                #Setting up folders and skipping
                if correct_tb:
                    result_folder = "ROS_NC"
                else:
                    result_folder = "ROS_NC_no_correction"
                folder_region  = "%s/%s/"%(result_folder, select_region)
                if not os.path.exists(path_in + folder_region):
                    os.mkdir(path_in + folder_region)
                folder = folder_region + str(iyear)
                if not os.path.exists(path_in + folder):
                    os.mkdir(path_in + folder)
                output_file = path_in + folder + '/ros_uds_' + platform_sensor + '_Morning_EASE2_' + str(spatial_resolution) + 'km_' + datep + '_' + version + '.nc'
                if os.path.exists(output_file):
                    if skip == True:
                        print("%s skipped"%date.strftime("%d-%m-%Y"))
                        continue


                year = date.year
                print("Run UdS ROS - " + datep)
                print("Load CETB")

                if run_SAT:
                    ''''''
                    ndays = 5
                    list_channel=['19V', '19H', '37V', '37H', '89H']
                else:
                    ndays = 1
                cetb_5days = []
                try:
                    for idx, date2 in enumerate(daterange_backwards(date - dt.timedelta(days=0), date - dt.timedelta(days=ndays))):
                        print('Loading previous date: ', date2)
                        platform_sensor2 = select_sensor(date2)
                        cetb = CETB(platform_sensor2, date2)
                        CETB.load(cetb, list_channel=['19V', '19H', '37V', '37H', '89H'])
                        cetb.V19.tb = np.repeat(cetb.V19.tb, 2, axis=0)
                        cetb.V19.tb = np.repeat(cetb.V19.tb, 2, axis=1)
                        cetb.H19.tb = np.repeat(cetb.H19.tb, 2, axis=0)
                        cetb.H19.tb = np.repeat(cetb.H19.tb, 2, axis=1)
                        cetb_5days.append(cetb)
                except Exception as e:
                    print(str(e))
                    with open("log.txt", 'w') as log:
                        log.write("%s\n"%e)
                        continue
                #print(cetb_5days)

                cetb = cetb_5days[0]
                tb19v = cetb.V19.tb
                tb19h = cetb.H19.tb
                tb37v = cetb.V37.tb
                tb37h = cetb.H37.tb
                tb89h = cetb.H89.tb
                print(tb19v.max())

                

                maxclass = np.zeros(tb37h.shape)
                v18 = np.full((tb37h.shape[0], tb37h.shape[1], ndays), np.nan)
                h18 = np.full(v18.shape, np.nan)
                v36 = np.full(v18.shape, np.nan)
                h36 = np.full(v18.shape, np.nan)
                h89 = np.full(v18.shape, np.nan)

                # print("hey")
                # print(cetb_5days[0].V19.tb.shape)
                # print(v18.shape)

                for i in range(0, len(cetb_5days)):
                    v18[:, :, i] = cetb_5days[i].V19.tb
                    h18[:, :, i] = cetb_5days.__getitem__(i).H19.tb
                    v36[:, :, i] = cetb_5days.__getitem__(i).V37.tb
                    h36[:, :, i] = cetb_5days.__getitem__(i).H37.tb
                    h89[:, :, i] = cetb_5days.__getitem__(i).H89.tb


                tb19v = tb19v[rows[0]:rows[1], cols[0]:cols[1]]
                tb19h = tb19h[rows[0]:rows[1], cols[0]:cols[1]]
                tb37v = tb37v[rows[0]:rows[1], cols[0]:cols[1]]
                tb37h = tb37h[rows[0]:rows[1], cols[0]:cols[1]]
                v18 = v18[rows[0]:rows[1], cols[0]:cols[1],:]
                h18 = h18[rows[0]:rows[1], cols[0]:cols[1],:]
                v36 = v36[rows[0]:rows[1], cols[0]:cols[1],:]
                h36 = h36[rows[0]:rows[1], cols[0]:cols[1],:]
                h89 = h89[rows[0]:rows[1], cols[0]:cols[1],:]
                maxclass = maxclass[rows[0]:rows[1], cols[0]:cols[1]]
                for i in range(0, len(cetb_5days)):
                    v18[:, :, i] = np.where(area_mask, v18[:, :, i], np.nan)
                    h18[:, :, i] = np.where(area_mask, h18[:, :, i], np.nan)
                    v36[:, :, i] = np.where(area_mask, v36[:, :, i], np.nan)
                    h36[:, :, i] = np.where(area_mask, h36[:, :, i], np.nan)
                    h89[:, :, i] = np.where(area_mask, h89[:, :, i], np.nan)
                maxclass = np.where(area_mask, maxclass, np.nan)
                
                    # tb19v_raw = tb19v
                    # tb19h_raw = tb19h
                    # tb37v_raw = tb37v
                    # tb37h_raw = tb37h
                if correct_tb == True:
                    print("Correcting Tb")
                    pwat_file = path_in + "pwat/"+"pr_wtr.%s.nc"%str(date.year)
                    dataset = xr.open_dataset(pwat_file)
                    data = dataset.sel(time=date)
                    dict_file = path_in + "Measure/tool/ptr_dict_3.npy"
                    link_dict = np.load(dict_file, allow_pickle=True).ravel()[0]
                    count=0
                    print(len(lat.flatten()))
                    for i in range(len(lat.flatten())):
                        tlon,tlat = lon.flatten()[i], lat.flatten()[i]
                        if not "%s_%s"%(str(round(tlon,4)), str(round(tlat,4))) in link_dict.keys():
                            link_dict = at.add_coords_NARR(tlat, tlon, link_dict, pwat_file, dict_file)
                            count += 1
                            print("%s out of %s\n"%(str(count), str(len(lat.flatten()))))
                    vpwat=np.vectorize(at.get_pwat, excluded=["data"])
                    pwat_array=vpwat(lat=lat, lon=lon, link_dict=link_dict, data=data)
                    vfunc = np.vectorize(at.correct_tb)
                    for i in range(ndays):
                        freq = 19e9
                        v18[:,:,i] = vfunc(v18[:,:,i], freq, pwat=pwat_array)
                        h18[:,:,i] = vfunc(h18[:,:,i], freq, pwat=pwat_array)
                        freq = 37e9
                        h36[:,:,i] = vfunc(h36[:,:,i], freq, pwat=pwat_array)
                        v36[:,:,i] = vfunc(v36[:,:,i], freq, pwat=pwat_array)
                        freq = 89e9
                        #h89[:,:,i] = vfunc(h89[:,:,i], freq, pwat=pwat_array)

                tb19v = v18[:,:,0]
                tb19h = h18[:,:,0]
                tb37v = v36[:,:,0]
                tb37h = h36[:,:,0]
                tb89h = h89[:,:,0]
                print(tb19v.max())

                # ROS algorithm
                if run_algo:
                    print("Calculing ROS")
                    ros, grp, dh = uds_ros(tb19v, tb19h, tb37v, tb37h)
                    ros5 , grp, dh = uds_ros(tb19v, tb19h, tb37v, tb37h, grp_threshold=-5)
                    if run_SAT:
                        print("Calculing Ludo's ROS")
                        rosL, maxclass = rl.ros_algorithm(v18, h18, v36, h36, h89, None)
                        rosL = np.where(area_mask, rosL, np.nan)

                # save variable ros
                print("Saving in file for date %s"%datep)
                ncfile = netcdf.netcdf_file(output_file, 'w')
                ncfile.content = 'Rain-on-snow event detection based on Dolant et al. using passive microwave ' + sensor + 'observations on the ' + str(
                    spatial_resolution) + '-km EASE2 North grid'
                ncfile.author = 'Josee-Anne Langlois (GRIMP, UdeS)'
                ncfile.history = 'Version ' + version + '; Created on ' + \
                                dt.datetime.today().strftime('%Y-%m-%d')
                # ncfile.createDimension('r', np.shape(ros)[0])
                # ncfile.createDimension('c', np.shape(ros)[1])

                xdim = ncfile.createDimension('x', len(x))
                xdim = ncfile.createVariable('x', np.dtype('float32'), ('x',))
                xdim[:] = x
                ydim = ncfile.createDimension('y', len(y))
                ydim = ncfile.createVariable('y', np.dtype('float32'), ('y',))
                ydim[:] = y

                tmp = ncfile.createVariable('lat', np.dtype('float32').char, ('y', 'x'))
                tmp[:] = lat
                tmp = ncfile.createVariable('lon', np.dtype('float32').char, ('y', 'x'))
                tmp[:] = lon
                tmp = ncfile.createVariable('lc', np.dtype('float32').char, ('y', 'x'))
                tmp[:] = landcover

                tmp = ncfile.createVariable('tb19v', np.dtype('float32').char, ('y', 'x'))
                tmp[:] = tb19v
                tmp = ncfile.createVariable('tb19h', np.dtype('float32').char, ('y', 'x'))
                tmp[:] = tb19h
                tmp = ncfile.createVariable('tb37v', np.dtype('float32').char, ('y', 'x'))
                tmp[:] = tb37v
                tmp = ncfile.createVariable('tb37h', np.dtype('float32').char, ('y', 'x'))
                tmp[:] = tb37h
                tmp = ncfile.createVariable('tb89h', np.dtype('float32').char, ('y', 'x'))
                tmp[:] = tb89h

                if run_algo:
                    tmp = ncfile.createVariable('ros', np.dtype('float32').char, ('y', 'x'))
                    tmp[:] = ros
                    tmp = ncfile.createVariable('ros5', np.dtype('float32').char, ('y', 'x'))
                    tmp[:] = ros5
                    tmp = ncfile.createVariable('grp', np.dtype('float32').char,('y', 'x'))
                    tmp[:] = grp
                    tmp = ncfile.createVariable('dh', np.dtype('float32').char, ('y', 'x'))
                    tmp[:] = dh
                    if run_SAT:
                        tmp = ncfile.createVariable('ros_ludo', np.dtype('float32').char, ('y', 'x'))
                        tmp[:] = rosL

                ncfile.close()
                print(datep + " saved")

                # except Exception as e:
                #     with open(path_in + "log.txt", 'a') as log:
                #         log.write(date.strftime("%Y-%m-%d") + " failed\n")
                #         log.write(str(e) + '\n')
                #     print(str(e))
                #     continue

        end = time.time()
        print("region = %s"%select_region)
        print("Correct tb = %s"%correct_tb)
        print("Years = ")
        print(years)
        print(start_month_day)
        print(end_month_day)
        print("skip = %s"%skip)
        print("Temps total = " + str(round(end - start, 1)) + " sec")

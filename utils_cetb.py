"""
python utils_cetb.py

Load brightness temperature from the CETB data set for a given day, sensor, hemisphere, etc.
THIS HAS BEEN PUT TOGETHER QUICKLY TO GIVE AN IDEA OF WHAT IS EXPECTED


Revisions:
date     |               reason

"""
__author__ = "Ludovic Brucker (NASA GSFC, code 615)"
__version__ = "01"
__maintainer__ = "Ludovic Brucker"
__email__ = "ludovic.brucker@nasa.gov"
__status__ = "Dvp"
__date__ = "8.2018"

import os
import socket
import datetime as dt

import numpy as np
#from netCDF4 import Dataset, num2date
import xarray as xr


class CETB:
    """
    To load brightness temperature from the CETB data set,
    available at http://nsidc.org/data/nsidc-0630
    """

    def __init__(self, plateform_sensor, date, path_in, hemisphere='N'):
        '''
        Specify parameters to load brightness temperatures

        :param sensor: 'SMMR', 'SSM/I', 'SSMIS', or 'AMSR-E'
        :param date: yyyymmdd
        :param hemisphere: 'N' or 'S'
        '''

        self.platform_sensor = plateform_sensor
        self.hemisphere = hemisphere
        self.date = date
        self.path_in = path_in

        # # Paths
        # if socket.gethostname().find('flsh-geoal13') >= 0:
        #     self.path_in = '/mnt/e/Measure/'
        # elif socket.gethostname().find('flsh-geoal16') >= 0:
        #     self.path_in = '/mnt/f/'
        #     self.path_in2 = '/mnt/d/Brightness_temperature/'
        #     self.path_in3 = '/mnt/g/'
        #     path_out = '/mnt/f/result/'
        # elif socket.gethostname().find('flsh-geoal30') >= 0:
        #     self.path_in = 'D:/JALANGLOIS/'

        '''
            Sensor    Channel Frequency (GHz) and Polarization
            SMMR    6H, 6V, 10H, 10V, 18H, 18V, 21H, 21V, 37H, 37V
            SSM/I    19H, 19V, 22V, 37H, 37V, 85H, 85V
            SSMIS    19H, 19V, 22V, 37H, 37V, 91H, 91V
            AMSR-E    6H, 6V, 10.7H, 10.7V, 18H, 18V, 23H, 23V, 36H, 36V, 89H, 89V

            platform_sensor = ['NIMBUS7_SMMR', 'F08_SSMI', 'F10_SSMI', 'F11_SSMI', 'F13_SSMI', 'F14_SSMI', 'F15_SSMI',
                               'AQUA_AMSR-E', 'F16_SSMIS', 'F17_SSMIS', 'F18_SSMIS', 'F19_SSMIS']
            channel = [] # sensor dependent
            grid = ['N', 'S', 'T']
            resolution = [25, 12.5, 6.25, 3.125]
            algorithm = ['SIR', 'GRD']
            swath_source = ['CSU', 'RSS']
        '''

        '''
            Temporal Coverage by Sensor
            Sensor	Platform	Begin Coverage	End Coverage *
            AMSR-E	AQUA	01 June 2002	04 October 2011

            SSM/I   F08 07 September 1987   31 December 1991
            SSM/I   F10 08 December 1990    14 November 1997
            SSM/I   F11 03 December 1991    16 May 2000
            SSM/I   F13 03 May 1995         19 November 2009
            SSM/I   F14 07 May 1997         23 August 2008
            SSM/I   F15 23 February 2000    30 June 2017

            SSMIS	F16 01 November 2005    30 June 2017
            SSMIS	F17 01 March 2008       30 June 2017
            SSMIS	F18 08 March 2010       30 June 2017
            SSMIS	F19 27 November 2014    09 February 2016

            SMMR	Nimbus	25 October 1978	20 August 1987
        '''

        if self.platform_sensor == 'F15_SSMI':
            self.sensor = 'SSMI'
            self.platform = 'F15'
        elif self.platform_sensor == 'F17_SSMIS':
            self.sensor = 'SSMIS'
            self.platform = 'F17'
        elif self.platform_sensor == 'F13_SSMI':
            self.sensor = 'SSMI'
            self.platform = 'F13'
        elif self.platform_sensor == 'F11_SSMI':
            self.sensor = 'SSMI'
            self.platform = 'F11'
        elif self.platform_sensor == 'F08_SSMI':
            self.sensor = 'SSMI'
            self.platform = 'F08'
        elif self.platform_sensor == "NIMBUS7_smmr":
            self.sensor = 'smmr'
            self.platform = 'NIMBUS7'

        # Convert date (yyyymmdd) to yyyyDOY
        self.year = date.strftime("%Y")[0:4]
        self.doy = '%03d' % date.timetuple().tm_yday
        print("CETB Initialized")


    def ch_platform_sensor(self, platform_sensor):
        self.platform_sensor = platform_sensor
        if self.platform_sensor == 'F15_SSMI':
            self.sensor = 'SSMI'
            self.platform = 'F15'
        elif self.platform_sensor == 'F17_SSMIS':
            self.sensor = 'SSMIS'
            self.platform = 'F17'
        elif self.platform_sensor == 'F13_SSMI':
            self.sensor = 'SSMI'
            self.platform = 'F13'
        elif self.platform_sensor == 'F11_SSMI':
            self.sensor = 'SSMI'
            self.platform = 'F11'
        elif self.platform_sensor == 'F08_SSMI':
            self.sensor = 'SSMI'
            self.platform = 'F08'
        elif self.platform_sensor == "NIMBUS7_smmr":
            self.sensor = 'smmr'
            self.platform = 'NIMBUS7'

    def load(self, list_channel='all', orbit=None, interpolation_method='SIR'):
        '''
        Load CETB brightness temperature

        Likely, this should always load both orbits (M: Morning & E: Evening),
        and contain a new field with the daily average: (M+E)/2

        :param channel: e.g. ['19V', '19H']
        :param orbit: 'M', 'E', or 'all'
        :param interpolation_method: 'SIR' by default
        :return:
        '''
        print("loading %s"%self.platform_sensor)
        if self.platform_sensor == "NIMBUS7_smmr":
            for channel in list_channel:
                resolution = '3.125'
                channel3 = '37' + channel[-1]
                if channel[0:2] == '19':
                    resolution = '6.25'
                    channel3 = '18' + channel[-1]
                if channel[0:2] == '89':
                    channel3 = '85' + channel[-1]

                channel2 = channel[-1] + channel[0:2]
                channel2 = TBclass(channel2)

                if channel3 != "85H":
                    for orbit in ['M', 'E']:
                        filename = self.path_in3 + "Measure/" + "smmr_%s/"%channel3 + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                                   self.platform_sensor + '-' + self.year + self.doy + '-' + channel3 + '-' + \
                                   orbit + '-' + interpolation_method + '-JPL-v1.3.nc'
                        print("opening " + filename)
                        ncfile = Dataset(filename, "r", format="NETCDF4")
                        print(filename)

                        setattr(channel2, 'tb' + '_' + orbit, np.squeeze(ncfile.variables['TB'][:]))

                        self.x = np.squeeze(ncfile['x'][:])
                        self.y = np.squeeze(ncfile['y'][:])
                        ncfile.close()
                else:
                    for orbit in ['M', 'E']:
                        setattr(channel2, 'tb' + '_' + orbit, np.nan)
                if channel == '19V':
                    setattr(self, 'V19', channel2)
                elif channel == '19H':
                    setattr(self, 'H19', channel2)
                elif channel == '37V':
                    setattr(self, 'V37', channel2)
                elif channel == '37H':
                    setattr(self, 'H37', channel2)
                elif channel == '85V':
                    setattr(self, 'V85', channel2)
                elif channel == '89H':
                    setattr(self, 'H89', channel2)

                setattr(channel2, 'tb', np.nanmean([channel2.tb_M, channel2.tb_E], axis=0))


        elif self.platform_sensor == 'F08_SSMI':
            if self.sensor == 'SSMI':
                interpolation_method = 'SIR'
                # create dictionnary w/ channels and corresponding resolution
                #list_channel = channel
                for channel in list_channel:
                    resolution = '3.125'
                    if channel[0:2] == '19':
                        resolution = '6.25'
                    if channel == "89H":
                        channel3 = "85H"
                        channel4 = "H89"
                    else:
                        channel3 = channel

                    channel2 = channel[-1] + channel[0:2]
                    channel2 = TBclass(channel2)

                    # self.channel2 = TBclass(channel2)
                    # setattr(self, channel2, TBclass2())

                    for orbit in ['M', 'E']:
                        filename = self.path_in3 + "Measure/" + "F08_%s/"%channel3 + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                                   self.platform_sensor + '-' + self.year + self.doy + '-' + channel3 + '-' + \
                                   orbit + '-' + interpolation_method + '-CSU-v1.3.nc'
                        filename2 = self.path_in2 + "Measure/" + "%s_F08/"%channel3 + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                                  self.platform_sensor + '-' + self.year + self.doy + '-' + channel3 + '-' + \
                                  orbit + '-' + interpolation_method + '-CSU-v1.3.nc'
                        try:
                            ncfile = Dataset(filename, "r", format="NETCDF4")
                            print(filename)
                        except:
                            ncfile = Dataset(filename2, "r", format="NETCDF4")
                            print(filename2)

                        # data variables, w/ dimension (time=1, rows, cols):
                        # crs, TB, TB_num_samples, Incidence_angle, TB_std_dev, TB_time
                        # crs means coordinate reference system
                        setattr(channel2, 'tb' + '_' + orbit, np.squeeze(ncfile.variables['TB'][:]))
                        # setattr(channel2, 'std', np.squeeze(
                        #         ncfile.variables['TB_std_dev'][:]))
                        # setattr(channel2, 'ftp', np.squeeze(
                        #         ncfile.variables['TB_num_samples'][:]))

                        # filename = self.path_in + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                        #            self.platform_sensor + '-' + self.year + self.doy + \
                        #            '-' + channel + '-M-' + interpolation_method + '-CSU-v1.3.nc'
                        # print(filename)
                        # ncfile = Dataset(filename, "r", format="NETCDF4")
                        # yo = np.squeeze(ncfile.variables['TB_std_dev'][:])
                        # setattr(channel2, 'stdstd', np.abs(yo - channel2.std))



                        if channel == '19V':
                            setattr(self, 'V19', channel2)
                        elif channel == '19H':
                            setattr(self, 'H19', channel2)
                        elif channel == '37V':
                            setattr(self, 'V37', channel2)
                        elif channel == '37H':
                            setattr(self, 'H37', channel2)
                        elif channel == '85V':
                            setattr(self, 'V85', channel2)
                        elif channel == '89H':
                            setattr(self, 'H89', channel2)



                        # d = ncfile.variables['time']
                        # date = d[:]  # days since 1972-01-01
                        # print d
                        # print date
                        # greg_date = num2date(
                        #    date[:], units=d.units, calendar=d.calendar)
                        # print(greg_date)
                        # print greg_date[0].strftime("%Y-%m-%d")
                        # print greg_date[0].strftime("%b %d %Y")
                        self.x = np.squeeze(ncfile['x'][:])
                        self.y = np.squeeze(ncfile['y'][:])
                        ncfile.close()

                    # Replace empty cell by nan
                    # channel2.tb_M[channel2.tb_M==[]] = np.nan
                    # channel2.tb_E[channel2.tb_E==[]] = np.nan

                    # Average of Morning & Evening orbits
                    setattr(channel2, 'tb', np.nanmean([channel2.tb_M, channel2.tb_E], axis=0))


        elif self.platform_sensor == 'F13_SSMI':
            if self.sensor == 'SSMI':
                interpolation_method = 'SIR'
                # create dictionnary w/ channels and corresponding resolution
                #list_channel = channel
                for channel in list_channel:
                    resolution = '3.125'
                    if channel[0:2] == '19':
                        resolution = '6.25'


                    channel2 = channel[-1] + channel[0:2]
                    channel2 = TBclass(channel2)
                    channel3 = channel
                    if channel == "89H":
                        channel3 = "85H"

                    # self.channel2 = TBclass(channel2)
                    # setattr(self, channel2, TBclass2())

                    for orbit in ['M', 'E']:
                        filename = self.path_in + "Measure/" + "%s_F13/"%channel3 + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                                   self.platform_sensor + '-' + self.year + self.doy + '-' + channel3 + '-' + \
                                   orbit + '-' + interpolation_method + '-CSU-v1.3.nc'
                        filename2 = self.path_in3 + "Measure/" + "%s_F13/"%channel3 + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                                  self.platform_sensor + '-' + self.year + self.doy + '-' + channel3 + '-' + \
                                  orbit + '-' + interpolation_method + '-CSU-v1.3.nc'
                        try:
                            ncfile = Dataset(filename, "r", format="NETCDF4")
                            print(filename)
                        except:
                            ncfile = Dataset(filename2, "r", format="NETCDF4")
                            print(filename2)

                        # data variables, w/ dimension (time=1, rows, cols):
                        # crs, TB, TB_num_samples, Incidence_angle, TB_std_dev, TB_time
                        # crs means coordinate reference system
                        setattr(channel2, 'tb' + '_' + orbit, np.squeeze(ncfile.variables['TB'][:]))
                        # setattr(channel2, 'std', np.squeeze(
                        #         ncfile.variables['TB_std_dev'][:]))
                        # setattr(channel2, 'ftp', np.squeeze(
                        #         ncfile.variables['TB_num_samples'][:]))

                        # filename = self.path_in + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                        #            self.platform_sensor + '-' + self.year + self.doy + \
                        #            '-' + channel + '-M-' + interpolation_method + '-CSU-v1.3.nc'
                        # print(filename)
                        # ncfile = Dataset(filename, "r", format="NETCDF4")
                        # yo = np.squeeze(ncfile.variables['TB_std_dev'][:])
                        # setattr(channel2, 'stdstd', np.abs(yo - channel2.std))



                        if channel == '19V':
                            setattr(self, 'V19', channel2)
                        elif channel == '19H':
                            setattr(self, 'H19', channel2)
                        elif channel == '37V':
                            setattr(self, 'V37', channel2)
                        elif channel == '37H':
                            setattr(self, 'H37', channel2)
                        elif channel == '85V':
                            setattr(self, 'V89', channel2)
                        elif channel == '89H':
                            setattr(self, 'H89', channel2)



                        # d = ncfile.variables['time']
                        # date = d[:]  # days since 1972-01-01
                        # print d
                        # print date
                        # greg_date = num2date(
                        #    date[:], units=d.units, calendar=d.calendar)
                        # print(greg_date)
                        # print greg_date[0].strftime("%Y-%m-%d")
                        # print greg_date[0].strftime("%b %d %Y")
                        self.x = np.squeeze(ncfile['x'][:])
                        self.y = np.squeeze(ncfile['y'][:])
                        ncfile.close()

                    # Replace empty cell by nan
                    # channel2.tb_M[channel2.tb_M==[]] = np.nan
                    # channel2.tb_E[channel2.tb_E==[]] = np.nan

                    # Average of Morning & Evening orbits
                    setattr(channel2, 'tb', np.nanmean([channel2.tb_M, channel2.tb_E], axis=0))


        elif self.platform_sensor == 'F11_SSMI':
            if self.sensor == 'SSMI':
                interpolation_method = 'SIR'
                # create dictionnary w/ channels and corresponding resolution
                #list_channel = channel
                for channel in list_channel:
                    resolution = '3.125'
                    if channel[0:2] == '19':
                        resolution = '6.25'

                    if channel[0:2] == '89':
                        channel3 = '85' + channel[-1]
                    else:
                        channel3 = channel
                    channel2 = channel[-1] + channel[0:2]
                    channel2 = TBclass(channel2)

                    # self.channel2 = TBclass(channel2)
                    # setattr(self, channel2, TBclass2())

                    for orbit in ['M', 'E']:
                        filename = self.path_in + "Measure/" + "%s_F11/"%channel + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                                   self.platform_sensor + '-' + self.year + self.doy + '-' + channel3 + '-' + \
                                   orbit + '-' + interpolation_method + '-CSU-v1.3.nc'
                        filename2 = self.path_in2 + "Measure/" + "%s_F11/"%channel + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                                  self.platform_sensor + '-' + self.year + self.doy + '-' + channel3 + '-' + \
                                  orbit + '-' + interpolation_method + '-CSU-v1.3.nc'
                        try:
                            ncfile = Dataset(filename, "r", format="NETCDF4")
                            print(filename)
                        except:
                            ncfile = Dataset(filename2, "r", format="NETCDF4")
                            print(filename2)

                        # data variables, w/ dimension (time=1, rows, cols):
                        # crs, TB, TB_num_samples, Incidence_angle, TB_std_dev, TB_time
                        # crs means coordinate reference system
                        setattr(channel2, 'tb' + '_' + orbit, np.squeeze(ncfile.variables['TB'][:]))
                        # setattr(channel2, 'std', np.squeeze(
                        #         ncfile.variables['TB_std_dev'][:]))
                        # setattr(channel2, 'ftp', np.squeeze(
                        #         ncfile.variables['TB_num_samples'][:]))

                        # filename = self.path_in + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                        #            self.platform_sensor + '-' + self.year + self.doy + \
                        #            '-' + channel + '-M-' + interpolation_method + '-CSU-v1.3.nc'
                        # print(filename)
                        # ncfile = Dataset(filename, "r", format="NETCDF4")
                        # yo = np.squeeze(ncfile.variables['TB_std_dev'][:])
                        # setattr(channel2, 'stdstd', np.abs(yo - channel2.std))



                        if channel == '19V':
                            setattr(self, 'V19', channel2)
                        elif channel == '19H':
                            setattr(self, 'H19', channel2)
                        elif channel == '37V':
                            setattr(self, 'V37', channel2)
                        elif channel == '37H':
                            setattr(self, 'H37', channel2)
                        elif channel == '85V':
                            setattr(self, 'V85', channel2)
                        elif channel == '89H':
                            setattr(self, 'H89', channel2)



                        # d = ncfile.variables['time']
                        # date = d[:]  # days since 1972-01-01
                        # print d
                        # print date
                        # greg_date = num2date(
                        #    date[:], units=d.units, calendar=d.calendar)
                        # print(greg_date)
                        # print greg_date[0].strftime("%Y-%m-%d")
                        # print greg_date[0].strftime("%b %d %Y")
                        self.x = np.squeeze(ncfile['x'][:])
                        self.y = np.squeeze(ncfile['y'][:])
                        ncfile.close()

                    # Replace empty cell by nan
                    # channel2.tb_M[channel2.tb_M==[]] = np.nan
                    # channel2.tb_E[channel2.tb_E==[]] = np.nan

                    # Average of Morning & Evening orbits
                    setattr(channel2, 'tb', np.nanmean([channel2.tb_M, channel2.tb_E], axis=0))

        elif self.platform_sensor == 'F17_SSMIS':
            if self.sensor == 'SSMIS':
                if self.date > dt.datetime(2017, 6, 29):
                    version = "v1.4"
                    if self.date > dt.datetime(2019, 12, 31):
                        version = "v1.5"
                else:
                    version = "v1.3"
                # create dictionnary w/ channels and corresponding resolution
                #list_channel = channel
                for channel in list_channel:
                    channel3 = channel
                    channel4 = channel
                    resolution = '3.125'
                    if channel[0:2] == '19':
                        resolution = '6.25'

                    channel2 = channel[-1] + channel[0:2]
                    channel2 = TBclass(channel2)

                    # self.channel2 = TBclass(channel2)
                    # setattr(self, channel2, TBclass2())
                    if channel == "89H":
                        channel3 = "91H"
                        channel4 = "91H"
                    if channel == "37V" and self.date > dt.datetime(2016, 7, 31):
                        plats = "F17_SSMIS"
                        version = "v1.3"
                        if self.date > dt.datetime(2016, 6, 30):
                            version = "v1.4"
                            if self.date > dt.datetime(2019, 12, 31):
                                version = "v1.5"
                                if self.date > dt.datetime(2021, 5, 10):
                                    csu = "CSU_ICDR"
                    else:
                        plats = "F17_SSMIS"
                        if self.date > dt.datetime(2017, 6, 30):
                            version = "v1.4"
                        if self.date >= dt.datetime(2020, 1, 1):
                            version = "v1.5"
                            if self.date > dt.datetime(2021, 5, 10):
                                csu = "CSU_ICDR"
                    for orbit in ['M', 'E']:
                        print('loading file')
                        filename = self.path_in + "Measure/" + "%s/"%channel3 + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                                   plats + '-' + self.year + self.doy + '-' + channel4 + '-' + \
                                   orbit + '-' + interpolation_method + '-%s-%s.nc'%(csu, version)


                        #ncfile = Dataset(filename, "r", format="NETCDF4")
                        #print(filename)
                        #print ncfile size in x and y
                        #print(np.squeeze(ncfile.variables['TB'][:]).shape)


                        # data variables, w/ dimension (time=1, rows, cols):
                        # crs, TB, TB_num_samples, Incidence_angle, TB_std_dev, TB_time
                        # crs means coordinate reference system
                        #setattr(channel2, 'tb' + '_' + orbit, np.squeeze(ncfile.variables['TB'][:]))
                        # setattr(channel2, 'std', np.squeeze(
                        #         ncfile.variables['TB_std_dev'][:]))
                        # setattr(channel2, 'ftp', np.squeeze(
                        #         ncfile.variables['TB_num_samples'][:]))

                        # filename = self.path_in + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
                        #            self.platform_sensor + '-' + self.year + self.doy + \
                        #            '-' + channel + '-M-' + interpolation_method + '-CSU-v1.3.nc'
                        # print(filename)
                        # ncfile = Dataset(filename, "r", format="NETCDF4")
                        # yo = np.squeeze(ncfile.variables['TB_std_dev'][:])
                        # setattr(channel2, 'stdstd', np.abs(yo - channel2.std))

                        # Open the NetCDF file using xarray
                        ds = xr.open_dataset(filename, decode_times=False)

                        # Print the filename (optional)
                        print(filename)

                        # Access and set the 'TB' variable, squeezing it to remove single-dimensional entries
                        setattr(channel2, 'tb' + '_' + orbit, ds['TB'].squeeze().values)



                        if channel == '19V':
                            setattr(self, 'V19', channel2)
                        elif channel == '19H':
                            setattr(self, 'H19', channel2)
                        elif channel == '37V':
                            setattr(self, 'V37', channel2)
                        elif channel == '37H':
                            setattr(self, 'H37', channel2)
                        elif channel == '89V':
                            setattr(self, 'V89', channel2)
                        elif channel == '89H':
                            setattr(self, 'H89', channel2)


                        # Access and set the 'x' and 'y' variables, squeezing them as well
                        self.x = ds['x'].squeeze().values
                        self.y = ds['y'].squeeze().values

                        # Close the dataset (not strictly necessary with xarray, but good practice)
                        ds.close()



                        # d = ncfile.variables['time']
                        # date = d[:]  # days since 1972-01-01
                        # print d
                        # print date
                        # greg_date = num2date(
                        #    date[:], units=d.units, calendar=d.calendar)
                        # print(greg_date)
                        # print greg_date[0].strftime("%Y-%m-%d")
                        # print greg_date[0].strftime("%b %d %Y")
                        # self.x = np.squeeze(ncfile['x'][:])
                        # self.y = np.squeeze(ncfile['y'][:])
                        # ncfile.close()

                    # Replace empty cell by nan
                    # channel2.tb_M[channel2.tb_M==[]] = np.nan
                    # channel2.tb_E[channel2.tb_E==[]] = np.nan

                    # Average of Morning & Evening orbits
                    setattr(channel2, 'tb', np.nanmean([channel2.tb_M, channel2.tb_E], axis=0))


        # if channel == 'all':
        #     if self.sensor == 'SSMI':
        #         list_channel = ['19V', '19H', '37V',
        #                         '37H', '85V', '85H']  # '22V'
        #         # create dictionnary w/ channels and corresponding resolution
        #         for channel in list_channel:
        #             resolution = '3.125'
        #             if channel[0:2] == '19':
        #                 resolution = '6.25'
        #
        #             channel2 = channel[-1] + channel[0:2]
        #             if orbit == 'all':
        #                 # Need to loop on the two files _M_ and _E_
        #                 print('todo')
        #             else:
        #                 filename = self.path_in + self.satellite + '_CSU_N_' + self.year + self.doy + \
        #                            '/EASE2_' + self.hemisphere + str(resolution) + 'km.' + \
        #                            self.satellite + '_' + self.sensor + '.' + self.year + self.doy + \
        #                            '.' + channel + '.' + orbit + '.' + interpolation_method + '.CSU.v0.1.nc'
        #
        #             print(filename)
        #             ncfile = Dataset(filename, "r", format="NETCDF4")
        #
        #             # data variables, w/ dimension (time=1, rows, cols):
        #             # crs, TB, TB_num_samples, Incidence_angle, TB_std_dev, TB_time
        #             # crs means coordinate reference system
        #             setattr(self, channel2 + '.tb',
        #                     np.squeeze(ncfile.variables['TB'][:]))
        #             setattr(self, channel2 + '.ftp',
        #                     np.squeeze(ncfile.variables['TB_num_samples'][:]))
        #             setattr(self, channel2 + '.std',
        #                     np.squeeze(ncfile.variables['TB_std_dev'][:]))
        #
        #             d = ncfile.variables['time']
        #             date = d[:]  # days since 1972-01-01
        #
        #             greg_date = num2date(
        #                 date[:], units=d.units, calendar=d.calendar)
        #
        #             print(greg_date,
        #                   greg_date[0].strftime("%Y-%m-%d"),
        #                   greg_date[0].strftime("%b %d %Y"))
        #             ncfile.close()
        #     elif self.sensor == 'AMSRE':
        #         list_channel = ['06V', '06H', '10V', '10H',
        #                         '19V', '19H', '36V', '36H', '89', '89H']
        #         for channel in list_channel:
        #             # resolution is actually channel dependent,
        #             # there is need for a dictionnary w/ channels and resolutions
        #             filename = self.path_in + self.satellite + \
        #                        '_CSU_N_' + self.year + self.doy + '/EASE2_' + self.hemisphere + resolution + 'km.' + self.satellite + \
        #                        '_' + self.sensor + '.' + self.year + self.doy + '.' + channel + \
        #                        '.E.' + interpolation_method + '.CSU.v0.1.nc'
        #             ncfile = Dataset(filename, "r", format="NETCDF4")
        #             self.channel.tb = np.squeeze(ncfile.variables['TB'][:])
        #             self.channel.ftp = np.squeeze(
        #                 ncfile.variables['TB_num_samples'][:])
        #             self.channel.std = np.squeeze(
        #                 ncfile.variables['TB_std_dev'][:])
        #             ncfile.close()
        # else:
        #     if self.sensor == 'SSMI':
        #         # create dictionnary w/ channels and corresponding resolution
        #         list_channel = channel
        #         for channel in list_channel:
        #             resolution = '3.125'
        #             if channel[0:2] == '19':
        #                 resolution = '6.25'
        #
        #             channel2 = channel[-1] + channel[0:2]
        #             channel2 = TBclass(channel2)
        #
        #             # self.channel2 = TBclass(channel2)
        #             # setattr(self, channel2, TBclass2())
        #
        #             for orbit in ['M', 'E']:
        #                 filename = self.path_in + "Measure" + "%s/"%channel + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
        #                            self.platform_sensor + '-' + self.year + self.doy + '-' + channel + '-' + \
        #                            orbit + '-' + interpolation_method + '-CSU-v1.3.nc'
        #                 filename2 = self.path_in2 + "Measure" + "%s/"%channel + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
        #                           self.platform_sensor + '-' + self.year + self.doy + '-' + channel + '-' + \
        #                           orbit + '-' + interpolation_method + '-CSU-v1.3.nc'
        #                 try:
        #                     ncfile = Dataset(filename, "r", format="NETCDF4")
        #                     print(filename)
        #                 except:
        #                     ncfile = Dataset(filename2, "r", format="NETCDF4")
        #                     print(filename2)
        #
        #
        #                 # data variables, w/ dimension (time=1, rows, cols):
        #                 # crs, TB, TB_num_samples, Incidence_angle, TB_std_dev, TB_time
        #                 # crs means coordinate reference system
        #                 setattr(channel2, 'tb' + '_' + orbit, np.squeeze(ncfile.variables['TB'][:]))
        #                 # setattr(channel2, 'std', np.squeeze(
        #                 #         ncfile.variables['TB_std_dev'][:]))
        #                 # setattr(channel2, 'ftp', np.squeeze(
        #                 #         ncfile.variables['TB_num_samples'][:]))
        #
        #                 # filename = self.path_in + 'NSIDC-0630-EASE2_' + self.hemisphere + resolution + 'km-' + \
        #                 #            self.platform_sensor + '-' + self.year + self.doy + \
        #                 #            '-' + channel + '-M-' + interpolation_method + '-CSU-v1.3.nc'
        #                 # print(filename)
        #                 # ncfile = Dataset(filename, "r", format="NETCDF4")
        #                 # yo = np.squeeze(ncfile.variables['TB_std_dev'][:])
        #                 # setattr(channel2, 'stdstd', np.abs(yo - channel2.std))
        #
        #                 if channel == '19V':
        #                     setattr(self, 'V19', channel2)
        #                 elif channel == '19H':
        #                     setattr(self, 'H19', channel2)
        #                 elif channel == '37V':
        #                     setattr(self, 'V37', channel2)
        #                 elif channel == '37H':
        #                     setattr(self, 'H37', channel2)
        #                 elif channel == '85V':
        #                     setattr(self, 'V85', channel2)
        #                 elif channel == '85H':
        #                     setattr(self, 'H85', channel2)
        #
        #                 # d = ncfile.variables['time']
        #                 # date = d[:]  # days since 1972-01-01
        #                 # print d
        #                 # print date
        #                 # greg_date = num2date(
        #                 #    date[:], units=d.units, calendar=d.calendar)
        #                 # print(greg_date)
        #                 # print greg_date[0].strftime("%Y-%m-%d")
        #                 # print greg_date[0].strftime("%b %d %Y")
        #                 ncfile.close()
        #
        #             # Replace empty cell by nan
        #             # channel2.tb_M[channel2.tb_M==[]] = np.nan
        #             # channel2.tb_E[channel2.tb_E==[]] = np.nan
        #
        #             # Average of Morning & Evening orbits
        #             setattr(channel2, 'tb', np.nanmean([channel2.tb_M, channel2.tb_E], axis=0))

    # print crs.long_name
    # N3grid = Ease2Transform(crs.long_name)
    # (row, col) = N3grid.geographic_to_grid(40., -105.)
    # print row, col
    # (irow, icol) = (int(round(row)), int(round(col)))
    # print irow, icol
    # print "TB at (40.0N, 105.0W) is: %f K" % data[irow, icol]
    # print "Num samples used: %d" % num[irow, icol]
    # print N3grid.grid_to_geographic(row, col)

    def grid(self, resolution=6.25, hemisphere='N'):
        '''
        Load EASE2 grid coordinates and land cover type for the given spatial resolution

        :param resolution: e.g. 25, 12.5, 6.25, 3.125
        :param hemisphere: 'N' or 'S'
        :return: lat, lon, landcover
        '''

        # # Paths
        # print(socket.gethostname())
        # if socket.gethostname().find('gs615-montblanc') >= 0:
        #     # path Ludo
        #     self.path_in = os.getenv('HOME') + '/PMESDR/GeolocationTools/'
        # elif socket.gethostname().find('gs615-oibserve') >= 0:
        #     # path server
        #     self.path_in = os.getenv('HOME') + '/PMESDR/GeolocationTools/'
        # elif socket.gethostname().find('discover') >= 0:
        #     # path Jayanthi
        #     self.path_in = '/gpfsm/dnb32/jsrikish/ROS/Grid/EASE2/'
        # elif socket.gethostname().find('flsh-geoal13') >= 0:
        #     self.path_in = '/mnt/e/'

        # Load coordinates
        filename = self.path_in + 'Measure/tool/EASE2_' + hemisphere.upper() + str(resolution) + 'km.geolocation.v0.9.nc'
        # Open the NetCDF file using xarray
        ds = xr.open_dataset(filename, decode_times=False)
        #ncfile = Dataset(self.path_in + "Measure/tool/" + filename, "r", format="NETCDF4")
        x = np.squeeze(ds['x'][:])
        y = np.squeeze(ds['y'][:])
        lat = np.asarray(ds.variables['latitude'])
        lon = np.asarray(ds.variables['longitude'])


        return(x, y, lat, lon)


class TBclass(object):
    def __init__(self, channel):
        if channel == 'V19':
            self.V19 = None


class TBclass2(object):
    def __init__(self):
        self.tb = None
        self.nfp = None
        self.std = None

# if 'AQUA_AMSRE' == sensor:
#     startYear = 2002
#     stopYear = 2011
#     channels = ['18H', '18V', '36H', '36V']
# elif 'F08_SSMI' == sensor:
#     startYear = 1987
#     stopYear = 1991
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F10_SSMI' == sensor:
#     startYear = 1990
#     stopYear = 1997
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F11_SSMI' == sensor:
#     startYear = 1991
#     stopYear = 2000
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F13_SSMI' == sensor:
#     startYear = 1995
#     stopYear = 2009
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F14_SSMI' == sensor:
#     startYear = 1997
#     stopYear = 2008
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F15_SSMI' == sensor:
#     startYear = 2000
#     stopYear = 2016
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F16_SSMIS' == sensor:
#     startYear = 2005
#     stopYear = 2016
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F17_SSMIS' == sensor:
#     startYear = 2008
#     stopYear = 2016
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F18_SSMIS' == sensor:
#     startYear = 2010
#     stopYear = 2016
#     channels = ['19H', '19V', '37H', '37V']
# elif 'F19_SSMIS' == sensor:
#     startYear = 2014
#     stopYear = 2016
#     channels = ['19H', '19V', '37H', '37V']
# elif 'NIMBUS7_SMMR' == sensor:
#     startYear = 1978
#     stopYear = 1987
#     channels = ['18H', '18V', '37H', '37V']
# else:
#     raise ValueError

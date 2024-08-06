# preprocess_ros
Python code to process passive microwave data brightess temperature (CETB) (MEASURE database, (Brodzik et al., 2016)) into daily filtered and corrected data and calculate GRP for ros detection (Dolant et al., 2016, Sasseville et al., 2024)


# Optimized code 
Developed by Josée-Anne Langlois

Objective : manage Brightess temperature (TB), apply atmospheric correction and calculate GRP

## nsidc-data-download.py
This code is used to download daily netcdf file of the Brightness temperature from MEasure dataset NSIDC (Brodzik et al., 2016).  The file must be copied to the directory where you want to download data. You need to update the file with the parameters for the download (keyword search for the file, ex name of the sensor and algorithm used) and the start and end date.
You need to execute the file from the command line
>>> cd /path/to/your/directory
>>> python nsidc-data-download.py

You need to provide a username and password for an earthdata account (NASA website) in the command line when executing the python file.

## build_netcdf_cetb.py

Main python code to be used to read Brightness temperature daily files from Measure NSIDC database and create netcdf of file for a user defined period of time for the frequencies set by the user in the code.

This code also resample the 19ghz data that are originaly at 6.25 km resolution to 3.125 resolution in order to align with data at 37 ghz.

This code also creates a csv with the list of input files combined in the netcdf.
It also creates a csv file with the days and orbit for which we do not have 4 TBs required for the ROS algorithm (19V, 19H, 37V, 37H)

## atmo_correction.py

This code apply atmospheric correction to brightness temperature (TB) data using precipitable water and create a new netcdf file with corrected TB values. Parameters are derived from Roy et al., 2012 as done in Sasseville et al., 2024 and Dolant et al., 2018.
Create a new netcdf file with corrected TB. 
The name of the variables to be corrected in the input file must be TB_[freq][pol] ex : TB_19H.

## download_snowcover.py

For the year 2004 to now, daily snow cover extent is available at a resolution of 4km (name of product is NOAA-IMS-4km). This code is used to download a year of daily data in a local repository.


## build_netcdf_snowcover.py

This code is used to unzip and combined daily snow cover data in a single netcdf file for the year specified as a parameter in the code. 
The data is filtered spatially based on the region of interest shapefile that is provided as input parameter (region_path).

## detect_ros.py

This code add snow cover data to the file with corrected TB data for a specific year and region. 

It also calculates GRP from corrected brightness temperature data to detect Rain-on-snow event in the Arctic (Dolant at al., 2016, Sasseville et al., 2024)

It creates a new variables ROS that has the value 1 if there is snow on the ground and if GRP is below -10. 

A new netcdf file is created will all the variables (corrected TB, GRP, ROS, Snowcover, etc.)
   
## ros_analyses.ipynb
This notebook can be used to analyse the ros data for a specific year. It can mask the data to keep only the data on islands and generate monthly maps and statistics for ROS events.
    
# References
    Brodzik, M.J. et al. (2016) ‘MEaSUREs Calibrated Enhanced-Resolution Passive Microwave Daily EASE-Grid 2.0 Brightness Temperature ESDR, Version 1’. Boulder, Colorado USA: NASA National Snow and Ice Data Center Distributed Active Archive Center.

    Dolant, C. et al. (2016) ‘Development of a rain-on-snow detection algorithm using passive microwave radiometry’, Hydrological Processes, 30(18), pp. 3184–3196. Available at: https://doi.org/10.1002/hyp.10828.

    Sasseville, V. et al. (2024) ‘Patterns and Trend Analysis of Rain-on-Snow Events using Passive Microwave Satellite Data over the Canadian Arctic Archipelago Since 1987’, Journal of Hydrometeorology, 25(2), pp. 311–324. Available at: https://doi.org/10.1175/JHM-D-22-0218.1.





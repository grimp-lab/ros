# preprocess_ros
Python code to process passive microwave data brightess temperature (CETB) (MEASURE database, (Brodzik et al., 2016)) into daily filtered and corrected data and calculate GRP for ros detection (Dolant et al., 2016, Sasseville et al., 2024))


# Optimized code 
Developed by Josée-Anne Langlois

Objective : manage Brightess temperature (TB), apply atmospheric correction and calculate GRP

## nsidc-data-download.py
This code is use to download daily netcdf file of the Brightness temperature from MEasure dataset NSIDC (Brodzik et al., 2016).  The file must be copied to the directory where you want to download data. You need to update the file with the parameters for the download (keyword search for the file, ex name of the sensor and algorithm used) and the start and end date.
You need to execute the file from the command line
>>> cd /path/to/your/directory
>>> python nsidc-data-download.py

You need to provide a username and password for an earthdata account (NASA website) in the command line when executing the python file.

## build_netcdf_cetb.py

Main python code to be used to read Brightness temperature daily files from Measure NSIDC database and create netcdf of file for a user defined period of time for the frequencies set by the user in the code.

This code also resample the 19ghz data that are originaly at 6.25 km resolution to 3.125 resolution in order to align with data at 37 ghz.

## atmo_correction.py

This cod apply atmospheric correction to brightness temperature (TB) data using precipitable water and create a new netcdf file with corrected TB values.

## calculateGRP.py
Calculate GRP from corrected brightness temperature data to detect Rain-on-snow event in the Arctic (Dolant at al., 2016, Sasseville et al., 2024)

Create a new netcdf file with the input data (corrected TB values) and GRP as a new variables.


# Old version of code 
developped by Vincent Sasseville and Ludovick Brucker

## detect_ros.py
Main python code to be used to read Brightness temperature downloaded from the MEasure database and.
The code will apply the atmospheric correction (atmo_correction.py) if parameter correct_tb is set to True and then calculate the GRP ratio to detect ROS event (Dolant et al., 2016). Daily TB values, grp, lat lon and ROS detection index are exported as a dataframe in csv file per year.

Input parameters are defined in the main part of the code and need to be adjust by the user before running the script
To execute the code, open the cmd in windows and navigate to the folder where your python code is. Then execute the command below to run the code. Make sure to adjust input parameters before running the script (path_in, regions, start_date and end_date, etc.)
>>> python detect_ros.py


In order to work properly, the netcdf file from the MEasure database needs first to be dowloaded localy. The code nsidc-data-download.py can be use to download the data before using this code.
    
    
## utils_cetb.py
This code was developped by Ludovic Brucker and adapted by Vincent Sasseville and is used in the detect_ros.py to extract brightness temperature from the netcdf files of the Measures database (Brodzik et al. 2016). Based on the dates, the code is rebuilding the names of the files that contains information on the sensor, the methods of interpolation, the resolution, etc. 
    

    
    
    
    
# References
    Brodzik, M.J. et al. (2016) ‘MEaSUREs Calibrated Enhanced-Resolution Passive Microwave Daily EASE-Grid 2.0 Brightness Temperature ESDR, Version 1’. Boulder, Colorado USA: NASA National Snow and Ice Data Center Distributed Active Archive Center.

    Dolant, C. et al. (2016) ‘Development of a rain-on-snow detection algorithm using passive microwave radiometry’, Hydrological Processes, 30(18), pp. 3184–3196. Available at: https://doi.org/10.1002/hyp.10828.

    Sasseville, V. et al. (2024) ‘Patterns and Trend Analysis of Rain-on-Snow Events using Passive Microwave Satellite Data over the Canadian Arctic Archipelago Since 1987’, Journal of Hydrometeorology, 25(2), pp. 311–324. Available at: https://doi.org/10.1175/JHM-D-22-0218.1.





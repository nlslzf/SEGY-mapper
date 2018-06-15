# -*- coding: utf-8 -*-
"""
MIT License

Copyright (c) 2018 sarah-murray

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

##############################################################################

Scan for SEG-Y data. Read files and map in a user-defined coordinate system.

Scan specified folder for files with a .sgy or .segy extension. Identify if 
spatial data is available for CDP, source, or receiver/group and if the data 
is for a 2D or 3D survey. Read coordinates and convert to a set coordinate 
system. Plot new coordinates to a map as lines (2D) and polygons (3D) in a 
.png image. Provide text file to relate map to files within the directory, and
provide information about the survey geometry.

Args:
    survey (str) -- Name of output files.
    set_directory (str) -- File location to scan for SEG-Y data.
    data_projection (str) -- Define coordinate system of data as an EPSG code.
    required_projection (str) -- Define the required coordinate system as an 
        EPSG code.
    resolution (int) -- Define number of traces to skip when plotting 2D data.

Returns:
    .png (file) -- Map image of reprojected SEG-Y files.
    .txt (file) -- Associate int values in .png with file names. Provide data
        on file geometry.
"""

# Utilises SEGPY 2.0: https://github.com/sixty-north/segpy
# Utilises Pyproj: https://pypi.org/project/pyproj
from segpy.reader import create_reader
import glob, os
import matplotlib.pyplot as plt
import pyproj
from datetime import datetime

"""
##########################    REQUIRED USER INPUT    ##########################
"""

#set a name for output files
survey = " YOUR SURVEY NAME"

#set data directory
#ALL DATA IN THIS DIRECTORY MUST BE IN THE SAME COORDINATE SYSTEM
#i.e. r" YOUR DIRECTORY HERE "
directory = r" YOUR DIRECTORY "

#User to define spatial reference code from spatialreference.org
#Input projection
data_projection = "EPSG: SPATIAL REFERENCE OF YOUR DATA "
#Output projection
#Eg ESPG:4326 = WGS84
required_projection = "EPSG:4326"

"""
###############################################################################
"""
#Start "timer"
start = datetime.now()

#Change working directory
os.chdir(directory)
# Find and create list of .sgy/.segy files within all subdirectories
filenames = glob.glob("**/*.s*gy", recursive = True)

#Create text file for legend
legend = open(str(survey)+'_legend.txt', 'w')
legend.write(str(survey)+", "+str(data_projection)+" to "+ 
             str(required_projection)+"\n \n")


#Create figure
fig = plt.figure(figsize = (7, 7))
ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])

# Add numeric label to each line/polygon and associate with filename
filenumber = 1
lats = []
lons = []
dimension = []
for file in filenames:
    # Read binary
    files = open(file, "rb") 
    # Read SEG-Y
    reader = create_reader(files)

    # Total number of traces
    num_traces = reader.num_traces()
    first_trace = reader.trace_header(0)

    # Define index of last trace
    max_trace_number = reader.num_traces() - 1
    
    # Find if 2D or 3D data. 3 = 3D
    dimensions = reader.dimensionality 
    
    # Get simplified lines/polygons to plot
    if dimensions == 3:
        # Find crossline range
        min_xline = first_trace.crossline_number
        max_xline = reader.trace_header(max_trace_number).crossline_number
        range_xline = max_xline - min_xline
        # trace_range = (lower left, lower right, upper right, upper left)
        # (orientation may vary depending on direction of survey)
        # Listed in this order so corners connect in a square when plotted.
        trace_range = 0, range_xline, max_trace_number, max_trace_number - range_xline
    else:
        # Simplify data in 2D data. ie. only take every 200 values.
        trace_range = []
        for i in range(0, max_trace_number, 200):
            trace_range.append(i)  
    
    # Set correct scaling for traces - make positive
    trace_scalar = first_trace.xy_scalar
    if trace_scalar < 0:
        scalar = 1/(trace_scalar * -1)
    else:
        scalar = trace_scalar
    # Make sure trace coordinates are scaled correctly.
    first_cdp_x = first_trace.cdp_x * scalar
    first_source_x = first_trace.source_x * scalar
    first_group_x = first_trace.group_x * scalar  
    
    # Get coordinated for each trace in simplified lists
    x = []
    y = []
    for i in trace_range:
        trace = reader.trace_header(i)
        
        if first_cdp_x != 0:
            # cdp is "real" datapoint. So use this if not equal to 0
            cdp_x = trace.cdp_x * scalar
            cdp_y = trace.cdp_y * scalar
            x_points = cdp_x
            y_points = cdp_y
        elif first_source_x != 0:
            # Some data has the same value for source as cdp.
            # Most data has source if nothing else.
            # Therefore if cdp not available, use source if not equal to 0
            source_x = trace.source_x * scalar
            source_y = trace.source_y * scalar
            x_points = source_x
            y_points = source_y
        else:
            # Use group if cdp or source not available
            group_x = trace.group_x * scalar
            group_y = trace.group_y *scalar
            x_points = group_x
            y_points = group_y
            
        x.append(x_points)
        y.append(y_points)
    

    # Create a Proj class for data and required coordinate systems
    spatial_ref = "+init=" + data_projection
    projection = "+init=" + required_projection
    ref = pyproj.Proj(spatial_ref)
    proj = pyproj.Proj(projection)
    # Convert x, y to required coordinate system 
    # (assumed to be lat, lon for the purpose of naming variables)
    lon, lat = pyproj.transform(ref, proj, x, y)
    
    # If 3d data, close the loop to plot a polygon
    if dimensions == 3:
        lon.append(lon[0])
        lat.append(lat[0])
        plt.plot(lon, lat)
    else:
        plt.plot(lon, lat)
    
    # Find max and min lat lon to set grid axes extents
    lats.append(max(lat))
    lats.append(min(lat))
    lons.append(max(lon))
    lons.append(min(lon))
    
    # Annotate lines with a number at first trace
    # Use of numbers keeps map tidy
    ax.annotate(filenumber, xy=(lon[0], lat[0]))
    #Write number and associated file to legend
    legend.write(str(filenumber)+": "+str(file)+"\n")
    
    # Provide survey geometry in legend
    if first_cdp_x != 0:
        legend.write("        Location of:  CDP\n")
    elif first_source_x != 0:
        legend.write("        Location of:  Source \n")
    else:
        legend.write("        Location of:  Group \n")
    
    if dimensions == 3:
        dimension.append("3D")
        legend.write("        Type:         3D \n")
        legend.write("        Extents:      " + 
                     str(lon[0]) + ",  " + str(lat[0]) + "\n")
        legend.write("                      " + 
                     str(lon[1]) + ",  " + str(lat[1]) + "\n")
        legend.write("                      " + 
                     str(lon[2]) + ",  " + str(lat[2]) + "\n")
        legend.write("                      " + 
                     str(lon[3]) + ",  " + str(lat[3]) + "\n\n")
    else:
        dimension.append("2D")
        legend.write("        Type:         2D \n")
        legend.write("        Start:        " + 
                     str(lon[0]) + ",  " + str(lat[0]) + "\n")
        legend.write("        End:          " + 
                     str(lon[-1]) + ",  " + str(lat[-1]) + "\n\n")
    # Increase number by one to identify next file in list
    filenumber += 1
    
    #Realease the file
    files.close() 



# Stop timer and write processing time to legend
time = datetime.now() - start
legend.write('----------\nMapping Time: '  + 
             str(int(time.total_seconds() )) + ' s')
#ʀelease legend file
legend.close()

#Create 10% buffer to control zoom level
lat_buffer = (max(lats) - min(lats))/10
lon_buffer = (max(lons) - min(lons))/10
#set grid extents with buffer
plt.ylim(min(lats)-lat_buffer, max(lats)+lat_buffer)
plt.xlim(min(lons)-lon_buffer, max(lons)+lon_buffer)
plt.grid(True)

#Use directory as figure title
if "2D" in dimension:
    plt.title(directory+":\n"+str(data_projection)+" to "+
              str(required_projection)+"\n2D Line Resolution = "
              +str(resolution)+" traces per point")
else:
    plt.title(directory+":\n"+str(data_projection)+" to "+
              str(required_projection))
#Save map as .png
plt.savefig(str(survey)+'_layout.png',dpi=300)

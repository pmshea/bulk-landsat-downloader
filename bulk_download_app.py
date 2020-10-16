#!/usr/bin/env python
# coding: utf-8

# In[13]:


import pandas as pd
import numpy as np
import geopandas as gpd
import folium
import os, shutil
from glob import glob
import requests
from bs4 import BeautifulSoup
from google.cloud import storage


# In[15]:


# reads my boundary shapefile 
bounds = gpd.read_file('../GeoData/boundaryFinal.gpkg')

# creates path variables for WRS and landsat folders 
WRS_PATH = '../GeoData/Landsat8/WRS2_descending_0.zip'
LANDSAT_PATH = os.path.dirname(WRS_PATH)

shutil.unpack_archive(WRS_PATH, os.path.join(LANDSAT_PATH, 'wrs2'))

wrs = gpd.GeoDataFrame.from_file('../GeoData/Landsat8/wrs2/WRS2_descending.shp')
wrs_intersection = wrs[wrs.intersects(bounds.geometry[0])]

# creates path (unrelated to file architecture paths) and row variables for wrs2-boundary intersection
paths, rows = wrs_intersection['PATH'].values, wrs_intersection['ROW'].values

# get the center of the map
xy = np.asarray(bounds.centroid[0].xy).squeeze()
center = list(xy[::-1])

# select a zoom
zoom = 6

# create the most basic OSM folium map
m = folium.Map(location=center, zoom_start=zoom, control_scale=True)

# add the bounds GeoDataFrame
m.add_child(folium.GeoJson(bounds.__geo_interface__, name='Maricopa County', 
                           style_function=lambda x: {'color': 'red', 'alpha': 0}))

# iterate through each polygon of paths and rows intersecting the area
for i, row in wrs_intersection.iterrows():
    # create a string for the name containing the path and row of this polygon
    name = 'path: %03d, row: %03d' % (row.PATH, row.ROW)
    # create the folium geometry of this polygon 
    g = folium.GeoJson(row.geometry.__geo_interface__, name=name)
    # add a folium popup object with the name string
    g.add_child(folium.Popup(name))
    # add the object to the map
    g.add_to(m)

folium.LayerControl().add_to(m)
m.save('../GeoData/images/wrs.html')


# In[ ]:


# # finds scenes that match criteria and creates list of selection

# scene_selection = pd.read_csv('../GeoData/Landsat8/index.csv', chunksize=1000)

# bulk_list = []

# # iterate through paths and rows

# for chunk in scene_selection: 
    
#     for path, row in zip(paths, rows):

#         # filter the google table for images matching path, row, satellite, datetime, cloudcover, processing state
#         scenes = chunk[(chunk.WRS_PATH == path) & (chunk.WRS_ROW == row) & 
#                            (chunk.CLOUD_COVER <= 5) & 
#                            (~chunk.PRODUCT_ID.str.contains('_T2')) &
#                            (~chunk.PRODUCT_ID.str.contains('_RT')) &
#                            (chunk.SPACECRAFT_ID == 'LANDSAT_8') & 
#                            (chunk.SENSING_TIME > '2018-01-01')]
        
#         if len(scenes) > 0: 
#             print('Path:',path, 'Row:', row)
#             print(' Found {} images\n'.format(len(scenes)))

#         if len(scenes):
#             scenes = scenes.sort_values('CLOUD_COVER').iloc[0]

#         if len(scenes) > 0:
#             bulk_list.append(scenes)
            
# print(len(bulk_list))


# In[12]:


# creates dataframe object and writes csv file of scene selection

# bulk_frame = pd.concat(bulk_list, 1).T
# bulk_frame = bulk_frame.sort_values(by=['DATE_ACQUIRED'], ascending=False)
bulk_frame = pd.read_csv('scene_selection.csv')

test_frame = bulk_frame[bulk_frame['PRODUCT_ID'] == 'LC08_L1TP_037038_20200925_20201006_01_T1']                       [bulk_frame['PRODUCT_ID'] == 'LC08_L1TP_037036_20200925_20201006_01_T1']                       [bulk_frame['PRODUCT_ID'] == 'LC08_L1TP_037037_20200925_20201006_01_T1']                       [bulk_frame['PRODUCT_ID'] == 'LC08_L1TP_036036_20200918_20201006_01_T1']

print(test_frame)

# uses scene selection to download scenes from amazon server

for i, row in test_frame.iterrows():
    
    print('\n', 'EntityId:', row.PRODUCT_ID, '\n')
    print(' Checking content: ', '\n')
    
    
    
    row_url = 'https://landsat-pds.s3.amazonaws.com/c1/L8/{}/{}/{}/index.html'.format(row.WRS_PATH, row.WRS_ROW, row.PRODUCT_ID)
    
    response = requests.get(row_url)
    
    if response.status_code == 200:

        # Import the html to beautiful soup
        html = BeautifulSoup(response.content, 'html.parser')
        entity_dir = os.path.join(LANDSAT_PATH, row.PRODUCT_ID)
        os.makedirs(entity_dir, exist_ok=True)
        
        for li in html.find_all('li'):

            # Get the href tag
            file = li.find_next('a').get('href')

            print('  Downloading: {}'.format(file))

            # Download the files
            # code from: https://stackoverflow.com/a/18043472/5361345

            response = requests.get(row_url.replace('index.html', file), stream=True)

            with open(os.path.join(entity_dir, file), 'wb') as output:
                shutil.copyfileobj(response.raw, output)
            del response


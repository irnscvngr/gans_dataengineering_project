# -*- coding: utf-8 -*-
"""
Created on Mon Apr  8 08:54:56 2024
@author: Patrick Hausmann

"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
# --- Custom modules
from get_keys import get_keys


# =============================================================================
# GET CITY LATITUDE, LONGITUDE AND COUNTRY CODE
# =============================================================================
def get_geocoords(cities):
    if(type(cities) is str):
        cities = [cities]
    # --- INITIALIZE NEW DATAFRAME
    geocoords = pd.DataFrame({'city':[],
                       'latitude':[],
                       'longitude':[],
                       'country':[]})
    # Set query parameters
    for i,city in enumerate(cities):
        params = {
            'q':city,
            'appid':get_keys('openweathermap')
            }
        # Build query URL
        url = "http://api.openweathermap.org/geo/1.0/direct?"
        # Query API and store response
        response = requests.get(url,params).json()[0]
        # Transform response to dataframe
        res = pd.DataFrame({
            'city':city,
            'latitude':response['lat'],
            'longitude':response['lon'],
            'country':response['country']},index=[i])

        # Extrend DataFrame
        geocoords = pd.concat([geocoords,res])
                         
    # Return response
    return geocoords


# =============================================================================
# GET CITY POPULATIONS
# =============================================================================
def get_population(cities):
    if(type(cities) is str):
        cities = [cities]
    # Connect to List of cities with over 1 Mio. Inhabitants on Wikipedia
    url = "https://en.wikipedia.org/wiki/List_of_cities_with_over_one_million_inhabitants"
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    # Get table from page
    citytable = soup.find_all('table')[1].find('tbody').find_all('tr')
    # Initialize empty DataFrame
    citydata = {}
    # --- GO THROUGH CITY TABLE
    for i in range(1,len(citytable)):
        td = citytable[i].find_all('td')
        name = td[0].text.split("\n")[0]
        population = int(td[2].text.split("\n")[0].replace(',',''))
        citydata[name] = population
    # Output population of selected cities
    res = [citydata.get(key) for key in cities]
    # Output scalar value in case of scalar query
    if(len(cities)==1):
        res = res[0]
    # --- RETURN RESULTS
    return res


# TESTING
# cities = ['Berlin','Munich']
# cities = 'Cologne'
# get_population(cities)


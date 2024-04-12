# -*- coding: utf-8 -*-
"""
Created on Mon Apr  8 11:37:08 2024
@author: Patrick Hausmann

"""

import requests
import pandas as pd
from datetime import datetime
# ---
from get_keys import get_keys


# =============================================================================
# 
# =============================================================================
def init_weather_df():
    df_weather = pd.DataFrame({
        'city':[],
        'time':[],
        'weather_id':[],
        'rain':[],
        'rain_prob':[],
        'windspeed':[],
        'temp':[],
        'temp_feel':[],
        'temp_min':[],
        'temp_max':[],
        'vis':[]
    })
    return df_weather


# =============================================================================
# GET 5D/3H-WEATHERFORECAST PER CITY
# =============================================================================
def weather_forecast(cities,timeframe):
    print("Getting weather forecasts...")
    if(type(cities) is str):
        cities = [cities]
    
    # Create new DataFrame to collect weather data
    df_weather_full = init_weather_df()
    
    # GO THROUGH ALL CITY IDs
    for city in cities:
        print(f"Get weather for {city}...")
        # --- API CALL
        # Only return 5 entries (&cnt=5) to limit forecast to 12h (= (5-1)*3h)
        # To fall in line with flights API (max. 12h)
        params = {'q':city,
                  'appid':get_keys('openweathermap'),
                  'units':'metric',
                  'cnt':int(min(1+timeframe/3,5*24/3))
                  }
        url = "http://api.openweathermap.org/data/2.5/forecast?"
        response = requests.get(url,params)
        response = response.json()['list']
        
        # Create temporary DF to store weather data
        df_weather = init_weather_df()
        
        # --- GO THROUGH RESPONSE ELEMENTS
        for i in range(len(response)):
            df_weather.loc[i,'weather_id'] = response[i]['weather'][0]['id'] # Weather condition according to https://openweathermap.org/weather-conditions
            df_weather.loc[i,'time'] = datetime.utcfromtimestamp(response[i]['dt']) # Time of data forecasted, unix, UTC -> Convert back to UTC
            # Rain-Key doesn't always exist
            if ('rain' in response[i].keys()):
                df_weather.loc[i,'rain'] = response[i]['rain']['3h'] # Rain Volume for last 3 hours in [mm]
            df_weather.loc[i,'windspeed'] = response[i]['wind']['speed'] # Wind speed in [m/s]
            df_weather.loc[i,'temp'] = response[i]['main']['temp'] # Forecasted temperature in °C
            df_weather.loc[i,'temp_min'] = response[i]['main']['temp_min'] # Forecasted minimal temperature in °C
            df_weather.loc[i,'temp_max'] = response[i]['main']['temp_max'] # Forecasted maximal temperature in °C
            df_weather.loc[i,'temp_feel'] = response[i]['main']['feels_like'] # Human perception of forecasted temperature in °C
            if ('visibility' in response[i].keys()):
                df_weather.loc[i,'vis'] = response[i]['visibility'] # Average visibility in meters
            df_weather.loc[i,'rain_prob'] = response[i]['pop'] # Probability of precipitation (0...1)

        # If rain-prob is 0, rain-value is NaN -> Convert to 0
        df_weather.loc[df_weather['rain'].isna(),'rain'] = 0
        # Convert timestring to datetime
        df_weather['time'] = pd.to_datetime(df_weather['time'])
        # Add city ID
        df_weather['city'] = city
        
        # Add current forecast to forecast-collection
        df_weather_full = pd.concat([df_weather_full,df_weather])
               
        # Make integer from float ID
        df_weather_full['weather_id'] = df_weather_full['weather_id'].astype(int)
    
    # OUTPUT FORECAST-COLLECTION
    return df_weather_full.reset_index(drop=True)


# TESTING
# cities=['Berlin',
#         'Cologne',
#         'Munich',
#         'Bangalore',
#         'Paris',
#         'Madrid',
#         'Los Angeles',
#         'Shanghai']
# weather_forecast(cities,4)

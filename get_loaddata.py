# -*- coding: utf-8 -*-
"""
Created on Mon Apr  8 15:52:54 2024
@author: Patrick Hausmann

"""

import random as rnd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from scipy.interpolate import splrep, BSpline
# ---
import customplots as cp
cp.customfont(10)


# =============================================================================
# TOTAL CUSTOMERLOAD FOR QUERIED TIMES
# =============================================================================
def get_customerload(flightload_city,weatherfactor_city,baseload_city):
    print("Get customerload per city...")
    # Copy dataframe to use as a template
    customerload = flightload_city.copy()
    # Get hour-information from flights-time to retrieve baseload-value later
    flightload_city['hour'] = flightload_city['scheduled_time'].dt.hour
    
    # --- GO THROUGH ALL CITIES
    for i,city in enumerate(flightload_city['city']):
        print(f"Get customerload for {city}")
        # --- BASELOAD
        # Get baseload information for current city
        df = baseload_city[baseload_city['city']==city]
        # Get baseload-value for corresponding time/hour
        customerload.loc[i,'baseload'] = (
            df[df['time']==flightload_city.loc[i,'hour']]['baseload'].iloc[0]
            )
        # --- WEATHERFAC
        # Get weatherfactors for current city
        select_wf = weatherfactor_city['city']==city
        # Get weatherfactors for current time
        select_wf = select_wf & (weatherfactor_city.loc[select_wf,'wtime']==flightload_city.loc[i,'scheduled_time'])
        # Try to extract WF for current city and time
        wf = weatherfactor_city.loc[select_wf,'weatherfac']
        if(wf.empty):
            # If no factor available -> NaN
            customerload.loc[i,'weatherfac'] = np.nan
        else:
            # If available -> Store weatherfac to DataFrame
            customerload.loc[i,'weatherfac'] = wf.iloc[0]
    
    # Calculate Total Load
    customerload['total_load'] = (
        (customerload['baseload'] + customerload['flightload'])
        *customerload['weatherfac']
        )
    
    # Rename time-column
    customerload = customerload.rename(columns={'scheduled_time':'ltime'})
    
    # Return results
    return customerload


# =============================================================================
# BASELOAD FROM 0...24h IN 0...100%
# =============================================================================
def get_baseload(xq,population,seed=rnd.random()):
    print("Get baseload by population...")
    # Min and Max relative load
    lmin = 0.001
    lmax = 0.1
    
    # Set random-seed
    rnd.seed(seed)
    
    # Define base points
    x = np.array([0,
                  2,
                  8,
                  12,
                  18,
                  22,
                  24])
    y = np.array([lmin,
                  lmax/10,
                  lmax,
                  lmax/1.5,
                  lmax,
                  lmax/10,
                  lmin])
    
    for i in range(2,len(x)-2):
        rnd.seed(seed+i)
        x[i] += rnd.uniform(-0.9,0.9)
        y[i] *= rnd.uniform(0.8,1.2)
    
    # Create B-spline interpolation function
    t, c, k = splrep(x, y, s=0, k=2)
    spline = BSpline(t, c, k, extrapolate=False)    
    
    # Evaluate spline at the finer x values
    y_interp = abs(spline(xq))*population
    
    if 0:
        # Plot base points and spline curve
        # plt.plot(x, y, 'o', label='Base Points')
        plt.plot(xq, y_interp, label='B-spline Curve')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('B-spline Interpolation')
        plt.legend()
        plt.grid(True)
        plt.show()
    
    # Return results
    return y_interp


# =============================================================================
# 
# =============================================================================
def get_baseload_per_city(cities,population):
    print("Get baseload per city...")
    # --- MERGE CITIES AND POPULATION TABLE
    df_pop = (
          population[population['pyear']==datetime.now().year]
          .merge(cities[['city','city_id']],on='city_id',how='left')
          .drop_duplicates()
          )
    # Initialize new dataframe to store results
    baseload = pd.DataFrame({'city':[],'time':[],'baseload':[]})
    # Query every 3h
    # (Because weather forecast is every 3h)
    xq = np.linspace(0,24,9)
    # --- GO THROUGH ALL CITIES
    for city in df_pop['city']:
        print(f"Get baseload for {city}...")
        # Get current population
        pop = df_pop[df_pop['city']==city]['population'].iloc[0]
        # Store result
        res = pd.DataFrame({'city':city,'time':xq,'baseload':get_baseload(xq, pop)})
        # Append result to DataFrame
        baseload = pd.concat([baseload,res])
    # Convert time (3h steps) to integer
    baseload['time'] = baseload['time'].astype(int)
    # Return result
    return baseload


# =============================================================================
# 
# =============================================================================
def get_weatherfactor(weather):
    print("Get weatherfactor per city ID...")
    # --- GET INDIVIDUAL WEATHER-FACTORS
    # Rain volume in mm for 3h
    # Values taken from World Meteorological Organization:
    # https://community.wmo.int/en/activity-areas/aviation/hazards/precipitation#:~:text=While%20there%20is%20no%20agreed,of%2010%20mm%20per%20hour.
    fac_rain = pd.Series(np.interp(weather['rain'],(0,12),(1,0)))
    # Rain probability
    fac_rainprob = pd.Series(np.interp(weather['rain_prob'],(0,1),(1,0.2)))
    # Temperature
    fac_temp = pd.Series(np.interp(weather['temp_feel'],(-5,15),(0,1)))
    # Wind speed in m/s
    # https://education.nationalgeographic.org/resource/beaufort-scale/
    fac_wind = pd.Series(np.interp(weather['windspeed'],(0,55.0/3.6),(1,0)))
    # --- CONCAT FACTORS AND PICK MINIMUM
    weatherfactor = pd.concat(
        [fac_rain,fac_rainprob,fac_temp,fac_wind],
        axis=1).min(axis=1)
    # Rename Series
    weatherfactor = weatherfactor.rename('weatherfac')
    # Concat with city ID and return
    weatherfactor = pd.concat([weather[['wtime','city_id']],weatherfactor],axis=1)
    # Return results
    return weatherfactor


# =============================================================================
# 
# =============================================================================
def get_weatherfactor_per_city(weather,cities):
    print("Get weatherfactor per city...")
    res= (
        weather
        # Get City Name from cities table
        .merge(cities[['city','city_id']],on='city_id',how='left')
        # Drop city_id column
        .drop(columns=['city_id'])
        )
    # Return results
    return res
    
# =============================================================================
# GET LOAD OF CUSTOMERS FROM FLIGHT-PASSENGERS
# =============================================================================
def get_flightload_per_airport(flights,seed=rnd.random()):
    print("Get flightload per airport...")
    # Get seat configuration from flights
    passengers = get_passengers(flights)
    
    # Typical loadout for passenger planes
    # Source:
    # https://www.statista.com/statistics/658830/passenger-load-factor-of-commercial-airlines-worldwide/#:~:text=Commercial%20airlines%20worldwide%20%2D%20passenger%20load%20factor%202005%2D2023&text=Global%20airlines'%20combined%20passenger%20load,factor%20dropped%20to%2065%20percent
    loadfac = 0.826
    
    # Set random-seed
    rnd.seed(seed)
    
    # Min./Max. Load
    lmin = 0.005
    lmax = 0.05
    
    # Amount of passengers per plane using an e-scooter
    flightload = passengers*rnd.uniform(lmin,lmax)*loadfac
    
    # Return rounded result
    flightload = round(flightload).rename('flightload')
    
    # Add scheduled time and IATA-code back to result
    res = pd.concat([flights[['scheduled_time','iata']],flightload],axis=1)
    # Try/Except for the case that flights-data is missing
    try:
        # Group by airport and sum up load for 3h each
        # (Because weather forecast is based on 3h)
        res = (res
               .set_index('scheduled_time')
               .groupby('iata')
               .resample('3H')
               .sum('flightload')
               .reset_index()
               )
    except:
        print("Error detected. Probably no flights data available.")
    # Return results
    return res


# =============================================================================
# 
# =============================================================================
def get_flightload_per_city(flightload,airports,cities):
    print("Get flightload per city...")
    # --- MERGE CITY TABLE TO FLIGHTLOAD TO GET CITY-NAMES
    res= (
        flightload
        # Get City ID from airports table
        .merge(airports[['iata','city_id']],on='iata',how='left')
        # Get City Name from cities table
        .merge(cities[['city','city_id']],on='city_id',how='left')
        # Drop IATA and city_id columns
        .drop(columns=['iata','city_id'])
        )
    #
    # --- GROUP EQUAL CITIES TOGETHER AND RESAMPLE BY 3h
    # (Because weatherforecast is in 3h raster)
    res = (res
           .set_index('scheduled_time')
           .groupby('city')
           .resample('3H')
           .sum('flightload')
           .reset_index()
           )
    # Return results
    return res


# =============================================================================
# EXTRACT POTENTIAL PASSENGERS FROM FLIGHTS
# =============================================================================
def get_passengers(flights):
    print("Extract passengers from flights...")
    # Get missing entries
    select = flights['typ_config'].isna()
    # Median of most flights is 150 seats per airplane
    flights.loc[select,'typ_config'] = 150
    # Return seats/passengers only
    return flights['typ_config']


# =============================================================================
# 
# =============================================================================
def get_load_total(cities,population,weather,airports,flights):
    print("Get total customerload (base + flights + weather)...")
    # Get flightload per airport
    flightload_iata = get_flightload_per_airport(flights)
    # Get flightload per city
    flightload_city = get_flightload_per_city(flightload_iata, airports, cities)
    # Get weatherfactor per city (from weather-forecast)
    weatherfactor_city = get_weatherfactor_per_city(get_weatherfactor(weather),cities)
    # Get general baseload per city (0...24h)
    baseload_city = get_baseload_per_city(cities, population)
    # Get total customerload per city
    customerload = get_customerload(flightload_city,weatherfactor_city,baseload_city)
    # Return results
    return customerload

# =============================================================================
# 
# =============================================================================
def format_load_total(cities,population,weather,airports,flights):
    print("Get total customerload formatted for SQL...")
    customerload = get_load_total(cities,population,weather,airports,flights)
    #
    customerload = (
        customerload
        .merge(cities[['city_id','city']],on='city',how='left')
        .drop(columns=['city','total_load'])
        )
    #
    return customerload

# =============================================================================
# 
# =============================================================================
def plot_load(df,xv,yv,hv):
    ax = sns.lineplot(
        data = df,
        x = xv,
        y = yv,
        hue = hv,
        palette = 'viridis',
        errorbar = None,
        linewidth = 2.2
        );
    
    cp.declutter(ax)
    ax.tick_params(axis='x',rotation=45)
    
    ax.set_title(yv)
    return ax


# =============================================================================
# TESTING
# =============================================================================
def testing():
    print("Testing...")
    # --- GET SQL-DATA
    # cities = pd.read_sql("cities", con=connect_to_sql())
    # population = pd.read_sql("population", con=connect_to_sql())
    # weather = pd.read_sql("weather", con=connect_to_sql())
    # airports = pd.read_sql("airports", con=connect_to_sql())
    # flights = pd.read_sql("flights", con=connect_to_sql())
    
    
    # --- GET LOAD TOTAL AND MAKE SOME TEST PLOTS
    # load_total = get_load_total(cities,population,weather,airports,flights)
    # plot_load(load_total,'ltime','total_load','city');
    
    # return load_total

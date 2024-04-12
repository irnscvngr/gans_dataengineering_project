# -*- coding: utf-8 -*-
"""
Created on Mon Apr  8 18:57:14 2024
@author: Patrick

"""

import numpy as np
import pandas as pd
import time
from datetime import datetime
# ---
import get_flightsdata as fd
import get_weatherdata as wd
import get_citydata as cd
import get_loaddata as ld
from get_keys import get_keys
# ---
import functions_framework
# ---
import sqlalchemy
import pymysql


# =============================================================================
# DEFINE CITIES OF INTEREST
# =============================================================================
cities=[#'Berlin',
        'Cologne',
        #'Munich',
        'Bangalore',
        'Paris',
        'Madrid',
        'Los Angeles',
        'Shanghai']


# =============================================================================
# UPDATE DATABASE
# =============================================================================
@functions_framework.http
def update_database(request):
    con = connect_to_sql();
    # simpletest(con);
    update_cities();
    update_population();
    update_airports();
    update_weather(48); # Timeframe possible
    update_flights(48); # Timeframe possible
    update_load();
    return 'Database update successful.'
    

# =============================================================================
# SETUP MySQL CONNECTION
# =============================================================================

def connect_to_sql():
  print("Connecting to SQL...")
  connection_name = "wbsproject01:europe-west1:wbs-mysql-db"
  # db_user = "root"
  db_user = "wbs-mysql-db"
  # db_password = get_keys('mysql_gcp')
  db_password = "wbsPH_24gans"
  schema_name = "gans"

  driver_name = 'mysql+pymysql'
  query_string = {"unix_socket": f"/cloudsql/{connection_name}"}

  db = sqlalchemy.create_engine(
      sqlalchemy.engine.url.URL(
          drivername = driver_name,
          username = db_user,
          password = db_password,
          database = schema_name,
          query = query_string,
      )
  )

  return db

# =============================================================================
# SIMPLETEST
# =============================================================================
def simpletest(con_string):
  data = {'city':['test1','test2'],
          'country':['Ctest1','Ctest2'],
          'latitude':[66,77],
          'longitude':[88,99],}
  df = pd.DataFrame(data)
  df.to_sql(name="cities", con=connect_to_sql(), if_exists='append', index=False)


# =============================================================================
# CONCAT DATAFRAMES BASED ON CUSTOM ID
# Takes columns given as list in "cols", converts their values to string and 
# generates a uniqe ID from them.
# Then compares 2 dataframes based on this ID and gives back the part of DF2
# that is not present in DF1
# =============================================================================
def append_by_condition(df2,df1,cols):
    # --- GO THROUGH COLUMNS AND GENERATE UNIQUE ID
    def add_cond_col(df,cols):
        # Reset-Index to avoid duplicate-errors
        df = df.reset_index(drop=True)
        # Initialize new series to store unique ID
        cond = pd.Series(['']*df.shape[0],dtype=str)
        # --- GO THROUGH COLUMS
        for col in cols:
            # Take each column, format to string, and concat with previous iter.
            cond += df[col].astype(str)
        # Add new colum to dataframe which contains the unique ID
        df['_cond'] = cond
        return df
    
    # --- ADD UNIQUE ID COLUMNS TO DATAFRAMES
    df1 = add_cond_col(df1,cols)
    df2 = add_cond_col(df2,cols)
    # Find differences between unique IDs
    dif = np.setdiff1d(list(df2['_cond']),list(df1['_cond']))
    # Make selector based on differences
    # Only keep parts of df2 where a difference was detected
    select = df2['_cond'].isin(dif)
    # Return part of df2 that was not already present in df1 (by unique ID)
    return df2.loc[select,:].drop(columns='_cond')


# =============================================================================
# CUSTOM DROP DUPLICATES
# Takes a list of columns to generate custom unique identifier.
# (e.g. airport-IATA code, flight number and scheduled time)
# Drops duplicates of rows where this custom combination appears more than once
# Returns DF without those custom duplicates
# =============================================================================
def drop_duplicates_custom(df,cols):
    # Create empty column to store custom unique ID
    df['_unique'] = ['']*df.shape[0]
    # Go through custom columns and create unique ID
    for col in cols:
        # Build ID from column-value converted to string
        df['_unique'] += df[col].astype(str)
    # Drop rows with duplicated uniqueID
    # And also drop uniqueID column as it's only temporarily
    df = df.drop_duplicates('_unique').drop(columns='_unique')
    # Return DF without custom duplicates
    return df

# =============================================================================
# CITIES
# city, country, latitude, longitude
# =============================================================================
def update_cities():
    print(">>>>>Updating Cities...")
    # --- GET CITIES FROM DATABASE
    cities_db = pd.read_sql("cities", con=connect_to_sql())
    
    # --- COMPARE CITYLIST WITH DATABASE -> FIND POTENTIAL NEWCOMERS
    cities_add = np.setdiff1d(cities,cities_db['city'])
    
    # --- GET DATA FOR NEWCOMERS
    cities_add = cd.get_geocoords(cities_add)
    
    print("Writing Cities to database...")
    # --- ADD NEWCOMERS TO DATABASE
    # "city_id" will be set automatically in MySQL
    cities_add.to_sql('cities',
                    if_exists='append',
                    con=connect_to_sql(),
                    index=False);
    print(">>>>>Cities updated.")

# =============================================================================
# POPULATION
# city_id, pyear, population
# =============================================================================
def update_population():
    print(">>>>>Updating Population...")
    # --- GET CURRENT CITIES AND POPULATION FROM DATABASE
    cities_db = pd.read_sql("cities", con=connect_to_sql())
    population_db = pd.read_sql("population", con=connect_to_sql())
    
    # --- MAKEW NEW DATAFRAME WITH POPULATION-DATA FROM CITIES-LIST
    population_add = pd.DataFrame({'city_id':cities_db['city_id'],
                                   'pyear':datetime.now().year,
                                   'population':cd.get_population(cities_db['city'])})
    
    # Add Newcomers where no match already exists in database
    population_add = append_by_condition(population_add,population_db,['city_id','pyear'])
          
    # --- ADD NEWCOMERS TO DATABASE
    population_add.to_sql('population',
                    if_exists='append',
                    con=connect_to_sql(),
                    index=False);
    print(">>>>>Population updated.")

# =============================================================================
# WEATHER
# city_id, wtime, weather_id, rain, rain_prob, windspeed, temp,
# temp_feel, temp_min, temp_max, vis
# =============================================================================
def update_weather(timeframe=12):
    print(">>>>>Updating Weather...")
    # --- GET CURRENT CITIES AND WEATHER FROM DATABASE
    cities_db = pd.read_sql("cities", con=connect_to_sql())
    weather_db = pd.read_sql("weather", con=connect_to_sql())
    
    # --- GET WEATHER-FORECAST
    weather_add = wd.weather_forecast(cities_db['city'], timeframe)
    
    # Add city_id to weatherforecast
    weather_add = weather_add.merge(cities_db[['city','city_id']],how='left',on='city')
    
    # Rename time-column to match with database
    weather_add = weather_add.rename(columns={'time':'wtime'})
    
    # Add Newcomers where no match already exists in database
    weather_add = append_by_condition(weather_add,weather_db,['city_id','wtime'])
    # Drop 'city'-column to match with database
    weather_add = weather_add.drop(columns='city')
    
    # --- ADD NEWCOMERS TO DATABASE
    weather_add.to_sql('weather',
                    if_exists='append',
                    con=connect_to_sql(),
                    index=False);
    print(">>>>>Weather updated.")

# =============================================================================
# AIRPORTS
# city_id, iata, latitude, longitude
# =============================================================================
def update_airports():
    print(">>>>>Updating Airports...")
    # --- GET CURRENT CITIES AND AIRPORTS FROM DATABASE
    cities_db = pd.read_sql("cities", con=connect_to_sql())
    airports_db = pd.read_sql("airports", con=connect_to_sql())
    
    # --- INITIALIZE NEW AIRPORTS-DATAFRAME
    airports_add = pd.DataFrame()
    # --- GO THROUGH ALL CITIES
    for row in cities_db.itertuples():
        print(f"Get airports for {row[2]}...")
        time.sleep(0.5)
        # Get airports by latitude and longitude
        res = fd.get_airports(row[4],row[5])
        # Get cityname
        res['municipalityName'] = row[2]
        # Add airports to list
        airports_add = pd.concat([airports_add,res]).reset_index(drop=True)
    
    # --- PROCESS DATAFRAME
    # Only keep needed columns
    airports_add = airports_add[['iata','location.lat','location.lon','municipalityName']]
    # Change column-name to merge with city-table
    airports_add = airports_add.rename(columns={'municipalityName':'city',
                                                'location.lat':'latitude',
                                                'location.lon':'longitude'
                                                })
    # Merge with city-table to get city-ID
    airports_add = airports_add.merge(cities_db[['city','city_id']],how='left',on='city')
    
    # Add Newcomers where no match already exists in database
    airports_add = append_by_condition(airports_add,airports_db,['city_id','iata'])
    # Drop 'city'-column
    airports_add = airports_add.drop(columns='city')
    
    # --- ADD NEWCOMERS TO DATABASE
    airports_add.to_sql('airports',
                    if_exists='append',
                    con=connect_to_sql(),
                    index=False);
    print(">>>>>Airports updated.")
    
# =============================================================================
# FLIGHTS
# iata, ftype, fnumber, scheduled_time, revised_time, terminal, aircraft,
# airline, typ_config
# =============================================================================
def update_flights(timeframe=12):
    print(">>>>>Updating Flights...")
    # --- GET CURRENT CITIES AND FLIGHTS FROM DATABASE
    cities_db = pd.read_sql("cities", con=connect_to_sql())
    flights_db = pd.read_sql("flights", con=connect_to_sql())
       
    # Get flight-forecast and adjust colum-names
    flights_add = (fd.get_flightsdata(cities_db['city'],timeframe)
                   .rename(columns={'number':'fnumber',
                                    'type':'ftype',
                                    'typ. config.':'typ_config'})
                   )
    
    # Add Newcomers where no match already exists in database
    flights_add = append_by_condition(flights_add,flights_db,['iata','fnumber','scheduled_time'])
    # Drop city column
    flights_add = flights_add.drop(columns='city')
    
    # Drop duplicates to be sure!
    flights_add = flights_add.drop_duplicates()
    
    # Drop duplicates of specific column combination to be super sure!
    flights_add = drop_duplicates_custom(
        flights_add, ['iata','fnumber','scheduled_time'])
    
    # --- ADD NEWCOMERS TO DATABASE
    flights_add.to_sql('flights',
                    if_exists='append',
                    con=connect_to_sql(),
                    index=False);
    print(">>>>>Flights updated.")

# =============================================================================
# 
# =============================================================================
def update_load():
    print(">>>>>Updating Load...")
    # --> Needs flights data to work!
    # --- GET CURRENT VALUES FROM DATABASE
    cities = pd.read_sql("cities", con=connect_to_sql())
    population = pd.read_sql("population", con=connect_to_sql())
    weather = pd.read_sql("weather", con=connect_to_sql())
    airports = pd.read_sql("airports", con=connect_to_sql())
    flights = pd.read_sql("flights", con=connect_to_sql())
    customerload_db = pd.read_sql("customerload", con=connect_to_sql())
    
    # --- GET CURRENT LOAD-FORECAST
    customerload_add = (
        ld.format_load_total(cities, population, weather, airports, flights)
        )

    # Add Newcomers where no match already exists in database
    customerload_add = append_by_condition(
        customerload_add,
        customerload_db,
        ['city_id','ltime']
        )
    
    # --- ADD NEWCOMERS TO DATABASE
    customerload_add.to_sql('customerload',
                    if_exists='append',
                    con=connect_to_sql(),
                    index=False);
    print(">>>>>Load updated.")





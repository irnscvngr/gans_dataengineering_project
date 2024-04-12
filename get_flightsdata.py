# -*- coding: utf-8 -*-
"""
Created on Fri Apr  5 16:01:20 2024
@author: Patrick Hausmann

Main function: get_flights_by_iata(timeframe,IATA_code)

Usage:
    Set timeframe (e.g. 18 hours)
    
    Select airport via IATA_code (e.g. "CGN" for Cologne, Germany)
    
    Function will return pandas-dataframe with the following information:
        - iata
            (IATA-Code of the requested airport)
        - type
            (Arrival, Departure)
        - scheduled_time
            (Scheduled Arrival or Departure time)
        - revised_time
            (In case of delays. Advise: Don't use for now...')
        - terminal
            (Terminal where the flight arrives/departs)
        - aircraft
            (Type of aircraft)
        - airline
            (Name of airline)
        - typ. config.
            (Typical seat-configuration of the aircraft. In 2019 aircrafts used
             82.6% of their capacity)
    
    Take 82.6% of typ. config. to get an estimate for the passanger count.
    
Notes:
    revised_time is mostly NaN and might not work.

"""

# =============================================================================
# IMPORT LIBRARIES
# =============================================================================
import time
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
# --- Custom modules
from get_keys import get_keys
from get_citydata import get_geocoords


# =============================================================================
# GET INFORMATION ABOUT AIRCRAFTS (PASSENGER CAPACITY)
# =============================================================================
def get_aircraftinfo():
    print("Getting aircraft information...")
    # --- SCRAPE AXONAVIATION WEBSITE
    url = "http://www.axonaviation.com/commercial-aircraft/aircraft-data/aircraft-specifications"
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    print("Aircrafttable query successful.")
    aircrafttable = soup.find_all('table', class_='data-grid')[0].find_all('tr')
    # --- INITIALIZE DATAFRAME
    aircraftinfo = pd.DataFrame({
        'name':[],
        'max. config.':[],
        'typ. config.':[],
        'no. engines':[],
        'prim. operators':[]
    })
    # --- GO THROUGH TABLE-INFORMATION
    for i, model in enumerate(aircrafttable):
        if i==0:
            # Skip first row (=header)
            pass
        else:
            # Get aircraft-info from columns
            info = model.find_all('td')
            aircraftinfo.loc[i,'name'] = info[0].text
            aircraftinfo.loc[i,'max. config.'] = info[7].text
            aircraftinfo.loc[i,'typ. config.'] = info[8].text
            aircraftinfo.loc[i,'no. engines'] = info[9].text
            aircraftinfo.loc[i,'prim. operators'] = info[11].text
    # Convert number-values from string to numeric (might contain NaNs!)
    aircraftinfo['no. engines'] = aircraftinfo['no. engines'].astype(int)
    aircraftinfo['max. config.'] = pd.to_numeric(aircraftinfo['max. config.'],errors='coerce')
    aircraftinfo['typ. config.'] = pd.to_numeric(aircraftinfo['typ. config.'],errors='coerce')
    
    # Drop aircraft whose names end on 'F' as they are cargo aircraft
    aircraftinfo = aircraftinfo[aircraftinfo['name'].str[-1:]!='F']
    
    # Reset index (since the table is 1-indexed -> make 0-indexed again)
    aircraftinfo = aircraftinfo.reset_index(drop=True)
    
    # Return DataFrame with aircraft information
    return aircraftinfo



# =============================================================================
# GET PASSENGERS PER INDIVIDUAL FLIGHT
# =============================================================================
def get_flight_capacity(flights):
    print("Getting flight capacity...")
    # --- GET REFERENCE INFORMATION ABOUT AIRCRAFTS
    aircraftinfo = get_aircraftinfo()
    
    # --- GET ALL UNIQUE AIRCRAFT FROM CURRENT FLIGHTS
    f_aircrafts = pd.DataFrame(flights['aircraft'].drop_duplicates().reset_index(drop=True))
    
    # --- FUNCTION TO COMPARE AIRCRAFT NAMES
    def stringcompare(str1, str2):
        # Make both names lower to have case insensitive comparison
        str1 = str1.lower()
        str2 = str2.lower()
        # Count amount of equal characters
        countequal = sum(1 for c1, c2 in zip(str1, str2) if c1 == c2)
        if (countequal == 0):
            # In some cases countequal is zero
            # -> just output original stringlength in this case
            res = len(str1)
        else:
            # If strings are equal the result is zero
            res = abs(1-1.0*len(str1)/countequal)
        # Return result
        return res
    
    # --- GO THROUGH ALL UNIQUE AIRCRAFTS FROM CURRENT FLIGHTS
    for k, name in enumerate(f_aircrafts['aircraft']):
        # Initialize list for comparisons
        comp = []
        # --- GO THROUGH EACH ENTRY OF REFERENCE AIRCRAFT LIST
        for i in range(aircraftinfo.shape[0]):
            # Compare current aircraft name with entry
            # from reference-list and store comparison result
            comp.append(stringcompare(name, aircraftinfo.loc[i,'name']))
        # Get index of minimum entry
        ind = comp.index(min(comp))
        # --- CHECK SIMILARITY OF STRINGS
        if(min(comp)<0.5):
            # If difference between strings is small enough, store value
            f_aircrafts.loc[k,'typ. config.'] = aircraftinfo.loc[ind,'typ. config.']
        else:
            # If difference is too big, store NaN
            f_aircrafts.loc[k,'typ. config.'] = np.nan
    
    # Make sure flights-DF doesn't already have "typ. config."-column
    flights.drop(columns='typ. config.', inplace=True)
    # Add passenger configuration to flights-table
    flights = flights.merge(f_aircrafts,how='left',on='aircraft')
    
    # Return DataFrame with flights and passenger information
    return flights



# =============================================================================
# INITIALIZE DATAFRAME TO STORE FLIGHTS
# =============================================================================
def init_flights_df():
    flights = pd.DataFrame({
        'iata':[],
        'number':[],
        'type':[],
        'scheduled_time':[],
        'revised_time':[],
        'terminal':[],
        'aircraft':[],
        'airline':[],
        'typ. config.':[]
    })
    return flights


# =============================================================================
# GET AIRPORTS BY LOCATION
# =============================================================================
def get_airports(latitude,longitude):
    print("Getting airports by lat/lon coordinates...")
    radius = 75
    limit = 1

    list_for_df = []

    url = "https://aerodatabox.p.rapidapi.com/airports/search/location"

    querystring = {"lat":latitude,"lon":longitude,"radiusKm":radius,"limit":limit,"withFlightInfoOnly":"true"}
    
    headers = {
    	"X-RapidAPI-Key": get_keys('aeroboxdata'),
    	"X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        print(response)
    except:
        print("Error from AeroboxData.")

    list_for_df.append(pd.json_normalize(response.json()['items']))

    return pd.concat(list_for_df, ignore_index=True)


# =============================================================================
# GET FLIGHT INFORMATIONS FROM API
# =============================================================================
def get_flights(t0,t1,IATA_code):
    print("Getting flights-information...")
    # Source:
    # https://rapidapi.com/aedbx-aedbx/api/aerodatabox/
    API_key_aero = get_keys('aeroboxdata')

    # --- QUERY AERODATABOX API
    url = f"https://aerodatabox.p.rapidapi.com/flights/airports/iata/{IATA_code}/{t0}/{t1}"
    querystring = {"direction":"Both",
                   "withLeg":"false",
                   "withCodeshared":"true",
                   "withCargo":"false",
                   "withPrivate":"false"}
    headers = {
    	"X-RapidAPI-Key": API_key_aero,
    	"X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
    }
    print(f"Query flights for airport {IATA_code} at {t0}...")
    response = requests.get(url, headers=headers, params=querystring)
    print(response)
    
    # --- INITIALIZE DATAFRAME TO STORE FLIGHT INFO
    flights = init_flights_df()
    
    if(list(response.json().keys())[0]=="message"):
        print('\n---! API-Error !---\n')
        print(response.json())
    
    # --- GO THROUGH API-RESPONSE
    for flighttype in response.json().keys():
        # Select departures or arrivals
        L = response.json()[flighttype]
        # --- GO THROUGH INDIVIDUAL FLIGHTS
        for i in range(len(L)):
            # Store IATA_code (needed for requests with multiple airports)
            flights.loc[i,'iata'] = IATA_code
            # Type of flight (Arrival or Departure)
            flights.loc[i,'type'] = flighttype
            #
            flights.loc[i,'number'] = L[i]['number']
            # Scheduled time (for arrivals) in UTC (to match with weather data)
            flights.loc[i,'scheduled_time'] = L[i]['movement']['scheduledTime']['utc']
            # Revised time (for arrivals) in UTC (to match with weather data)
            if('revised_time' in L[i]['movement'].keys()):
                flights.loc[i,'revised_time'] = L[i]['movement']['revisedTime']['utc']
            # Terminal
            if('terminal' in L[i]['movement'].keys()):
                flights.loc[i,'terminal'] = L[i]['movement']['terminal']
            # Aircraft type
            if('aircraft' in L[i].keys()):
                flights.loc[i,'aircraft'] = L[i]['aircraft']['model']
            # Airline name
            flights.loc[i,'airline'] = L[i]['airline']['name']
    
    # Convert time-values to datetime-format
    flights['scheduled_time'] = pd.to_datetime(flights['scheduled_time'].str[:-1])
    flights['revised_time'] = pd.to_datetime(flights['revised_time'])
    
    # Return DataFrame of flights, also containing passenger capacity
    return get_flight_capacity(flights)



# =============================================================================
# GET FLIGHTSDATA FOR SPECIFIC TIMEFRAME - STARTING NOW
# =============================================================================
def get_flights_by_iata(IATA_code,timeframe):
    print("Getting flights per airport and timeframe...")
    # --- INITIALIZE EMPTY DATAFRAME
    flights = init_flights_df()
    
    # --- Max. query-duration for flights API is 12h
    timestep = 12
        
    # --- GO STEPWISE THROUGH REQUESTED TIMEFRAME
    # Example:
    # Timeframe is 27h: step0 12h, step1 24h, step3 27h
    for i in range( int(timeframe/timestep)+1):
        # Start Time
        t0 = datetime.now() + timedelta(hours = i*12)
        # Timedelta
        td = min(timestep,(timeframe - i*timestep))
        
        # Break if timedelta is zero
        if(td==0):
            break
        
        # End Time
        t1 = t0 + timedelta(hours = td) - timedelta(seconds=1)
        
        # Convert times to format needed by API
        t0 = t0.strftime("%Y-%m-%dT%H:%M")
        t1 = t1.strftime("%Y-%m-%dT%H:%M")
        
        # print(td)
        # print(t0)
        # print(t1)
        
        # Request and store results
        flights = pd.concat([flights, get_flights(t0, t1, IATA_code)])
    
    # Return DataFrame with all results
    return flights


# =============================================================================
# GET FLIGHTS BY CITY-NAME
# =============================================================================
def get_flights_by_city(city,timeframe):
    print("Getting flights per city and timeframe...")
    # Get latitude/longitude for city
    geocoords = get_geocoords(city)
    # Get airport list for lat/lon
    airports = get_airports(geocoords['latitude'], geocoords['longitude'])
    # Initialize empty DataFrame
    flights = init_flights_df()
    # --- GO THROUGH AIRPORT-LIST
    # Check if any airport was found
    if(airports.shape[0]>0):
        print(f"Found {airports.shape[0]} airport(s) for {city}.")
        for i,IATA_code in enumerate(airports['iata']):
            print(f"Get flights for {IATA_code}...")
            time.sleep(0.2)
            try:
                # Try to get flights-data for current IATA-code
                flights = pd.concat([flights, get_flights_by_iata(IATA_code,timeframe)])
                print(f"Check: {city} - {IATA_code}")
            except:
                # Sometimes IATA-codes don't work -> print error-msg
                print(f"Error occured: {city} - {IATA_code}")
    else:
        print(f"Did not find any airports for {city}!")
    # Append cityname-column
    flights['city'] = city
    # Return results
    return flights


# =============================================================================
# GET MULTIPLE FLIGHTS
# =============================================================================
def get_flightsdata(cities,timeframe=24):
    print("Get full flightsdata for city-list and timeframe...")
    # --- MAKE LIST IN CASE INPUT IS SINGLE CITY
    if(type(cities) is str):
        cities = [cities]
    # --- INITIALIZE EMPTY DATAFRAME
    flights = init_flights_df()
    # Append city-column
    flights['city'] = []
    # --- GO THROUGH ALL CITIES
    for city in cities:
        flights = pd.concat([flights, get_flights_by_city(city,timeframe)])
    # Return results
    return flights


# --- TESTING SINGLE
# get_flightsdata('Berlin',2)

# -- TESTING MULTI
# get_flightsdata(['Cologne','Munich'])
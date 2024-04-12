-- Drop the database if it already exists
# DROP DATABASE IF EXISTS gans;
-- Create the database
# CREATE DATABASE gans;
-- Use the database
USE gans;

-- CITIES
-- Stores city name, ID, country code and location
CREATE TABLE cities (
    city_id INT AUTO_INCREMENT, -- Automatically generated ID for each city (!!! Starts at "1")
    city VARCHAR(255) NOT NULL,
    country VARCHAR(255) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    PRIMARY KEY (city_id), -- Primary key to uniquely identify each city
    UNIQUE KEY (city)
);

-- POPULATION
-- Stores population per city and year
CREATE TABLE population (
    city_id INT NOT NULL,
    pyear INTEGER NOT NULL,
    population INTEGER NOT NULL,
    PRIMARY KEY(city_id, pyear),
    FOREIGN KEY (city_id) REFERENCES cities(city_id) -- Primary key to uniquely identify each city
);

-- WEATHER
-- Stores 5d/3h weather forecasts per city
CREATE TABLE weather (
    city_id INT NOT NULL,
    wtime DATETIME NOT NULL,
    weather_id INTEGER NOT NULL,
    rain FLOAT DEFAULT 0 ,
    rain_prob FLOAT DEFAULT 0,
    windspeed FLOAT DEFAULT 0,
    temp FLOAT NOT NULL,
    temp_feel FLOAT NOT NULL,
    temp_min FLOAT NOT NULL,
    temp_max FLOAT NOT NULL,
    vis FLOAT NOT NULL,
    PRIMARY KEY(city_id, wtime),
    FOREIGN KEY (city_id) REFERENCES cities(city_id) -- Primary key to uniquely identify each city
);

-- AIRPORTS
-- Stores airport IATA-Code and location
CREATE TABLE airports (
	city_id INT NOT NULL,
    iata CHAR(3) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    PRIMARY KEY (city_id, iata),
    FOREIGN KEY(city_id) REFERENCES cities(city_id),
	INDEX iata_index (iata)  -- Add an index on the 'iata' column
);

-- FLIGHTS
-- Stores flight information
CREATE TABLE flights (
    iata CHAR(3) NOT NULL,
    ftype VARCHAR(16) NOT NULL,
    fnumber VARCHAR(8) NOT NULL,
    scheduled_time DATETIME NOT NULL,
    revised_time DATETIME,
    terminal VARCHAR(8),
    aircraft VARCHAR(64),
    airline VARCHAR(64),
    typ_config INT DEFAULT 200, -- Median value of aircraft-config. in reference list
    PRIMARY KEY(iata, fnumber, scheduled_time),
    FOREIGN KEY(iata) REFERENCES airports(iata)
);

-- CUSTOMERLOAD
-- Stores modeled customerload
CREATE TABLE customerload (
	city_id INT NOT NULL,
    ltime DATETIME NOT NULL,
    flightload INT NOT NULL,
    baseload INT NOT NULL,
    weatherfac FLOAT,
    PRIMARY KEY (city_id, ltime),
    FOREIGN KEY (city_id) REFERENCES cities(city_id) -- Primary key to uniquely identify each city
);
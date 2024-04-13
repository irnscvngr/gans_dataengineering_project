# GANS Data Engineering Project

## Project Goal
This project was done as part of a data science bootcamp for a fictional company called "Gans".
Gans is a provider of electric scooters for rent.
For their business they want to know data about certain cities: population, weather-data and potential customers arriving via airplane.

So the task is to create an accessible database to provide them with up-to-date insights to these topics.
I personally expanded the goals of the project by also setting up a basic demand-"model" and an online-dashboard.

## Some results

Please follow this <a href="https://lookerstudio.google.com/reporting/d217368a-f033-457d-8f9d-307d04ae46d5">[Link]<a/> to find the interactive dashboard on Google Looker Studio!

<img src="Dashboard-01.png" width="500"> <img src="Dashboard-02.png" width="500">
<img src="Dashboard-03.png" width="500"> <img src="Dashboard-04.png" width="500">

## Project Setup

The project is split in distinct parts:
1. Gather population, weather and flights-data from online sources.
   Tools: Python, Pandas
2. Setup basic models on customerdemand (base demand, demand through aviation, influence of weather)
   Tools: Python, Pandas, Numpy
4. Setup local MySQL database and fill it with the gathered data.
   Tools: MySQL Workbench, Python, Pandas
5. Establish local data-pipeline on Google Cloud Platform.
   Tools: Google Cloud (GC) Functions, GC Run, GC SQL, GC Scheduler
6. Create online dashboard to visualize and analyze gathered data.
   Tools: Google Looker Studio.

### Google Cloud Platform

To provide easy accessability and automated updating of the database, the project is hosted on Google Cloud Platform (GCP).
Here, the data-gathering python code is executed daily and writes it's result to the online database.
See the GCP setup in the next image:

<img src="Flowdiagram_02.png" width="500">

### Data gathering with Pandas

The required data is gathered from different online-sources using the Pandas-library for Python among others.
Code related to the various types of data (cities, weather, flights, customer demand) is organized in individual *.py-files.
These functions are called from a main py-file that also contains the necessary code to make the project executable on GCP.
See the program setup in the next image:

<img src="Flowdiagram_01.png" width="700">

## Outcome and recap

The project setup successfully gathers the required data from various only sources and stores it to the database.
This happens automatically every day at 6am.
Beyond the "official" requirements this setup also features a simple load forecast based on city-, flight- and weatherdata as well as an online dashboard for visualization and analysis.
For further developments it is thinkable to improve the forecast model and to integrate more data-sources. This additional data could be about public transport (e.g. people arriving by train and potentially switching to a scooter) or public events like trade fairs or sport events.




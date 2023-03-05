# Educative.io Scraper / Educative.io Downloader

## An Automation tool built using python, selenium and chrome that scrapes Educative.io courses for offline use.

## To view the downloaded courses, use the [Educative-Viewer](https://github.com/anilabhadatta/educative-viewer) repository.

>    I Welcome anyone to contribute here in any form. Star and Fork my project 😊 Thanks.
    ***<h3 style="text-align: center;">Repo Version : 7.2 (latest) || Release Version 6.8</h3>***
>    Update 6.9: Added support for scraping a special type of quiz container (Mark Down Quiz) in the course.\
    Update 7.0: Fixed File name where "name" is not present in meta property og:title.\
    Update 7.1: Various bug fixes related to code containers and improvements.\
    Update 7.2: Added Chromedriver(v98) for Mac M1, use the chrome binary for osx - auto update disabled by default.

## How to use the Scraper?

 >   1. Create a text file and copy the urls of the first topic of any number of courses and paste it in the
         text file as shown below.

<img src="https://user-images.githubusercontent.com/48487849/162980989-0f128b3d-c969-4809-8553-2bc6791f34b8.png" width="820" height="300">
<img src="https://user-images.githubusercontent.com/48487849/197013915-1320da6b-d2c2-4239-b1f7-d95450f8fabb.png" width="820" height="180">

>    2. Run both the executables chromedriver and educative_scraper by downloading them from latest releases.\
      Note: If the executable release version is older than the current github repo version then run the
            project manually explained below.

>    3. Select a config if you don't want to use the default config "0" by pressing 2.\
        Note: Make sure to generate the config if it is selected for the first time.

>    4. Generate the config (if not created) and provide the urls text file path, save location and headless
         mode by pressing 1.
         
<img src="https://user-images.githubusercontent.com/48487849/197013987-e6bccbde-06b5-49de-851c-00575a3f8173.png" width="820" height="150">

 >   5. Login your educative account by pressing 3.
 >   6. Start Scraping by pressing 4.
 >   7. To return to Main Menu/ Exit Scraper press Ctrl+C / CMD+C.

>    Note 1: If the scraper fails or the User Exits in between for any specific reason, a log.txt file will be created in the save path, containing the index and last known url while scraping, copy the {index url} and replace it in the urls text file to resume scraping the course where it was stopped previously by restarting the scraper.

>    Make sure to delete the urls that are already scraped while replacing in the urls text file

<img src="https://user-images.githubusercontent.com/48487849/197014154-a7dbd7e4-d398-4076-b0e8-279d9841c8f9.png" width="820" height="300">

>    Note 2: If for any reason your system shuts down for power failure or the scraper crashes then you have to manually search the url and index and provide the {index url} in urls text file since the scraper cannot create log.txt for sudden power cut/ crash.

## To Run the project manually using git and python:

### Prerequisites:

      Git
      Python 3.9+
      OS: Win/Mac(Intel)/Linux(ARM/AMD) 64bit
      Replace the word "python3" with "python" and "pip3" with "pip" for Windows OS only.

### Step 1: Clone the repository and create a terminal inside the cloned directory and run the following commands.

### Step 2: Install the virtualenv package for python3 and create a virtual environment named "env".

      pip3 install virtualenv
      virtualenv env

### Step 3: Activate the virtual environment.

#### > (For Windows)

      env\Scripts\activate

#### > (For MacOS/Linux)

      source env/bin/activate

### Step 4: Install the required modules:

      pip3 install -r requirements.txt

### Step 5: Download, extract and paste the respective Chrome-bin for your OS from the latest releases section inside the Chrome-bin folder.

![img4](https://user-images.githubusercontent.com/48487849/197014188-3906af24-2297-48a6-9592-b669ac72af53.png)

### Step 6: Open up two terminals and run the following commands in separate terminals.

      python3 chromedriver.py
      python3 educative_scraper.py

### Step 7: Refer, **[How to use the Scraper?](#how-to-use-the-scraper)** explained above, except the 2nd point.

#### For Mac OS users only: Refer to [this Repository](https://github.com/anilabhadatta/enable-disable-chrome-updates) to Disable Chrome Updates. 

## (Optional) To Build the chromedriver and educative-scraper executables using pyinstaller:

#### Activate the Virtual Environment and Install the required modules for the project (Refer Step 2, 3, 4 above).

#### Install the pyinstaller package and run the following commands.

      pip3 install pyinstaller

#### > (For Windows)

      pyinstaller --clean --add-data Chrome-bin;Chrome-bin --onefile -i"icon.ico" educative_scraper.py
      pyinstaller --clean --add-data "Chrome-driver;Chrome-driver" --onefile -i"icon.ico" chromedriver.py

#### > (For MacOS/Linux)

      pyinstaller --clean --add-data Chrome-bin:Chrome-bin --onefile -i"icon.ico" educative_scraper.py
      pyinstaller --clean --add-data "Chrome-driver:Chrome-driver" --onefile -i"icon.ico" chromedriver.py

Pyinstaller command for Linux OS may or may not work due to a pyinstaller bug, currently checking for a fix.\
A Whitepaper will be released containing the explanation of each functions and the cases handled by the scraper.

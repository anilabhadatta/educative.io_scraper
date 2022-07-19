# Educative.io Scraper / Educative.io Downloader
## A Python script that downloads Educative.io courses for offline use using selenium.
## To view the downloaded courses, use the [Educative-Viewer](https://github.com/anilabhadatta/educative-viewer) repository.

I Welcome anyone to contribute to this project. A Star would help me a lot.\
Update 20/07/2022 : v5.3 Fixed and Added a feature to Code Widget type containers.\
Update 19/07/2022 : v5.2 Added SingleFile HTML page content instead of screenshot.\
Update 15/07/2022 : v5.0 Added support for Linux arm64 architecture.\
Update 07/07/2022 : v4.9 Fixed Multiple Bugs as educative.io made some changes in their DOM.

## How to use the Scraper?
      1. Create a urls text file and copy the links of the first topic of courses and paste it in text file as shown below.
      
![image](https://user-images.githubusercontent.com/48487849/162980989-0f128b3d-c969-4809-8553-2bc6791f34b8.png)
      
######   eg: url -> https://www.educative.io/courses/grokking-computer-networking/JQBKG47LlGg
      2. Run both the executables chromedriver and educative_scraper by downloading them from latest release.
      3. Select a config if you don't wish to use the default config "0" by pressing 2. 
      (Make sure to generate the config if it is selected for the first time)
      4. Generate the config (if not present) and provide the urls text file path, save location and headless mode by pressing 1.
      5. Login your educative account by pressing 3.
      6. Start Scraping by pressing 4.
      7. To return to Main Menu/ Exit Scraper press Ctrl+C / CMD+C.
      
#####   Note 1: Uncomment line 469 to download the courses having download_button container but download button not working.[This Feature is not added in releases]
#####   Note 2: If the scraper fails or the User Exits in between for any specific reason, a log.txt file will be created in the save directory, containing the last known url while scraping along with the index, copy the {index url} line and replace it in the original urls text file (make sure to delete the urls that are already scraped while replacing) to resume scraping the course where it was stopped previously by restarting the scraper.
#####   Note 3: If for any reason your system shuts down for power failure or the scraper crashes then you have to manually search the url and index and provide the {index url} in urls text file since the scraper cannot create log.txt for sudden power cut/ crash.      
      
## To Run the project manually:

### Step 1: Install the virtualenv package for python3 and create a virtual environment named "env".

      pip3 install virtualenv 
      virtualenv env 

### Step 2: Activate the environment.
#### > (For Windows) 
      
      env\Scripts\activate
      
#### > (For MacOS/Linux) 
      
      source env/bin/activate
      
### Step 3: Install the required modules:
      
      pip3 install -r requirements.txt
      
### Step 4: Download and paste the respective Chrome-bin for your OS from the latest releases section. 

### Step 5: Open up two terminals and run the following commands.
      python3 chromedriver.py
      python3 educative_scraper.py
      

### Step 6: Refer, "How to use the Scraper?" explained above.


## To Build the chromdriver and educative-scraper using pyinstaller:
      
#### Activate the Virtual Environment and Install the required modules for the project (Refer Step 1, 2, 3 above).

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

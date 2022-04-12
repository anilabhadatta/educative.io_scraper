# Educative.io Scraper / Educative.io Downloader
## A Python script that downloads Educative.io courses for offline use using selenium.

## How to use the Scraper?
      1. Create a text file and copy the links of the first topic of courses and paste it in text file.
      
![image](https://user-images.githubusercontent.com/48487849/162980989-0f128b3d-c969-4809-8553-2bc6791f34b8.png)
      
      eg: url -> https://www.educative.io/courses/grokking-computer-networking/JQBKG47LlGg
      2. Select a config if you don't wish to use the default config 0 by pressing 2. (Make sure to generate the config if the selected config is created for the first time)
      3. Generate the config (if not present) and provide the url text file path, save location and headless mode by pressing 1.
      4. Login your educative account by pressing 3.
      5. Start Scraping by pressing 4.
      
      Note 1: Uncomment line 403 to download the courses having download_button container but download button not working.[This Feature is not added in releases]
      Note 2: If you are using Multiprocessing release, use only 1 instance per machine since chromedriver may exit if the scraper stops and may hamper the secondary scraper.
      Note 3: If the scraper fails to scrap a url for any specific reason, a log.txt file will be automatically created in the save directory, copy the <index url> line and replace it in urls text file (make sure to delete the urls that are already scraped while replacing) to resume scraping the course by restarting the scraper.
      If for any reason your system shuts down for power failure then you have to manually search where the scraper stopped working and provide the <index url> in urls text file since the scraper cannot create log.txt for sudden power cut/ crash.
      To exit the scraper in between scraping, press Ctrl+C/ CMD+C (This will save the <index url> of the url being scraped at the moment) to return to main menu and press enter to exit
      
## To view the downloaded courses, use the [Educative-Viewer](https://github.com/anilabhadatta/educative-viewer) repository.
### Refer Step 4 if you are using Releases.
      Make sure you have xterm or uxterm or gnome-terminal installed in your Linux OS.
      
## To Run/Build this project:

### Step 1: Install the virtualenv package for python3 and create a virtual environment named "env".

      
      pip3 install virtualenv 
      virtualenv env 
      

### Step 2: Activate the environment.
#### > (For Windows) 
      
      env\Scripts\activate
      
#### > (For MacOS/Linux) 
      
      source env/bin/activate
      
### Step 3: Install the required modules and start the educative-scraper using the following commands:
      
      pip3 install -r requirements.txt
      
      > For Manual Chromedriver Loader
      python3 chromedriver.py
      python3 educative_scraper.py
      
      > For Auto Chromedriver Loader (Multiprocessing)
      python3 multiprocess.py
      

### Step 4: Create a config by entering 1 and provide the urls.txt file path and course-save folder path.


### Step 5 (Optional): To build the educative-viewer using pyinstaller:
      
#### Install the pyinstaller package and run the following commands.
      
      pip3 install pyinstaller
      
#### > (For Windows) 
      
      > For educative_scraper and chromedriver.py (Manual Chromedriver Loader)
      pyinstaller --clean --add-data Chrome-bin;Chrome-bin --onefile -i"icon.ico" educative_scraper.py
      pyinstaller --clean --add-data "Chrome-driver;Chrome-driver" --onefile -i"icon.ico" chromedriver.py
      
      > For multiprocess.py (Auto Chromedriver Loader)
      pyinstaller --clean --add-data "Chrome-driver;Chrome-driver" --add-data "./educative_scraper.py;./" --add-data "Chrome-bin;Chrome-bin" --add-data "env;env" --onefile -i"icon.ico" multiprocess.py
      
#### > (For MacOS/Linux) 
      
      > For educative_scraper and chromedriver.py (Manual Chromedriver Loader)
      pyinstaller --clean --add-data Chrome-bin:Chrome-bin --onefile -i"icon.ico" educative_scraper.py
      pyinstaller --clean --add-data "Chrome-driver:Chrome-driver" --onefile -i"icon.ico" chromedriver.py
      
      > For multiprocess.py (Auto Chromedriver Loader)
      pyinstaller --clean --add-data "Chrome-driver:Chrome-driver" --add-data "./educative_scraper.py:./" --add-data "Chrome-bin:Chrome-bin" --add-data "env:env" --onefile -i"icon.ico" multiprocess.py


Pyinstaller command for Linux OS may or may not work due to a pyinstaller bug, currently checking for a fix.

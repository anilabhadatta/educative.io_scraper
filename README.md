# Educative Scraper
## A Python script that scraps Educative.io courses using selenium.

## To view the scraped courses, use the [Educative-Viewer](https://github.com/anilabhadatta/educative-viewer) repository
### Refer Step 4 if you are using Releases.

## To Run/Build this project:

### Step 1: Install the virtualenv package for python3 and create a virtual environment

      
      pip3 install virtualenv 
      virtualenv env 
      

### Step 2: Activate the environment
#### > (For Windows) 
      
      env\Scripts\activate
      
#### > (For MacOS/Linux) 
      
      source env/bin/activate
      
### Step 3: Install the required modules and start the educative-scraper using the following commands:
      
      pip3 install -r requirements.txt
      python3 run.py
      

### Step 4: Create a config by entering 1 and provide the urls.txt file path and course-save folder path


### Step 5 (Optional): To build the educative-viewer using pyinstaller:
      Uncomment Line 54 and Comment Line 57,58 in run.py
#### Install the pyinstaller package and run the following commands
      
      pip3 install pyinstaller
      
#### > (For Windows) 
      
      pyinstaller --clean --add-data Chrome-bin;Chrome-bin --onefile -i"icon.ico" educative_scraper.py
      pyinstaller --clean --add-data "Chrome-driver;Chrome-driver" --add-data "./dist/educative_scraper.exe;./dist" --onefile -i"icon.ico" run.py
      
#### > (For MacOS/Linux) 
      
      pyinstaller --clean --add-data Chrome-bin:Chrome-bin --onefile -i"icon.ico" educative_scraper.py
      pyinstaller --clean --add-data "Chrome-driver:Chrome-driver" --add-data "./dist/educative_scraper:./dist" --onefile -i"icon.ico" run.py

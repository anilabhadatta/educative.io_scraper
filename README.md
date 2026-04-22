# Educative.io Scraper -- Educative.io Downloader

<pre><code style="white-space : pre-wrap !important;">Description: 
This tool effortlessly scrapes and saves Educative.io courses for offline use enabling you to
learn at your own pace, even without an internet connection.

Contributions:
I wholeheartedly welcome contributions from individuals in any capacity to enhance this project.
Thank you for your support!

Disclaimer:
I want to clarify that I am not accountable for any inappropriate use of this scraper. 
I developed it solely for research purposes and take no responsibility for its misuse.

Repository Version: v4.0.20 (Recommended)
Master Branch: v4-dev</code></pre>
```
Updates Information
1. New architecture introduced:
   - Topic content is now stored in the database and can be rendered in Educative Viewer v5.
   - The viewer renders each topic dynamically by component type, delivering an experience close to Educative.io.
2. V4 will maintain and provide fixes only for the API Scraper.
3. V3 will maintain and provide fixes for the Single File HTML-based Scraper.
```
###                                

## To view the downloaded courses, you can use the [Educative-Viewer V5](https://github.com/Biraj2004/educative-viewer) repository, which provides a better readability and user-friendly interface for accessing the downloaded course content.


## Steps to use the scraper:

-  ### Prerequisites:

```
Git
Python 3.12 or more
OS: Win(x86/x64) - Mac(ARM64/x64) - Linux(ARM64/x64)
```

-  ### Download & cd this project dir.

```
git clone https://github.com/anilabhadatta/educative.io_scraper.git
cd educative.io_scraper
   ```

-  ### Run the following commands to start Educative Scraper.
- #### Automatic Steps:
    - #### Use python3 instead of python for Linux and MacOS.
      ```
      python setup.py --install
      python setup.py --run
      
      [Commands]
      --install: Creates a virtual environment and installs the required dependencies.
      --run: Activates the environment and starts the scraper. [Default = True]
      --create: Creates a shortcut executable file linked to the scraper directory.
            
            If the git repository is moved to a different location after creating
            the executable then recreate it again to set the new repository path.
      ```


- #### Manual Steps:
    - #### Windows:
      ```
      pip install virtualenv
      python -m venv env <or> virtualenv env
      env\Scripts\activate
      pip install -r requirements.txt
      
      python EducativeScraper.py                 (For UI)
      python EducativeScraper.py --loginbrowser  (Open browser for login to account)
      python EducativeScraper.py --terminal      (For Terminal)
      python EducativeScraper.py --help          (For Config and Help info)
      ```
    - #### MacOS/Linux:
      ```
      pip3 install virtualenv
      python3 -m venv env <or> virtualenv env
      source env/bin/activate
      pip3 install -r requirements.txt
      
      python3 EducativeScraper.py                 (For UI)
      python3 EducativeScraper.py --loginbrowser  (Open browser for login to account)
      python3 EducativeScraper.py --terminal      (For Terminal)
      python3 EducativeScraper.py --help          (For Config and Help info)
      ```
    - #### Run the help command to learn about config setup for terminal based scraping before starting the scraper

      <div align="center">
         <figure>
            <img src="https://github.com/user-attachments/assets/c3c3168f-88c4-432d-94c5-2f9b9c919466" style="width: 50%; height:50%;">
            <br>
            <figcaption>Recommeded GUI Settings</figcaption>
         </figure>
      </div>


-  ### After the GUI successfully loads, please proceed to follow the subsequent steps.
    - Create a text file.
    - Copy the URLs of the first topic/lesson from any number of courses.
    - Paste all the URLs into the text file and save it.
      <div align="center">
       <br><img src="https://user-images.githubusercontent.com/48487849/162980989-0f128b3d-c969-4809-8553-2bc6791f34b8.png" style="width: 70%; height:50%;">
       <br>
         <figure><img src="https://user-images.githubusercontent.com/48487849/197013915-1320da6b-d2c2-4239-b1f7-d95450f8fabb.png" style="width: 70%; height:50%;"><br>
          <figcaption>Reference</figcaption>
         </figure>
      </div>


    - Select a configuration if you prefer not to use the default configuration.
    - If you prefer not to display the browser window, choose the `headless` option.
    - Please provide a unique `User Data Directory` name that the browser will use to store your current session. 
    - Please select the file path of the text file containing the course URLs, as well as the directory where you would
      like to save the database.
    - You can choose to save/export the current configuration for later use, or you can opt for the default
      configuration.
    - For the initial setup or updates, click on `Download Chromedriver` and `Download Chrome Binary` to automatically
      Download them into the project directory.
    - If you intend to utilize proxies, simply enable the proxy option and enter the proxy in the proxies box.
      <ul>
      <br>
        <li> For an IP authorized proxy, you can directly enter IP:PORT of the proxy.</li>
        <li> For USER:PASS authorized proxy, you'll need to create a localhost tunnel using the <a href="https://github.com/anilabhadatta/proxy-login-automator">Proxy-Login-Automator</a> repository.</li>
        <li> After setting up the tunnel, enter the IP:PORT of the localhost proxy that you configured in the Proxy Login Automator.</li>
        <br>
      </ul>
    - Click on `Login Account` to log in to your Educative.io account, and click on `Close Browser Button` to close the
      browser after the authentication is completed.
    - Click on `Start Scraper` to begin scraping the courses.
    - The scraper will automatically stop after scraping all the URLs in the selected text file.
    - For Projects, add the project link in the text file. Do not add the first topic link of the project.
    - Auto Resume Function will try to resume URL 3 times in case of any error before failing.
    - Auto Fix URL will automatically update the text file to remove any completed URLs to stop unnecessary rescraping.
    - DB stores each topic's scraping status to resume from leftovers. If Overwrite is needed, enable the Overwrite option.
    - Extract Assets - Run only if you want to extract the assets again. By default, the assets are already stored while scraping the topic.
    - Download Assets - The extracted Assets will be downloaded in the save directory. Contains Images/SVGs/Files.

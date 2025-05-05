import argparse
import ctypes
import platform
import shutil

from src.Utility.DownloadUtility import DownloadUtility
from src.Main.StartTerminalScraper import StartTerminalScraper
from src.Utility.ConfigUtility import ConfigUtility
from src.Common.Constants import constants
from src.UI.HomeScreenGUI import HomeScreen
from src.Utility.FileUtility import FileUtility


class EducativeScraper:
    def __init__(self, cmdArgs):
        
        print(f"""
                Educative Scraper ({version}), developed by Anilabha Datta
                Project Link: https://github.com/anilabhadatta/educative.io_scraper/
                Check out ReadMe for more information about this project.
                Use the GUI to start scraping.
        """)
        if platform.system() == "Windows":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EducativeScraper")
        self.fileUtil = FileUtility()
        self.loadBasicUtility()
        self.cmdArgs = cmdArgs
        self.configJson = None
        self.configUtil = ConfigUtility()


    def createDefaultConfigIfNotExists(self):
        if not self.fileUtil.checkIfFileExists(constants.defaultConfigPath):
            print(f"Creating default config file in {constants.defaultConfigPath}")
            shutil.copy(constants.commonConfigPath, constants.defaultConfigPath)


    def loadBasicUtility(self):
        self.fileUtil.createFolderIfNotExists(constants.OS_ROOT)
        self.createDefaultConfigIfNotExists()


    def run(self):
        if not any(vars(self.cmdArgs).values()):
            HomeScreen().createHomeScreen(version)
        else:
            self.loadDefaultConfig()
            if self.cmdArgs.terminal:
                StartTerminalScraper(self.configJson).startScraper()
            elif self.cmdArgs.dwldchromedriver:
                DownloadUtility().downloadChromeDriver(app=None, progressVar=None, configJson=self.configJson)
            elif self.cmdArgs.dwldchromebinary:
                DownloadUtility().downloadChromeBinary(app=None, progressVar=None, configJson=self.configJson)


    def loadDefaultConfig(self):
        self.config = self.configUtil.loadConfig()['ScraperConfig']
        self.configJson = {
            'userDataDir': self.config['userDataDir'],
            'headless': self.config['headless'],
            'courseUrlsFilePath': self.config['courseUrlsFilePath'],
            'saveDirectory': self.config['saveDirectory'],
            'logger': self.config['logger'],
            'moduleType': self.config['moduleType'],
            'isProxy': self.config['isProxy'],
            'proxy': self.config['proxy'],
            'scraperType': self.config["scraperType"],
            "scrapingMethod": self.config["scrapingMethod"],
            'fileType': self.config["fileType"],
            'ucdriver': self.config["ucdriver"],
            'binaryversion': self.config["binaryversion"],
            'autoresume': self.config["autoresume"],
            'autofixtextfile': self.config["autofixtextfile"],
            'blockscraper': self.config["blockscraper"],
            'autonext': self.config["autonext"],
            'useExtension': self.config["useExtension"]
        }



if __name__ == '__main__':
    version = "v3.9.6 Master Branch"
    helpDescription = f"""
                        Educative Scraper ({version}), developed by Anilabha Datta
                        Project Link: https://github.com/anilabhadatta/educative.io_scraper/
                        Check out ReadMe for more information about this project.
                        Use the GUI to start scraping.

                        Usage:
                        - Run with UI (default): Just run the script without arguments
                            > python EducativeScraper.py
                        
                        - Generate Default Config: Use --gendefaultconfig
                            > python EducativeScraper.py --gendefaultconfig

                        - Run Scraper in terminal mode: Use --terminal
                            > python EducativeScraper.py --terminal
                        
                        - Download chromedriver in terminal mode: Use --dwldchromedriver
                            > python EducativeScraper.py --dwldchromedriver

                        - Download chromebinary in terminal mode: Use --dwldchromebinary
                            > python EducativeScraper.py --dwldchromebinary    

                        Use --help to display this message.

                        For terminal users, configuration is controlled via the ScraperConfig file located at: {constants.defaultConfigPath}. 
                        
                        Below are the keys and their purposes:

                        [ScraperConfig]
                        - userdatadir         [IMP]: Directory for storing user profile data
                        - headless            [IMP]: Run browser in headless mode (True/False)
                        - courseurlsfilepath  [IMP]: Path to text file containing course URLs eg: C:/Users/<Username>/Desktop/urls.txt
                        - savedirectory       [IMP]: Folder to save scraped data eg: C:/Users/<Username>/Desktop
                        - scrapertype         [IMP]: Type of scraper to use
                                                     Options: Course-Topic-Scraper, All-Course-Urls-Text-File-Generator
                        - scrapingmethod      [IMP]: Method for scraping the course data
                                                     Options: SingleFile-HTML, Full-Page-Screenshot
                        - filetype            [IMP]: Format of output files
                                                     Options: html, html2pdf, png, png2pdf
                        - logger              [IMP]: Logging level
                                                     Options: DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET
                        - isproxy             [IMP]: Enable proxy usage (True/False)
                        - proxy               [IMP]: Proxy address (if isproxy is True)
                        - ucdriver            [IMP]: Use SeleniumBase Undetected Mode (True/False)
                        - binaryversion            : Browser version for the driver (e.g., 116)
                        - autoresume          [IMP]: Resume from where it stopped on last run (True/False)
                        - autofixtextfile     [IMP]: Automatically fix malformed input text files (True/False)
                        - blockscraper             : Block scraper execution temporarily (True/False)
                        - autonext                 : Auto-click next page on course listing (True/False)
                        - moduletype          [IMP]: Type of course module
                                                     Options: COURSE-PATH, CLOUDLAB, PROJECT
                        - useExtension             : Enable browser extension for login or scraping (True/False)
                        """
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description=helpDescription, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--terminal', action='store_true', help='Run the scraper in terminal mode instead of UI.')
    parser.add_argument('--dwldchromedriver', action='store_true', help='Download chromedriver in terminal mode instead of UI.')
    parser.add_argument('--dwldchromebinary', action='store_true', help='Download chromebinary in terminal mode instead of UI.')
    parser.add_argument('--gendefaultconfig', action='store_true', help='Generate default config in terminal mode instead of UI.')
    args = parser.parse_args()
    app = EducativeScraper(args)
    app.run()

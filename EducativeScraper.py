import argparse
import ctypes
import platform
import shutil

from src.Utility.Html2PdfConverter import Html2PdfConverter, PDFConverterConfig
from src.Utility.DownloadUtility import DownloadUtility
from src.Main.StartTerminalScraper import StartTerminalScraper
from src.Utility.ConfigUtility import ConfigUtility
from src.Common.Constants import constants
from src.UI.HomeScreenGUI import HomeScreen
from src.Utility.FileUtility import FileUtility
from src.Main.LoginAccount import LoginAccount


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
            terminalRunner = StartTerminalScraper(self.configJson)
            if self.cmdArgs.terminal or self.cmdArgs.autoscraper:
                terminalRunner.startAutoScraper()
            elif self.cmdArgs.extractanddownloadassets:
                terminalRunner.extractAndDownloadAssets()
            elif self.cmdArgs.extractassets:
                terminalRunner.extractAssets()
            elif self.cmdArgs.downloadassets:
                terminalRunner.downloadAssets()
            elif self.cmdArgs.convertmulticourses:
                config = PDFConverterConfig(self.configJson)
                converter = Html2PdfConverter(config)
                converter.convert_multiple_courses()
            elif self.cmdArgs.convertsinglefiles:
                config = PDFConverterConfig(self.configJson)
                converter = Html2PdfConverter(config)
                converter.convert_single_file(
                    file_path=r"path\to\file.html",
                    output_path=r"path\to\file.pdf"
                )
            elif self.cmdArgs.dwldchromedriver:
                DownloadUtility().downloadChromeDriver(app=None, progressVar=None, configJson=self.configJson)
            elif self.cmdArgs.dwldchromebinary:
                DownloadUtility().downloadChromeBinary(app=None, progressVar=None, configJson=self.configJson)
            elif self.cmdArgs.loginbrowser:
                LoginAccount().start(self.configJson)
                

    def loadDefaultConfig(self):
        self.config = self.configUtil.loadConfig()['ScraperConfig']
        self.configJson = {
            'userDataDir': self.config['userDataDir'],
            'headless': self.config.getboolean('headless', fallback=False),
            'courseUrlsFilePath': self.config['courseUrlsFilePath'],
            'saveDirectory': self.config['saveDirectory'],
            'logger': self.config['logger'],
            'moduleType': self.config['moduleType'],
            'isProxy': self.config.getboolean('isProxy', fallback=False),
            'proxy': self.config['proxy'],
            'scraperType': self.config["scraperType"],
            "scrapingMethod": self.config["scrapingMethod"],
            'fileType': self.config["fileType"],
            'ucdriver': self.config.getboolean("ucdriver", fallback=False),
            'binaryversion': self.config["binaryversion"],
            'autoresume': self.config.getboolean("autoresume", fallback=False),
            'autofixtextfile': self.config.getboolean("autofixtextfile", fallback=False),
            'blockscraper': self.config.getboolean("blockscraper", fallback=False),
            'autonext': self.config.getboolean("autonext", fallback=False),
            'overwrite': self.config.getboolean("overwrite", fallback=False),
            'downloadType': self.config.get("downloadType", fallback="PAL+COLLECTION"),
            'retryFailedUrls': self.config.getboolean("retryfailedurls", fallback=False),
            'useExtension': self.config.getboolean("useExtension", fallback=False)
        }



if __name__ == '__main__':
    version = "v4.0.33 Dev Branch"
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

                        - Run Auto Scraper in terminal mode: Use --autoscraper
                            > python EducativeScraper.py --autoscraper

                        - Extract static assets metadata (terminal): Use --extractassets
                            > python EducativeScraper.py --extractassets

                        - Download static assets from DB (terminal): Use --downloadassets
                            > python EducativeScraper.py --downloadassets

                        - Run extract + download static assets (terminal): Use --extractanddownloadassets
                            > python EducativeScraper.py --extractanddownloadassets
                        
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
                                                     Options: Course-Topic-Scraper, All-Course-Urls-Text-File-Generator, API-JSON-Scraper
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
    parser.add_argument('--autoscraper', action='store_true', help='Run the auto scraper in terminal mode (alias of --terminal).')
    parser.add_argument('--extractassets', action='store_true', help='Extract static assets into static_assets table from terminal.')
    parser.add_argument('--downloadassets', action='store_true', help='Download static assets listed in static_assets from terminal.')
    parser.add_argument('--extractanddownloadassets', action='store_true', help='Extract and then download static assets from terminal.')
    parser.add_argument('--convertmulticourses', action='store_true', help='Convert multiple HTML Courses to PDF in terminal mode.')
    parser.add_argument('--convertsinglefiles', action='store_true', help='Convert a single HTML file to PDF in terminal mode.')
    parser.add_argument('--dwldchromedriver', action='store_true', help='Download chromedriver in terminal mode instead of UI.')
    parser.add_argument('--dwldchromebinary', action='store_true', help='Download chromebinary in terminal mode instead of UI.')
    parser.add_argument('--gendefaultconfig', action='store_true', help='Generate default config in terminal mode instead of UI.')
    parser.add_argument('--loginbrowser', action='store_true', help='Login to browser in terminal mode instead of UI. Ctrl+C to exit.')
    args = parser.parse_args()
    app = EducativeScraper(args)
    app.run()

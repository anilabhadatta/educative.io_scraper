import ctypes
import platform

from src.Common.Constants import constants
from src.UI.HomeScreenGUI import HomeScreen
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.FileUtility import FileUtility


class EducativeScraper:
    def __init__(self):
        print("""
                Educative Scraper (version 3.0.6 Dev Branch), developed by Anilabha Datta
                Project Link: https://github.com/anilabhadatta/educative.io_scraper/tree/v3-dev
                Check out ReadMe for more information about this project.
                Use the GUI to start scraping.
        """)

        self.fileUtil = FileUtility()
        self.configUtil = ConfigUtility()
        self.loadBasicUtility()
        self.run()


    def loadBasicUtility(self):
        self.fileUtil.createFolderIfNotExists(constants.OS_ROOT)
        self.configUtil.createDefaultConfigIfNotExists()


    @staticmethod
    def run():
        HomeScreen().createHomeScreen()


if __name__ == '__main__':
    if platform.system() == "Windows":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EducativeScraper")
    app = EducativeScraper()

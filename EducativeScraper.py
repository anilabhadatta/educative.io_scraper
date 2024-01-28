import ctypes
import platform

from src.Common.Constants import constants
from src.UI.HomeScreenGUI import HomeScreen
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.FileUtility import FileUtility


class EducativeScraper:
    def __init__(self):
        self.version = "v3.3.5 Master Branch"
        print(f"""
                Educative Scraper ({self.version}), developed by Anilabha Datta
                Project Link: https://github.com/anilabhadatta/educative.io_scraper/tree/v3-dev
                Check out ReadMe for more information about this project.
                Use the GUI to start scraping.
        """)
        if platform.system() == "Windows":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EducativeScraper")
        self.fileUtil = FileUtility()
        self.configUtil = ConfigUtility()
        self.loadBasicUtility()


    def loadBasicUtility(self):
        self.fileUtil.createFolderIfNotExists(constants.OS_ROOT)
        self.configUtil.createDefaultConfigIfNotExists()


    def run(self):
        HomeScreen().createHomeScreen(self.version)


if __name__ == '__main__':
    app = EducativeScraper()
    app.run()

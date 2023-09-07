import ctypes
import platform

from src.Common.Constants import constants
from src.UI.HomeScreenGUI import HomeScreen
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.FileUtility import FileUtility


class EducativeScraper:
    def __init__(self):
        self.version = "v3.0.12 Dev Branch"
        print(f"""
                Educative Scraper ({self.version}), developed by Anilabha Datta
                Project Link: https://github.com/anilabhadatta/educative.io_scraper/tree/v3-dev
                Check out ReadMe for more information about this project.
                Use the GUI to start scraping.
        """)

        self.fileUtil = FileUtility()
        self.configUtil = ConfigUtility()


    def loadBasicUtility(self):
        self.fileUtil.createFolderIfNotExists(constants.OS_ROOT)
        self.configUtil.createDefaultConfigIfNotExists()


    def run(self):
        HomeScreen().createHomeScreen(self.version)


if __name__ == '__main__':
    if platform.system() == "Windows":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EducativeScraper")
    app = EducativeScraper()
    app.loadBasicUtility()
    app.run()

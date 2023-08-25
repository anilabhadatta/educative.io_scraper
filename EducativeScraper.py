import tkinter as tk

from src.Common.Constants import constants
from src.UI.HomeScreen import HomeScreen
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.FileUtility import FileUtility


class EducativeScraper:
    def __init__(self):
        print("Scraper initialized")

        self.fileUtil = FileUtility()
        self.configUtil = ConfigUtility()
        self.loadBasicUtility()
        self.root = tk.Tk()
        self.run()


    def loadBasicUtility(self):
        self.fileUtil.createFolderIfNotExists(constants.OS_ROOT)
        self.configUtil.createDefaultConfigIfNotExists()


    def run(self):
        HomeScreen(self.root).createHomeScreen()
        self.root.mainloop()


if __name__ == '__main__':
    # Create the Tkinter app
    app = EducativeScraper()

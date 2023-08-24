import os
import zipfile

import wget

from src.Common.Constants import constants
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class DownloadUtility:
    def __init__(self):
        self.configUtil = ConfigUtility()
        self.fileUtil = FileUtility()
        self.config = self.configUtil.loadConfig(constants.commonConfigPath)["DownloadUrls"]
        self.releaseUrl = self.config["release_url"]
        self.app = None
        self.progressVar = None
        self.osUtil = OSUtility()


    def downloadChromeDriver(self, app, progressVar):
        self.app = app
        self.progressVar = progressVar
        chromeDriverUrl = self.releaseUrl + self.config[constants.chromedriverConfigKey]
        chromeDriverOutputPath = os.path.join(constants.chromeDriverFolderPath, "ChromeDriver.zip")

        self.fileUtil.deleteFolderIfExists(os.path.join(constants.chromeDriverFolderPath, self.osUtil.getCurrentOS()))
        wget.download(chromeDriverUrl, out=chromeDriverOutputPath, bar=self.updateProgress)
        with zipfile.ZipFile(chromeDriverOutputPath, "r") as zip_ref:
            zip_ref.extractall(constants.chromeDriverFolderPath)
            print("Extraction completed.")

        self.fileUtil.deleteFileIfExists(chromeDriverOutputPath)


    def downloadChromeBinary(self, app, progressVar):
        self.app = app
        self.progressVar = progressVar
        chromeBinaryUrl = self.releaseUrl + self.config[constants.chromebinaryConfigKey]
        chromeBinaryOutputPath = os.path.join(constants.chromeBinaryFolderPath, "ChromeBinary.zip")

        self.fileUtil.deleteFolderIfExists(os.path.join(constants.chromeBinaryFolderPath, self.osUtil.getCurrentOS()))
        wget.download(chromeBinaryUrl, out=chromeBinaryOutputPath, bar=self.updateProgress)
        with zipfile.ZipFile(chromeBinaryOutputPath, "r") as zip_ref:
            zip_ref.extractall(constants.chromeBinaryFolderPath)
            print("Extraction completed.")

        self.fileUtil.deleteFileIfExists(chromeBinaryOutputPath)


    def updateProgress(self, current, total, width=80):
        percentage = (current / total) * 100
        self.progressVar.set(percentage)
        self.app.update_idletasks()

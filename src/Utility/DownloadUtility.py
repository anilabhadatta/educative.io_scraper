import os
import ssl
import zipfile

import wget

from src.Common.Constants import constants
from src.Logging.Logger import Logger
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility

ssl._create_default_https_context = ssl._create_unverified_context


class DownloadUtility:
    def __init__(self):
        self.logger = None
        self.configUtil = ConfigUtility()
        self.fileUtil = FileUtility()
        self.config = self.configUtil.loadConfig(constants.commonConfigPath)["DownloadUrls"]
        self.releaseUrl = self.config["release_url"]
        self.app = None
        self.progressVar = None
        self.osUtil = OSUtility()
        self.chromeDriverOSPath = os.path.join(constants.chromeDriverFolderPath, self.osUtil.getCurrentOS())
        self.chromeBinaryOSPath = os.path.join(constants.chromeBinaryFolderPath, self.osUtil.getCurrentOS())


    def downloadChromeDriver(self, app, progressVar, configJson):
        self.app = app
        self.progressVar = progressVar
        self.logger = Logger(configJson, "DownloadUtility").logger
        chromeDriverUrl = self.releaseUrl + self.config[constants.chromedriverConfigKey]
        chromeDriverOutputPath = os.path.join(constants.chromeDriverFolderPath, "ChromeDriver.zip")
        self.logger.debug(f"""  Downloading Chrome Driver..
                                URL: {chromeDriverUrl}
                                Output Path: {self.chromeDriverOSPath}
                                OS: {self.osUtil.getCurrentOS()}
                            """)

        self.fileUtil.deleteFolderIfExists(self.chromeDriverOSPath)
        wget.download(chromeDriverUrl, out=chromeDriverOutputPath, bar=self.updateProgress)
        self.logger.debug("Download Complete now Extracting...")
        with zipfile.ZipFile(chromeDriverOutputPath, "r") as zip_ref:
            zip_ref.extractall(constants.chromeDriverFolderPath)
            self.logger.debug("Extraction completed.")

        self.fileUtil.deleteFileIfExists(chromeDriverOutputPath)


    def downloadChromeBinary(self, app, progressVar, configJson):
        self.app = app
        self.progressVar = progressVar
        self.logger = Logger(configJson, "DownloadUtility").logger
        chromeBinaryUrl = self.releaseUrl + self.config[constants.chromebinaryConfigKey]
        chromeBinaryOutputPath = os.path.join(constants.chromeBinaryFolderPath, "ChromeBinary.zip")
        self.logger.debug(f"""  Downloading Chrome Binary..
                                URL: {chromeBinaryUrl}
                                Output Path: {self.chromeBinaryOSPath}
                                OS: {self.osUtil.getCurrentOS()}
                            """)

        self.fileUtil.deleteFolderIfExists(self.chromeBinaryOSPath)
        wget.download(chromeBinaryUrl, out=chromeBinaryOutputPath, bar=self.updateProgress)
        self.logger.debug("Download Complete now Extracting...")
        with zipfile.ZipFile(chromeBinaryOutputPath, "r") as zip_ref:
            zip_ref.extractall(constants.chromeBinaryFolderPath)
            self.logger.debug("Extraction completed.")

        self.fileUtil.deleteFileIfExists(chromeBinaryOutputPath)


    def updateProgress(self, current, total, width=80):
        percentage = (current / total) * 100
        self.progressVar.set(percentage)
        self.app.update_idletasks()

import json
import os
import shutil
import ssl
import subprocess
import zipfile
from urllib.parse import urljoin

import requests
import wget

from src.Common.Constants import constants
from src.Logging.Logger import Logger
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility

ssl._create_default_https_context = ssl._create_unverified_context


class DownloadUtility:
    def __init__(self):
        self.app = None
        self.progressVar = None
        self.logger = None
        self.configUtil = ConfigUtility()
        self.fileUtil = FileUtility()
        self.osUtil = OSUtility()
        self.config = self.configUtil.loadConfig(constants.commonConfigPath)["DownloadUrls"]
        # self.updateDownloadUrlsInConfig()


    def downloadChromeDriver(self, app, progressVar, configJson):
        self.app = app
        self.progressVar = progressVar
        self.logger = Logger(configJson, "DownloadUtility").logger
        self.logger.debug("downloadChromeDriver called...")
        chromeDriverUrl = self.config[constants.chromedriverConfigKey]
        self.fileUtil.deleteFolderIfExists(constants.chromeDriverFolderPath)
        self.fileUtil.createFolderIfNotExists(constants.chromeDriverFolderPath)
        chromeDriverOutputPath = os.path.join(constants.chromeDriverFolderPath, "ChromeDriver.zip")
        self.logger.info(f"""  Downloading Chrome Driver and Extracting..
                                URL: {chromeDriverUrl}
                                Output Path: {constants.chromeDriverFolderPath}
                                OS: {self.osUtil.getCurrentOS()}
                            """)

        wget.download(chromeDriverUrl, out=chromeDriverOutputPath, bar=self.updateProgress)
        self.logger.debug("Download Complete now Extracting...")
        with zipfile.ZipFile(chromeDriverOutputPath, "r") as zip_ref:
            zip_ref.extractall(constants.chromeDriverFolderPath)
            self.logger.info("Download and Extraction of Chromedriver completed.")

        self.fileUtil.deleteFileIfExists(chromeDriverOutputPath)
        if self.osUtil.getCurrentOS() != "win":
            self.logger.info("Changing Permissions of ChromeDriver...")
            subprocess.check_call(['chmod', '-R', '+x', constants.chromeDriverPath])
            subprocess.check_call(['chmod', 'u+x', constants.chromeDriverPath])
            self.logger.info("Permissions Changed.")
        shutil.copy2(constants.chromeDriverPath, constants.ucDriverPath)


    def downloadChromeBinary(self, app, progressVar, configJson):
        self.app = app
        self.progressVar = progressVar
        self.logger = Logger(configJson, "DownloadUtility").logger
        self.logger.debug("downloadChromeBinary called...")
        chromeBinaryUrl = self.config[constants.chromebinaryConfigKey]
        self.fileUtil.deleteFolderIfExists(constants.chromeBinaryFolderPath)
        self.fileUtil.createFolderIfNotExists(constants.chromeBinaryFolderPath)
        chromeBinaryOutputPath = os.path.join(constants.chromeBinaryFolderPath, "ChromeBinary.zip")
        self.logger.info(f"""  Downloading Chrome Binary and Extracting..
                                URL: {chromeBinaryUrl}
                                Output Path: {constants.chromeBinaryFolderPath}
                                OS: {self.osUtil.getCurrentOS()}
                            """)

        wget.download(chromeBinaryUrl, out=chromeBinaryOutputPath, bar=self.updateProgress)
        self.logger.debug("Download Complete now Extracting...")
        with zipfile.ZipFile(chromeBinaryOutputPath, "r") as zip_ref:
            zip_ref.extractall(constants.chromeBinaryFolderPath)
            self.logger.info("Download and Extraction of ChromeBinary completed.")

        self.fileUtil.deleteFileIfExists(chromeBinaryOutputPath)
        if self.osUtil.getCurrentOS() != "win":
            self.logger.info("Changing Permissions of ChromeBinary...")
            subprocess.check_call(['chmod', '-R', '+x', constants.chromeBinaryFolderPath])
            subprocess.check_call(['chmod', 'u+x', constants.chromeBinaryPath])
            self.logger.info("Permissions Changed.")


    def updateProgress(self, current, total, width=80):
        percentage = (current / total) * 100
        self.progressVar.set(percentage)
        self.app.update_idletasks()


    def updateDownloadUrlsInConfig(self):
        downloadApi = self.config["download-api"]
        apiResponse = requests.get(downloadApi)
        if apiResponse.status_code == 200 and "linux-arm64" not in self.osUtil.getCurrentOSConfigKey():
            baseDownloadUrl = json.loads(apiResponse.content)["channels"]["Stable"]["downloads"]["chrome"][0]["url"]
            baseDownloadUrl = '/'.join(baseDownloadUrl.split('/')[:-1])
            joinedChromeUrl = f"{self.osUtil.getCurrentOSConfigKey()}/{constants.chromebinaryConfigKey}.zip"
            joinedChromeDriverUrl = f"{self.osUtil.getCurrentOSConfigKey()}/{constants.chromedriverConfigKey}.zip"
            self.config[constants.chromebinaryConfigKey] = urljoin(baseDownloadUrl, joinedChromeUrl)
            self.config[constants.chromedriverConfigKey] = urljoin(baseDownloadUrl, joinedChromeDriverUrl)
            self.configUtil.updateConfig(self.config, "DownloadUrls", constants.commonConfigPath)

import configparser
import os

from src.Utility.OSUtility import OSUtility


class Constants:
    def __init__(self):
        self.OS_ROOT = os.path.join(os.path.expanduser('~'), 'EducativeScraper')
        self.ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        self.defaultConfigPath = os.path.join(self.OS_ROOT, 'config.ini')
        self.commonFolderPath = os.path.join(self.ROOT_DIR, 'src', 'Common')
        self.commonConfigPath = os.path.join(self.commonFolderPath, 'config.ini')
        self.osUtil = OSUtility()
        self.chromedriverConfigKey = "chromedriver-" + self.osUtil.getCurrentOSConfigKey()
        self.chromebinaryConfigKey = "chrome-" + self.osUtil.getCurrentOSConfigKey()
        self.chromeDriverFolderPath = os.path.join(self.ROOT_DIR, 'src', 'ChromeDrivers', self.osUtil.getCurrentOS())
        self.chromeBinaryFolderPath = os.path.join('.', 'src', 'ChromeBinary', self.osUtil.getCurrentOS())

        config = configparser.ConfigParser()
        config.read(self.commonConfigPath)
        self.chromeDriverSubFolderPath = config["ChromeDriverPath"][self.chromedriverConfigKey]
        chromeDriverPathSeparated = self.chromeDriverSubFolderPath.split("/")
        self.ucDriverSubFolderPath = os.path.sep.join(chromeDriverPathSeparated[:-1] + ["uc"+chromeDriverPathSeparated[-1]])
        self.chromeDriverPath = os.path.join(self.chromeDriverFolderPath, self.chromeDriverSubFolderPath)
        self.ucDriverPath = os.path.join(self.chromeDriverFolderPath, self.ucDriverSubFolderPath)
        self.chromeBinaryPath = os.path.join(self.chromeBinaryFolderPath,
                                             config["ChromeBinaryPath"][self.chromebinaryConfigKey])


constants = Constants()

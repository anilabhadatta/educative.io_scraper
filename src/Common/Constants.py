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
        self.chromeBinaryFolderPath = os.path.join(self.ROOT_DIR, 'src', 'ChromeBinary', self.osUtil.getCurrentOS())

        config = configparser.ConfigParser()
        config.read(self.commonConfigPath)
        self.chromeDriverPath = os.path.join(self.chromeDriverFolderPath,
                                             config["ChromeDriverPath"][self.chromedriverConfigKey])
        self.chromeBinaryPath = os.path.join(self.chromeBinaryFolderPath,
                                             config["ChromeBinaryPath"][self.chromebinaryConfigKey])


constants = Constants()

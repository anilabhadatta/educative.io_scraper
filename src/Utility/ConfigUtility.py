import configparser
import shutil

from src.Common.Constants import constants
from src.Utility.FileUtility import FileUtility


class ConfigUtility:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.fileUtil = FileUtility()


    def createDefaultConfigIfNotExists(self):
        print("Creating default config")

        if not self.fileUtil.checkIfFileExists(constants.defaultConfigPath):
            shutil.copy(constants.commonConfigPath, constants.defaultConfigPath)


    def loadConfig(self, path=constants.defaultConfigPath):
        self.config.read(path)
        return self.config


    def updateConfig(self, configJson, path=constants.defaultConfigPath):
        for key, value in configJson.items():
            self.config['ScraperConfig'][key] = str(value)
        with open(path, 'w') as configfile:
            self.config.write(configfile)

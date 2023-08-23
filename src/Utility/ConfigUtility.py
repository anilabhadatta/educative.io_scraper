import configparser
import os
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
            defaultConfigPath = os.path.join(constants.OS_ROOT, 'config.ini')
            commonConfigPath = os.path.join(constants.ROOT_DIR, 'src', 'Common', 'config.ini')
            print(constants.OS_ROOT, constants.ROOT_DIR, commonConfigPath)
            shutil.copy(commonConfigPath, defaultConfigPath)


    def loadConfig(self, path=constants.defaultConfigPath):
        self.config.read(path)
        return self.config['ScraperConfig']


    def updateConfig(self, configJson, path=constants.defaultConfigPath):
        for key, value in configJson.items():
            self.config['ScraperConfig'][key] = str(value)
        with open(path, 'w') as configfile:
            self.config.write(configfile)

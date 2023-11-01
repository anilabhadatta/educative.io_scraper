import configparser
import shutil

from src.Common.Constants import constants
from src.Utility.FileUtility import FileUtility


class ConfigUtility:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.fileUtil = FileUtility()


    def createDefaultConfigIfNotExists(self):
        if not self.fileUtil.checkIfFileExists(constants.defaultConfigPath):
            shutil.copy(constants.commonConfigPath, constants.defaultConfigPath)


    def loadConfig(self, path=constants.defaultConfigPath):
        if path is not constants.commonConfigPath and not self.checkKeys(path, "ScraperConfig"):
            print("ConfigUtility: Config file is corrupted. Replacing with default common config...")
            shutil.copy(constants.commonConfigPath, path)
        self.config = configparser.ConfigParser()
        self.config.read(path)
        return self.config


    def updateConfig(self, configJson, sectionName, path=constants.defaultConfigPath):
        for key, value in configJson.items():
            self.config[sectionName][key] = str(value)
        with open(path, 'w') as configfile:
            self.config.write(configfile)


    def checkKeys(self, path, sectionName):
        self.config = configparser.ConfigParser()
        self.config.read(path)
        configKeys = set(self.config.options(sectionName))
        defaultConfigParse = configparser.ConfigParser()
        defaultConfigParse.read(constants.commonConfigPath)
        defaultConfigKeys = set(defaultConfigParse.options(sectionName))
        return configKeys == defaultConfigKeys

import platform
import time

from src.Logging.Logger import Logger

class OSUtility:
    def __init__(self, configJson=None):
        self.currentOS = platform.system()
        self.architecture = platform.architecture()[0]
        self.machineType = platform.machine().lower()
        self.osSuffix = None
        if configJson:
            self.logger = Logger(configJson, "OSUtility").logger


    def getCurrentOSConfigKey(self):
        if self.currentOS == "Linux":
            if "aarch64" in self.machineType or "arm" in self.machineType:
                self.osSuffix = 'linux-arm64'
            elif "64" in self.architecture:
                self.osSuffix = 'linux64'
        elif self.currentOS == "Darwin":
            if "arm" in self.machineType:
                self.osSuffix = 'mac-arm64'
            elif "64" in self.architecture:
                self.osSuffix = 'mac-x64'
        elif self.currentOS == "Windows":
            if "64" in self.architecture:
                self.osSuffix = 'win64'
            elif "32" in self.architecture:
                self.osSuffix = 'win32'
        return self.osSuffix


    def getCurrentOS(self):
        if self.currentOS == "Darwin":
            self.osSuffix = 'mac'
        elif self.currentOS == "Linux":
            self.osSuffix = 'linux'
        elif self.currentOS == "Windows":
            self.osSuffix = 'win'
        return self.osSuffix


    def sleep(self, seconds):
        self.logger.info(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
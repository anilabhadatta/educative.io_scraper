import logging
import os


class Logger:
    def __init__(self, configJson, logName):
        self.configJson = configJson
        self.logFilePath = os.path.join(configJson["saveDirectory"], "EducativeScraper.log")
        self.logLevel = configJson["logger"]
        self.logger = logging.getLogger(logName)
        self.logger.setLevel(self.logLevel)
        self.setupHandlers()


    def setupHandlers(self):
        formatter = logging.Formatter(" %(asctime)s - %(levelname)s - %(name)s - %(message)s")

        if not any(isinstance(handler, logging.StreamHandler) for handler in self.logger.handlers):
            consoleHandler = logging.StreamHandler()
            consoleHandler.setFormatter(formatter)
            self.logger.addHandler(consoleHandler)

        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)

        if not any(isinstance(handler, logging.FileHandler) for handler in self.logger.handlers):
            fileHandler = logging.FileHandler(self.logFilePath)
            fileHandler.setFormatter(formatter)
            self.logger.addHandler(fileHandler)
        return self.logger

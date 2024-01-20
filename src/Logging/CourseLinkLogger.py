import logging
import os


class CourseLinkLogger:
    def __init__(self, configJson):
        self.configJson = configJson
        self.logFilePath = os.path.join(configJson["saveDirectory"], "AllCourseLinks.log")
        self.logger = logging.getLogger("CourseLinkLogger")
        self.logger.setLevel("INFO")
        self.setupHandlers()


    def setupHandlers(self):
        formatter = logging.Formatter("%(message)s")
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
        if not any(isinstance(handler, logging.FileHandler) for handler in self.logger.handlers):
            fileHandler = logging.FileHandler(self.logFilePath)
            fileHandler.setFormatter(formatter)
            self.logger.addHandler(fileHandler)
        return self.logger


    def loadDataFromLinkLogger(self):
        with open(self.logFilePath, 'r') as file:
            contents = [line.strip() for line in file.readlines()]
        return contents

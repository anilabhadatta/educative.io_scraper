import logging
import os
import hashlib
import platform

from src.Utility.FileUtility import FileUtility

if platform.system() == "Windows":
    os.system("")  # Enables ANSI escape codes in Windows terminal

class CustomColorFormatter(logging.Formatter):
    COLORS = [
        "\033[36m", # Cyan
        "\033[35m", # Magenta
        "\033[34m", # Blue
        "\033[96m", # Light Cyan
        "\033[95m", # Light Magenta
        "\033[94m", # Light Blue
        "\033[93m", # Light Yellow
    ]
    RESET = "\033[0m"
    GREEN = "\033[32m"
    WHITE = "\033[97m"
    YELLOW = "\033[33m"
    ORANGE = "\033[31m"
    LIGHT_PURPLE = "\033[95m"
    TEAL = "\033[38;5;45m"   # deep sky blue — contrasts clearly with magenta

    def format(self, record):
        message = str(record.msg)
        is_topic_complete = "Saved JSON for:" in message or "done. Progress:" in message
        is_topic_start = "Scraping Topic:" in message
        is_derived_api_url = "Derived course API URLs:" in message
        is_course_type = "Determined course type:" in message
        is_course_started = "Started Scraping from Text File URL:" in message
        # Use log level, not message text — logger.error() sets levelno, not the message string
        is_error = record.levelno >= logging.ERROR

        color_index = int(hashlib.md5(record.name.encode()).hexdigest(), 16) % len(self.COLORS)
        module_color = self.COLORS[color_index]

        # Generate the standard formatted line first
        result = super().format(record)

        # ERROR / CRITICAL always take priority — colour overrides everything else
        if is_error:
            return f"{self.ORANGE}{result}{self.RESET}"
        elif is_topic_complete:
            return f"{self.GREEN}{result}{self.RESET}"
        elif is_topic_start:
            return f"{self.WHITE}{result}{self.RESET}"
        elif is_derived_api_url:
            return f"{self.YELLOW}{result}{self.RESET}"
        elif is_course_type:
            return f"{self.TEAL}{result}{self.RESET}"
        elif is_course_started:
            return f"{self.LIGHT_PURPLE}{result}{self.RESET}"
        else:
            return f"{module_color}{result}{self.RESET}"

class Logger:
    def __init__(self, configJson, logName):
        self.configJson = configJson
        self.logFilePath = os.path.join(configJson.get("saveDirectory", ""), "EducativeScraper.log")
        self.logLevel = configJson.get("logger", "INFO")
        self.logger = logging.getLogger(logName)
        self.logger.setLevel(self.logLevel)
        self.fileUtils = FileUtility()
        self.setupHandlers()

    def setupHandlers(self):
        use_color = self.configJson.get("scraperType") == "API-JSON-Scraper"
        
        file_formatter = logging.Formatter(" %(asctime)s - %(levelname)s - %(name)s - %(message)s")
        if use_color:
            console_formatter = CustomColorFormatter(" %(asctime)s - %(levelname)s - %(name)s - %(message)s")
        else:
            console_formatter = file_formatter

        if not any(isinstance(handler, logging.StreamHandler) for handler in self.logger.handlers):
            consoleHandler = logging.StreamHandler()
            consoleHandler.setFormatter(console_formatter)
            self.logger.addHandler(consoleHandler)

        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
        
        if self.configJson.get("saveDirectory", "") != "":
            self.fileUtils.createFolderIfNotExists(self.configJson["saveDirectory"])
            if not any(isinstance(handler, logging.FileHandler) for handler in self.logger.handlers):
                fileHandler = logging.FileHandler(self.logFilePath, encoding='utf-8')
                fileHandler.setFormatter(file_formatter)
                self.logger.addHandler(fileHandler)
        return self.logger

import os
import sys


class Chromedriver:
    def __init__(self, chromeDriverPath):
        self.chromeDriverPath = chromeDriverPath


    def loadChromeDriver(self):
        try:
            os.system(self.chromeDriverPath)
            pass
        except KeyboardInterrupt:
            sys.exit()


if __name__ == '__main__':
    Chromedriver(sys.argv[1]).loadChromeDriver()

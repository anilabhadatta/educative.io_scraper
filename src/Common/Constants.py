import os


class Constants:
    def __init__(self):
        self.OS_ROOT = os.path.join(os.path.expanduser('~'), 'EducativeScraper')
        self.ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        self.defaultConfigPath = os.path.join(self.OS_ROOT, 'config.ini')


constants = Constants()

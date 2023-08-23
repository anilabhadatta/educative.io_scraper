from src.Common.Constants import constants
from src.UI.HomeScreen import HomeScreen
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.FileUtility import FileUtility

'''
class GenerateConfigFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.text_file_path = tk.StringVar()
        self.variable1_value = tk.StringVar()
        self.variable2_value = tk.StringVar()

        tk.Label(self, text="Text File Path:").pack()
        tk.Entry(self, textvariable=self.text_file_path).pack()
        tk.Label(self, text="Variable 1 Value:").pack()
        tk.Entry(self, textvariable=self.variable1_value).pack()
        tk.Label(self, text="Variable 2 Value:").pack()
        tk.Entry(self, textvariable=self.variable2_value).pack()

        tk.Button(self, text="Save Config", command=self.save_config).pack()


    def save_config(self):
        config = configparser.ConfigParser()
        config['ScraperConfig'] = {
            'Option1': 'False',
            'Option2': 'False',
            'TextFilePath': self.text_file_path.get(),
            'Variable1Value': self.variable1_value.get(),
            'Variable2Value': self.variable2_value.get()
        }

        with open('config.ini', 'w') as configfile:
            config.write(configfile)

        self.parent.load_config_values()
        self.parent.show_generate_config_frame(False)  # Hide the frame
'''


class EducativeScraper:
    def __init__(self):
        print("Scraper initialized")

        self.fileUtility = FileUtility()
        self.configUtility = ConfigUtility()
        self.loadBasicUtility()
        self.homeScreen = HomeScreen()
        self.run()


    def loadBasicUtility(self):
        self.fileUtility.createFolderIfNotExists(constants.OS_ROOT)
        self.configUtility.createDefaultConfigIfNotExists()


    def run(self):
        self.homeScreen.createHomeScreen()


if __name__ == '__main__':
    # Create the Tkinter app
    app = EducativeScraper()

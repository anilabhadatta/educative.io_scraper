import argparse
import os
import platform
import shutil
import subprocess


class Setup:
    def __init__(self, args):
        self.currentOS = platform.system()
        self.args = args
        self.command = None
        self.pythonPrefix = "python3" if self.currentOS != "Windows" else "python"
        self.pipPrefix = "pip3" if self.currentOS != "Windows" else "pip"
        self.rootDir = os.path.dirname(os.path.realpath(__file__))
        self.envPath = os.path.join(self.rootDir, "env")
        self.envActivation = "source env/bin/activate" if self.currentOS != "Windows" else r"env\Scripts\activate.bat"
        self.envActivationPath = os.path.join(self.rootDir, self.envActivation)
        self.educativeScraperFilePath = os.path.join(self.rootDir, "EducativeScraper.py")
        self.tempSetupFilePath = os.path.join(self.rootDir, "tempDir", "setup.py")
        self.tempDirPath = os.path.join(self.rootDir, "tempDir")
        self.iconRoot = os.path.join(self.rootDir, "src", "Common")


    def installDependencies(self):
        self.removeFolderIfExists(self.envPath)
        self.command = f"{self.pythonPrefix} -m venv env && {self.envActivationPath} && {self.pipPrefix} install -r requirements.txt && exit"
        subprocess.run(self.command, shell=True)


    def createExecutable(self):
        self.createFolderIfNotExists(self.tempDirPath)
        self.createTempExecutableSetupFile()
        self.getIconPath()
        self.command = f"{self.envActivationPath}  && pyinstaller --clean --noconfirm --onefile --console --icon {self.iconRoot} {self.tempSetupFilePath} && exit"
        subprocess.run(self.command, shell=True)
        self.removeFolderIfExists(self.tempDirPath)


    def runScraper(self):
        if os.path.isdir(self.envPath):
            self.command = f"{self.envActivationPath} && {self.pythonPrefix} {self.educativeScraperFilePath} && exit"
            subprocess.run(self.command, shell=True)
        else:
            print(f"Please run '{self.pythonPrefix} setup.py --install' first")


    def createTempExecutableSetupFile(self):
        with open(self.tempSetupFilePath, "w") as f:
            f.write(rf"""
import subprocess
command = rf"{self.envActivationPath} && {self.pythonPrefix} {self.educativeScraperFilePath} && exit"
subprocess.call(command, shell=True)
                    """)


    def getIconPath(self):
        self.iconRoot = os.path.join(self.iconRoot, "icon.png")
        if self.currentOS == "Windows":
            self.iconRoot = os.path.join(self.iconRoot, "icon.ico")


    def createFolderIfNotExists(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)


    def removeFolderIfExists(self, path):
        if os.path.isdir(path):
            shutil.rmtree(path)


    def generateAndExecuteCommand(self):
        if self.args.install:
            self.installDependencies()
        elif self.args.create:
            self.createExecutable()
        elif self.args.run:
            self.runScraper()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Educative Scraper Setup")
    parser.add_argument("--install", action='store_true', default=False, help="Install required dependencies")
    parser.add_argument("--run", action='store_true', default=True, help="Run the scraper")
    parser.add_argument("--create", action='store_true', default=False, help="Create an executable file of the scraper")
    args = parser.parse_args()
    setup = Setup(args)
    setup.generateAndExecuteCommand()

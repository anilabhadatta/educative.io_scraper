import argparse
import os
import platform
import shutil
import subprocess


class Setup:
    def __init__(self, args, rootDir):
        self.currentOS = platform.system()
        self.args = args
        self.command = None
        self.pythonPrefix = "python3" if self.currentOS != "Windows" else "python"
        self.pipPrefix = "pip3" if self.currentOS != "Windows" else "pip"
        self.envActivation = "source env/bin/activate" if self.currentOS != "Windows" else r"env\Scripts\activate.bat"
        self.rootDir = rootDir
        self.envPath = os.path.join(self.rootDir, "env")
        self.setupFilePath = os.path.join(self.rootDir, "setup.py")
        self.educativeScraperFilePath = os.path.join(self.rootDir, "EducativeScraper.py")


    @staticmethod
    def getDefaultLinuxTerminal():
        terminals = ['gnome-terminal', 'xfce4-terminal', 'konsole', 'xterm', 'lxterminal', 'mate-terminal', 'urxvt',
                     'alacritty', 'termite']

        for terminal in terminals:
            try:
                subprocess.run(['which', terminal], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
                return terminal
            except subprocess.CalledProcessError:
                pass
        return None


    def executeCommand(self):
        if self.currentOS == "Windows":
            subprocess.Popen(["start", "cmd", "/k", self.command], shell=True)
        else:
            if self.currentOS == "Darwin":
                subprocess.Popen(["open", "-a", "Terminal", self.command])
            elif self.currentOS == "Linux":
                subprocess.Popen([self.getDefaultLinuxTerminal(), "-e", self.command])


    def generateAndExecuteCommand(self):
        if self.args.install:
            self.removeEnvIfExists()
            self.command = f"{self.pythonPrefix} -m venv env"
            subprocess.run(self.command, shell=True)
            self.command = f"{self.envActivation} && {self.pipPrefix} install -r requirements.txt && {self.pythonPrefix} {self.educativeScraperFilePath} && exit"
            self.executeCommand()
        elif self.args.create:
            self.removeEnvIfExists()
            self.command = f"{self.pythonPrefix} -m venv env"
            subprocess.run(self.command, shell=True)
            self.command = f"{self.envActivation} && {self.pipPrefix} install -r requirements.txt && pyinstaller --noconfirm --onefile --console {self.setupFilePath} && exit"
            self.executeCommand()
        elif self.args.run:
            if self.checkEnvIfExists():
                self.command = f"{self.envActivation} && {self.pythonPrefix} {self.educativeScraperFilePath} && exit"
                self.executeCommand()
            else:
                print(f"Please run '{self.pythonPrefix} setup.py install' first")


    def checkEnvIfExists(self):
        if os.path.isdir(self.envPath):
            return True
        return False


    def removeEnvIfExists(self):
        if self.checkEnvIfExists():
            shutil.rmtree(self.envPath)


if __name__ == '__main__':
    rootDir = os.path.dirname(os.path.realpath(__file__))
    # for pyinstaller hardcode the project directory path
    # rootDir = r"C:\Users\user\Documents\GitHub\EducativeScraper"
    os.chdir(rootDir)
    parser = argparse.ArgumentParser(description="Educative Scraper Setup")
    parser.add_argument("--install", action='store_true', default=False, help="Install required dependencies")
    parser.add_argument("--run", action='store_true', default=True, help="Run the scraper")
    parser.add_argument("--create", action='store_true', default=False, help="Create an executable file of the scraper")
    args = parser.parse_args()
    setup = Setup(args, rootDir)
    setup.generateAndExecuteCommand()

import argparse
import os
import platform
import shutil
import subprocess
import sys

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


    def generate_exe(self):

        # Get folder path
        
        folder_path = f"{rootDir}"
        # Create virtual environment 
        
        envPath = os.path.join(rootDir, "env")
        envPath = f"{envPath}"
        subprocess.run([sys.executable, "-m", "venv", envPath])
        
        # Activate virtual environment
        activate_path = os.path.join(envPath, 'Scripts', 'activate.bat')
        subprocess.call(activate_path, shell=True)
        
        # Install packages, including pyinstaller
        requirements_path = os.path.join(rootDir, 'requirements.txt')
        subprocess.run([os.path.join(envPath, 'Scripts', 'python.exe'),
                    "-m", "pip", "install", "-r", requirements_path, "pyinstaller"])

        # Make executable folder
        executable_path = os.path.join(rootDir, "executable")
        os.mkdir(executable_path)
        
        # Copy icon
        icon_path = os.path.join(rootDir, "icon.ico")
        shutil.copy(icon_path, executable_path)
        
        # Make scraper.py
        scraper_py = os.path.join(executable_path, "scraper.py")
        with open(scraper_py, "w") as f:
            f.write(f"""
import os
import subprocess

script_path = r"{folder_path}"
os.chdir(script_path)
script_to_run = r'"{os.path.join(envPath, 'Scripts', 'python.exe')}" EducativeScraper.py'

subprocess.call(script_to_run, shell=True)
    """)
  
        # Run pyinstaller
        pyinstaller_path = os.path.join(envPath, 'Scripts', 'pyinstaller.exe')
        command = [pyinstaller_path, "--noconfirm", "--onefile", "--console", "--icon", "executable/icon.ico", "executable/scraper.py"]   
        subprocess.run(command)
    
        # Delete executable folder
        shutil.rmtree(executable_path)

        # Delete builder folder for exe
        build_path = os.path.join(rootDir, "build")
        shutil.rmtree(build_path)

        # Delete temp file
        temp_path = os.path.join(rootDir, "scraper.spec")
        os.remove(temp_path)  


    def generateAndExecuteCommand(self):
        if self.args.install:
            self.removeEnvIfExists()
            self.command = f"{self.pythonPrefix} -m venv env"
            subprocess.run(self.command, shell=True)
            self.command = f"{self.envActivation} && {self.pipPrefix} install -r requirements.txt && {self.pythonPrefix} {self.educativeScraperFilePath} && exit"
            self.executeCommand()
        elif self.args.create:
            self.removeEnvIfExists()
            self.generate_exe()
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

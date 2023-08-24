import subprocess
import sys

from src.Common.Constants import constants


class StartChromedriver:
    def __init__(self):
        self.currentOS = sys.platform
        self.linuxTerminal = None


    def getDefaultTerminal(self):
        terminals = ['gnome-terminal', 'xfce4-terminal', 'konsole', 'xterm', 'lxterminal', 'mate-terminal', 'urxvt',
                     'alacritty', 'termite']

        for terminal in terminals:
            try:
                subprocess.run(['which', terminal], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
                self.linuxTerminal = terminal
            except subprocess.CalledProcessError:
                pass


    def loadChromeDriver(self):
        if self.currentOS.startswith('win32') or self.currentOS.startswith('cygwin'):
            subprocess.Popen(
                ["start", "cmd", "/k", constants.chromeDriverPath], shell=True)
        else:
            subprocess.check_call(['chmod', 'u+x', constants.chromeDriverPath])
            if self.currentOS.startswith('darwin'):
                subprocess.Popen(["open", "-a", "Terminal", constants.chromeDriverPath])
            elif self.currentOS.startswith('linux'):
                self.getDefaultTerminal()
                subprocess.Popen([self.linuxTerminal, "-e", constants.chromeDriverPath])

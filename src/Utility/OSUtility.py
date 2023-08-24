import platform
import sys


class OSUtility:
    def __init__(self):
        self.currentOS = sys.platform


    def getCurrentOSConfigKey(self):
        if self.currentOS.startswith('darwin'):
            if platform.machine() == 'x86_64':
                osSuffix = r'mac_x86_64'
            else:
                osSuffix = r'mac_arm64'
        elif self.currentOS.startswith('linux'):
            if platform.machine() == 'aarch64':
                osSuffix = r'linux_arm64'
            else:
                osSuffix = 'linux_amd64'
        else:
            osSuffix = 'win'
        return osSuffix


    def getCurrentOS(self):
        if self.currentOS.startswith('darwin'):
            osSuffix = 'mac'
        elif self.currentOS.startswith('linux'):
            osSuffix = 'linux'
        else:
            osSuffix = 'win'
        return osSuffix

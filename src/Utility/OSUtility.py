import platform


class OSUtility:
    def __init__(self):
        self.currentOS = platform.system()
        self.architecture = platform.architecture()[0]
        self.machineType = platform.machine().lower()
        self.osSuffix = None


    def getCurrentOSConfigKey(self):
        if self.currentOS == "Linux":
            if "aarch64" in self.machineType or "arm" in self.machineType:
                self.osSuffix = 'linux_arm64'
            elif "64" in self.architecture:
                self.osSuffix = 'linux_x64'
        elif self.currentOS == "Darwin":
            if "arm" in self.machineType:
                self.osSuffix = 'mac_arm64'
            elif "64" in self.architecture:
                self.osSuffix = 'mac_x64'
        elif self.currentOS == "Windows":
            if "64" in self.architecture:
                self.osSuffix = 'win_x64'
            elif "32" in self.architecture:
                self.osSuffix = 'win_x86'
        return self.osSuffix


    def getCurrentOS(self):
        if self.currentOS == "Darwin":
            self.osSuffix = 'mac'
        elif self.currentOS == "Linux":
            self.osSuffix = 'linux'
        elif self.currentOS == "Windows":
            self.osSuffix = 'win'
        return self.osSuffix

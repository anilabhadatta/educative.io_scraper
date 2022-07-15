import sys
import os
import platform

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_binary_path():
    current_os = sys.platform
    if current_os.startswith('darwin'):
        chromedriver = r'mac/chromedriver'
    elif current_os.startswith('linux'):
        if platform.machine() == 'aarch64':
             chromedriver = r'linux_arm64/chromedriver'
        else:
             chromedriver = r'linux_amd64/chromedriver'
    elif current_os.startswith('win32') or current_os.startswith('cygwin'):
        chromedriver = r'win\chromedriver.exe'
    return chromedriver


def load_chromedriver():
    try:
        chromedriver = get_binary_path()
        chromedriver_path = os.path.join(
            ROOT_DIR, "Chrome-driver", chromedriver)
        os.system(chromedriver_path)
    except KeyboardInterrupt:
        sys.exit()


if __name__ == '__main__':
    load_chromedriver()

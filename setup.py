import tkinter as tk
from tkinter import filedialog
import subprocess
import os
import sys
import shutil

# GUI setup
root = tk.Tk()
root.title("Executable Generator")  

folder_path_label = tk.Label(root, text="Select Folder Containing EducativeScraper.py:")
folder_path_entry = tk.Entry(root)


message = tk.Label(root, text="")

# Select folder dialog
def select_folder():
    folder_path = filedialog.askdirectory()
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, folder_path)
    
# Generate exe    
def generate_exe():

    # Get folder path
    folder_path = folder_path_entry.get()  

    # Create virtual environment 
    venv_name = 'myenv'
    venv_path = os.path.join(folder_path, venv_name)
    subprocess.run([sys.executable, "-m", "venv", venv_path])
    
    # Activate virtual environment
    activate_path = os.path.join(venv_path, 'Scripts', 'activate.bat')
    subprocess.call(activate_path, shell=True)
    
    # Install packages, including pyinstaller
    requirements_path = os.path.join(folder_path, 'requirements.txt')
    subprocess.run([os.path.join(venv_path, 'Scripts', 'python.exe'),
                   "-m", "pip", "install", "-r", requirements_path, "pyinstaller"])

    # Make executable folder
    executable_path = os.path.join(folder_path, "executable")
    os.mkdir(executable_path)
    
    # Copy icon
    icon_path = os.path.join(folder_path, "icon.ico")
    shutil.copy(icon_path, executable_path)
    
    # Make scraper.py
    scraper_py = os.path.join(executable_path, "scraper.py")
    with open(scraper_py, "w") as f:
        f.write(f"""
import os
import subprocess

script_path = r'{folder_path}'

os.chdir(script_path)

script_to_run = r'{os.path.join(venv_path, 'Scripts', 'python.exe')} EducativeScraper.py'

subprocess.call(script_to_run, shell=True)
""")
  
    # Run pyinstaller
    pyinstaller_path = os.path.join(venv_path, 'Scripts', 'pyinstaller.exe')
    command = [pyinstaller_path, "--noconfirm", "--onefile", "--console", "--icon", "executable/icon.ico", "executable/scraper.py"]   
    subprocess.run(command)
    
    # Delete executable folder
    shutil.rmtree(executable_path)
    
    message.config(text="Executable generated! Will find it in dist folder")



folder_select_button = tk.Button(root, text="Select Folder", command=select_folder)

generate_button = tk.Button(root, text="Generate", command=generate_exe)
# Layout
folder_path_label.pack()
folder_path_entry.pack()
folder_select_button.pack()  

generate_button.pack(pady=10)
message.pack()

root.mainloop()
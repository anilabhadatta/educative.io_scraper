from time import sleep
from selenium.webdriver.common.by import By
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from slugify import slugify
import glob
import zipfile
import json
import sys

OS_ROOT = os.path.expanduser('~')
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    config_path = os.path.join(OS_ROOT, ".educative")
    if ".educative" not in os.listdir(OS_ROOT) or "config.json" not in os.listdir(config_path):
        raise Exception("No config found, Please create one")
    with open(os.path.join(config_path, "config.json"), "r") as config_file:
        config = json.load(config_file)
    if "url_file_path" not in config or "save_path" not in config:
        raise Exception("Config is corrupted, Please recreate the config")
    url_text_file = config["url_file_path"]
    save_path = config["save_path"]
    return url_text_file, save_path


def load_chrome_driver(headless=True):
    chrome_path, chromedriver = get_binary_path()
    user_data_dir = os.path.join(OS_ROOT, ".educative", "User Data")
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('headless')
    options.add_argument(f'user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')
    options.add_argument("--start-maximized")
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--log-level=3')
    userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.56 Safari/537.36"
    options.add_argument(f'user-agent={userAgent}')
    options.binary_location = os.path.join(ROOT_DIR, "Chrome-bin", chrome_path)
    driver = webdriver.Chrome(service=ChromeService(
        os.path.join(ROOT_DIR, "Chrome-bin", chromedriver)), options=options)
    driver.set_window_size(1920, 1080)
    driver.command_executor._commands["send_command"] = (
        "POST", '/session/$sessionId/chromium/send_command')
    print("Driver Loaded")
    return driver


def create_course_folder(driver, url):
    print("Create Course Folder Function")
    course_name_class = "mb-4 px-6"
    if "educative.io/page" in url:
        course_name = get_file_name(driver)
    else:
        course_name = slugify(driver.find_element(
            By.CSS_SELECTOR, f"h4[class='{course_name_class}']").get_attribute('innerHTML')).replace("-", " ")
    if course_name not in os.listdir():
        print("Created a folder")
        os.mkdir(course_name)
    os.chdir(course_name)
    print("Inside Course Folder")


def next_page(driver):
    print("Next Page Function")
    next_page_class = "outlined-primary m-0"

    if not driver.find_elements(By.CSS_SELECTOR, f"button[class*='{next_page_class}']"):
        return False
    base_js_cmd = f'''document.getElementsByClassName("{next_page_class}")[0]'''
    check_next_module = driver.execute_script(
        '''return ''' + base_js_cmd + '''.innerHTML.slice(0,11);''')
    if check_next_module == "Next Module":
        return False
    driver.execute_script(base_js_cmd + '''.click()''')
    print("Next Page")
    return True


def open_slides(driver):
    print("Finding Slides Function")
    slidebox_class = "text-center block"
    menubar_class = "styles__ButtonsWrap"
    button_class = "Button-sc"
    action = ActionChains(driver)

    total_slides = driver.find_elements(
        By.CSS_SELECTOR, f"div[class*='{slidebox_class}']")
    if total_slides:
        for slide in total_slides:
            slide = slide.find_elements(
                By.CSS_SELECTOR, f"div[class*='{menubar_class}']")
            if slide:
                slide_button = slide[0].find_elements(
                    By.CSS_SELECTOR, f"button[class*='{button_class}']")[-2]
                action.move_to_element(slide_button).click().perform()
                sleep(1)
                print("Slides opened")
        sleep(10)
    else:
        print("No Slides Found")


def get_file_name(driver):
    print("Getting File Name")

    file_name = driver.find_elements(
        By.XPATH, "//h1[text()]") or driver.find_elements(
        By.XPATH, "//h2[text()]")
    print("File Name Found")
    return slugify(file_name[0].get_attribute('innerHTML'))


def delete_node(driver, node):
    driver.execute_script(f"""
                            var element = document.querySelector("{node}");
                            if (element)
                                element.parentNode.removeChild(element);
                            """)
    sleep(1)


def get_current_height(driver):
    return driver.execute_script('return document.body.parentNode.scrollHeight')


def increase_window_size(driver):
    driver.execute_script(f"window.scrollTo(0,{get_current_height(driver)})")
    sleep(2)
    driver.set_window_size(1920, get_current_height(driver))
    sleep(2)
    driver.set_window_size(1920, get_current_height(driver))
    sleep(2)


def create_html(file_name, base_64_png):
    with open(file_name + ".html", "w+") as fh:
        fh.write(f'''
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <title>{file_name}</title>
                </head>
                <body style="zoom: 80%">
                    <div style="text-align: center">
                        <img src="data:image/png;base64,{base_64_png}" alt="">
                    </div>
                </body>
                </html>
            ''')
    sleep(1)


def take_screenshot(driver, file_name):
    print("Take Screenshot Function")
    article_page_class = "ArticlePage"
    page_class = "Page"
    second_page_class = "PageContent"
    main_class = "ed-grid"
    nav_node = f"div[class*='{main_class}'] > nav"

    delete_node(driver, nav_node)
    increase_window_size(driver)

    base_64_png_ele = driver.find_element(
        By.CSS_SELECTOR, f"div[class*='{article_page_class}']").find_element(By.CSS_SELECTOR, f"div[class*='{page_class}']")
    base_64_png_ele_2 = base_64_png_ele.find_elements(
        By.CSS_SELECTOR, f"div[class*='{second_page_class}']")
    if base_64_png_ele_2:
        base_64_png = base_64_png_ele_2[0].screenshot_as_base64
    else:
        base_64_png = base_64_png_ele.screenshot_as_base64
    sleep(2)
    create_html(file_name, base_64_png)
    driver.set_window_size(1920, 1080)
    print("Screenshot taken and HTML File generated")


def show_hints_answer(driver):
    print("Show Hints Function")
    hints_div_class = "styles__Viewer"
    action = ActionChains(driver)

    hints_list = driver.find_elements(
        By.CSS_SELECTOR, f"div[class*='{hints_div_class}'] > button")
    if hints_list:
        for hints in hints_list:
            action.move_to_element(hints).click().perform()
            sleep(1)
        print("Show Hints Complete")
    else:
        print("No hints found")


def show_code_box_answer(driver):
    print("Show Codebox Answers Function")
    sol1 = "solution"
    sol2 = "show solution"
    show_solution_class = "popover-content"
    action = ActionChains(driver)

    answer_list = driver.find_elements(By.CSS_SELECTOR,
                                       f'button[aria-label="{sol1}"]') + driver.find_elements(By.CSS_SELECTOR, f'button[aria-label="{sol2}"]')
    if answer_list:
        for answer in answer_list:
            action.move_to_element(answer).click().perform()
            sleep(1)
            show_solution_button = driver.find_element(
                By.CSS_SELECTOR, f"div[class*='{show_solution_class}'] > button")
            action.move_to_element(show_solution_button).click().perform()
            sleep(1)
        print("Show Codebox Answers Complete")
    else:
        print("No Codebox answers found")


def create_temp_textarea(driver):
    driver.execute_script('''
        var div = document.querySelector('div[class*="ArticlePage"]');
                var input = document.createElement("textarea");
                input.name = "temptextarea";
                input.className = "temptextarea";
                input.maxLength = "10000";
                input.cols = "50";
                input.rows = "10";
                div.prepend(input);
    ''')
    sleep(1)


def create_folder(folder_name):
    if folder_name not in os.listdir():
        os.mkdir(folder_name)
    os.chdir(folder_name)


def download_parameters_for_chrome_headless(driver):
    params = {'cmd': 'Page.setDownloadBehavior', 'params': {
        'behavior': 'allow', 'downloadPath': os.getcwd()}}
    driver.execute("send_command", params)


def code_container_download_type(driver):
    print("Code Container Download Type Function")
    code_container_class = "styles__Spa_Container"
    svg_class = "w-7 h-7"
    action = ActionChains(driver)

    code_containers = driver.find_elements(
        By.CSS_SELECTOR, f"div[class*='{code_container_class}']")
    if code_containers:
        code_directory_path = os.getcwd()
        for folder_index, code in enumerate(code_containers):
            create_folder("code_downloaded" + str(folder_index))
            download_parameters_for_chrome_headless(driver)
            svg_buttons = code.find_elements(
                By.CSS_SELECTOR, f"svg[class*='{svg_class}']")
            if svg_buttons:
                action.move_to_element(svg_buttons[-1]).click().perform()
                sleep(2)
                print("Downloaded Zip File")
            else:
                print("Zip File not Downloaded")
            os.chdir(code_directory_path)
    else:
        print("No Code Container Downloadable Type found")


def copy_code(container, driver, use_svg=True):
    clipboard_title = "Copy To Clipboard"
    action = ActionChains(driver)
    sleep(1)

    if use_svg:
        svg_button = container.find_elements(
            By.CSS_SELECTOR, f"svg[title='{clipboard_title}']")[0]
    else:
        svg_button = container.find_elements(
            By.CSS_SELECTOR, f"button[title='{clipboard_title}']")[0]
    print("Clicked on Clipboard")
    action.move_to_element(svg_button).click().perform()
    sleep(1)
    textbox = driver.find_element(
        By.CSS_SELECTOR, "textarea[class*='temptextarea']")
    action.move_to_element(textbox).click().perform()
    sleep(1)
    textbox.send_keys(Keys.CONTROL, "a")
    textbox.send_keys(Keys.CONTROL, "v")
    print("Paste complete")
    sleep(1)
    return textbox.get_attribute('value')


def write_code(file_name, content):
    with open(file_name + ".txt", 'w', encoding='utf-8') as f:
        f.write(content)


def iterate_nav_bar(code, code_nav_bar, code_nav_tab, driver):
    print('Inside iterate_nav_bar function')
    nav_bar_tabs_class = "styles__TabTitle"

    nav_bar_tabs = code_nav_bar.find_elements(
        By.CSS_SELECTOR, f"span[class*='{nav_bar_tabs_class}']")
    for idx, _ in enumerate(nav_bar_tabs):
        driver.execute_script(f'''
            return document.querySelectorAll("span[class*='{nav_bar_tabs_class}']")[{idx}].click();
        ''')
        sleep(1)
        print("Clicked on Tab")
        nav_bar_file_name = driver.execute_script(f'''
            return document.querySelectorAll("span[class*='{nav_bar_tabs_class}']")[{idx}].textContent;
        ''')
        if code_nav_tab:
            iterate_nav_tab(code, code_nav_tab, driver, nav_bar_file_name)
        else:
            try:
                returned_code = copy_code(code, driver)
                write_code(nav_bar_file_name, returned_code)
            except Exception as e:
                print(e)
                print("Failed to write")


def iterate_nav_tab(code, code_nav_tab, driver, nav_bar_file_name=""):
    print("Inside iterate_nav_tab function")
    action = ActionChains(driver)

    for idx, tab in enumerate(code_nav_tab):
        action.move_to_element(tab).click().perform()
        sleep(1)
        try:
            returned_code = copy_code(code, driver)
            file_name = nav_bar_file_name + tab.get_attribute('innerHTML')
            write_code(file_name, returned_code)
        except Exception as e:
            print(e)
            print("Failed to write")


def iterate_general_code(code, driver, file_index):
    solution_code_class = "styles__Buttons_Wrapper"
    try:
        returned_code = copy_code(code, driver, file_index)
        write_code(f"Code_{file_index}", returned_code)
    except Exception as e:
        print("Failed to write")
    if code.find_elements(By.CSS_SELECTOR, f"div[class*='{solution_code_class}']"):
        try:
            returned_code = copy_code(code, driver, False)
            write_code(f"Code_Solution_{file_index}", returned_code)
        except Exception as e:
            print(e)
            print("Failed to write")


def code_container_clipboard_type(driver):
    print("Code Container Clipboard Type Function")
    code_container_class = "code-container"
    code_nav_bar_class = "styles__TabNav"
    code_nav_tab_class = "Widget__NavigaitonTab"

    code_containers = driver.find_elements(
        By.CSS_SELECTOR, f"div[class*='{code_container_class}']")
    if code_containers:
        create_temp_textarea(driver)
        code_directory_path = os.getcwd()
        for folder_index, code in enumerate(code_containers):
            create_folder("code_clipboard" + str(folder_index))
            code_nav_bar = code.find_element(
                By.XPATH, "../..").find_elements(By.CSS_SELECTOR, f"ul[class*='{code_nav_bar_class}']")
            code_nav_tab = code.find_elements(
                By.CSS_SELECTOR, f"div[class*='{code_nav_tab_class}']")
            if code_nav_bar:
                print("Nav Bar Found in code container")
                iterate_nav_bar(
                    code, code_nav_bar[0], code_nav_tab, driver)
            elif not code_nav_bar and code_nav_tab:
                iterate_nav_tab(code, code_nav_tab, driver)
            elif not code_nav_bar and not code_nav_tab:
                iterate_general_code(code, driver, str(folder_index))

            os.chdir(code_directory_path)
        delete_node(driver, "textarea[class*='temptextarea']")
    else:
        print("No code containers found")


def extract_zip_files():
    print("Zip File Extraction")
    for path in glob.iglob("./**/*zip", recursive=True):
        zf = os.path.basename(path)
        zipfile.ZipFile(path, 'r').extractall(path[:-len(zf)])
        os.remove(path)


def demark_as_completed(driver):
    div_class = "styles__Checkbox"
    try:
        driver.execute_script(f'''
            return document.querySelector("div[class*='{div_class}']").click();
        ''')
    except Exception:
        pass


def scrape_page(driver, file_index):
    title = get_file_name(driver)
    file_name = str(file_index) + "-" + title
    driver.set_window_size(1920, get_current_height(driver))
    show_hints_answer(driver)
    show_code_box_answer(driver)
    open_slides(driver)
    create_folder(file_name)
    take_screenshot(driver, file_name)
    code_container_download_type(driver)
    code_container_clipboard_type(driver)
    demark_as_completed(driver)

    if not next_page(driver):
        sleep(5)
        return False
    return True


def check_login(driver):
    is_logged_in = driver.find_elements(
        By.CSS_SELECTOR, "a[href*='/unlimited']")
    if not is_logged_in:
        return True
    print("Please log in")
    return False


def load_webpage(driver, url):
    global file_index
    _, save_path = load_config()
    driver.get(url)
    sleep(10)
    if not check_login(driver):
        return False
    os.chdir(save_path)

    create_course_folder(driver, url)
    course_path = os.getcwd()
    while check_login(driver) and scrape_page(driver, file_index):
        print("---------------", file_index, "Complete-------------------")
        sleep(10)
        file_index += 1
        os.chdir(course_path)
    os.chdir(course_path)
    extract_zip_files()
    os.chdir(save_path)
    return True


def create_log(file_index, url, save_path):
    with open(os.path.join(save_path, 'log.txt'), 'a') as file:
        file.write(f"{file_index} {url}\n")


def scrape_courses():
    clear()
    global file_index
    print('''
                Scraper Started, Log file can be found in config directory
    ''')

    driver = load_chrome_driver(headless=True)
    try:
        url_text_file, save_path = load_config()
        if not os.path.isfile(url_text_file):
            raise Exception(
                "Url Text file path not found, Please check your config")
        with open(url_text_file, 'r') as file:
            url_list = file.readlines()
        for url_data in url_list:
            url_data = url_data.split()
            if len(url_data) == 2:
                file_index, url = int(url_data[0]), url_data[1]
            else:
                file_index, url = 0, url_data[0]
            try:
                print(f'''
                            Starting Scraping: {file_index}, {url}
                ''')
                if not load_webpage(driver, url):
                    break
                print("Next Course")
            except KeyboardInterrupt:
                create_log(file_index, driver.current_url, save_path)
                raise Exception("Exited Manually")
            except Exception as e:
                create_log(file_index, driver.current_url, save_path)
                print("Found Issue, Going Next Course", e)

        print("Script Execution Complete")
        driver.quit()
    except Exception as e:
        driver.quit()
        print("Exception, Driver exited")
        raise Exception(e)


def generate_config():
    clear()
    print('''
        Leave Blank in you don't want to overwrite Previous Values
    ''')
    try:
        url_text_file, save_path = load_config()
    except Exception as e:
        print("Enter the paths for your config")
    url_text_file = input("Enter the URL text file path: ") or url_text_file
    save_path = input("Enter Save Path: ") or save_path

    base_config_path = os.path.join(OS_ROOT, ".educative")
    if ".educative" not in os.listdir(OS_ROOT):
        os.mkdir(base_config_path)

    with open(os.path.join(base_config_path, "config.json"), "w+") as config_file:
        json.dump({
            "url_file_path": url_text_file,
            "save_path": save_path
        }, config_file)


def login_educative():
    clear()
    driver = load_chrome_driver(headless=False)
    try:
        driver.get("https://educative.io")
        input("Press enter to return to Main Menu after Login is successfull")
        driver.quit()
        print("Login Success!")
    except Exception as e:
        print("Exception occured, Try again", e)
        driver.quit()


def get_binary_path():
    global current_os
    if current_os.startswith('darwin'):
        chromedriver = r'mac/chromedriver'
        chrome_path = r"mac/Chromium.app/Contents/MacOS/Chromium"
    elif current_os.startswith('linux'):
        chromedriver = r'linux/chromedriver'
        chrome_path = r"linux/chrome/chrome"
    elif current_os.startswith('win32') or current_os.startswith('cygwin'):
        chromedriver = r'win\chromedriver.exe'
        chrome_path = r'win\chrome.exe'
    return chrome_path, chromedriver


def clear():
    global current_os
    if current_os.startswith('darwin'):
        os.system('clear')
    elif current_os.startswith('linux'):
        os.system('clear')
    elif current_os.startswith('win32') or current_os.startswith('cygwin'):
        os.system('cls')


if __name__ == '__main__':
    current_os = sys.platform
    clear()
    while True:
        file_index = 0
        try:
            print('''
                        Educative Scraper, made by Anilabha Datta
                        Project Link: github.com/anilabhadatta/educative.io_scraper
                        Read the documentation for more information about this project.

                        Press 1 to generate config
                        Press 2 to login Educative
                        Press 3 to start scraping
                        Press any key to exit
            ''')
            choice = input("Enter your choice: ")
            if choice == "1":
                generate_config()
            elif choice == "2":
                login_educative()
            elif choice == "3":
                scrape_courses()
            else:
                break
        except KeyboardInterrupt:
            input("Press Enter to continue")
        except Exception as e:
            print("Main Exception", e)
            input("Press Enter to continue")

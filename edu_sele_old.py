import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time

options = webdriver.ChromeOptions()
options.add_argument('headless')
options.add_argument("user-data-dir=C:\\Users\\anila\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 7\\")
options.add_argument(r'--profile-directory=Default')
options.add_argument("--start-maximized")
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(executable_path="C:/chromedriver.exe", chrome_options=options)
driver.set_window_size(1920,1080)


# username = 'jonathan.h.friedman@gmail.com'
# password = 'lambofgod20'
# driver.get("https://educative.io/login")
# driver.get_screenshot_as_file('testa.png')
# time.sleep(4)
# user_inp = driver.find_element_by_xpath('//*[@id="__next"]/div[2]/div[2]/div/div/div/div/div[3]/form/div[1]/div[1]/input')
# user_inp.send_keys(username)
# pass_inp = driver.find_element_by_xpath('//*[@id="password-field"]')
# pass_inp.send_keys(password)
# driver.find_element_by_xpath('//*[@id="password-field"]').send_keys(Keys.RETURN)
# time.sleep(2)
# try:
# 	auth_inp = driver.find_element_by_xpath('//*[@id="__next"]/div[2]/div[2]/div/div/div/div/div[3]/form/div[1]/div[1]/input')
# 	auth = input("Enter auth code: ")
# 	auth_inp.send_keys(auth)
# 	driver.find_element_by_xpath('//*[@id="__next"]/div[2]/div[2]/div/div/div/div/div[3]/form/div[1]/div[1]/input').send_keys(Keys.RETURN)
# except:
# 	pass
# driver.get_screenshot_as_file('testb.png')
# time.sleep(5)
# driver.get_screenshot_as_file('testc.png')

def code_copy(container,driver):
	container = container.find_elements_by_css_selector("svg.w-7.h-7")
	# time.sleep(1)
	container[0].click()
	print("Clicked on Clipboard")
	textbox = driver.find_element_by_css_selector("textarea.tempcodebox")
	textbox.click()
	time.sleep(1)
	textbox.send_keys(Keys.CONTROL, "a")
	textbox.send_keys(Keys.CONTROL, "v")
	time.sleep(1)
	print("Paste complete")
	return textbox.get_attribute('value')

image_count = int(input("Enter starting index: "))
url = input("Enter url: ")
driver.get(url)
while True:
	bckpath = os.getcwd()
	print("---------------",image_count,"-------------------")
	flag = 0
	try:
		time.sleep(15)
		pimage_name = driver.find_elements_by_css_selector('h2.mb-10')
		if pimage_name != []:
			if pimage_name[0] == "":
				raise Exception
			else:
				image_name = pimage_name[0].get_attribute('innerHTML')
		else:
			image_name = driver.find_element_by_css_selector('h1.text-3xl.font-semibold.text-left.mb-2').get_attribute('innerHTML')
			if image_name == "":
				raise Exception
		S = lambda X: driver.execute_script('return document.body.parentNode.scroll'+X)
		driver.set_window_size(1920,S('Height'))

		#show ans
		answers = driver.find_elements_by_css_selector('button.whitespace-normal.outlined-default.m-0')
		if answers != []:
			for answer in answers:
				answer.click()
		answers = driver.find_elements_by_css_selector('div.tailwind-hidden')
		if answers != []:
			# print(len(answers))
			for answer in answers:
				if answer.get_attribute('innerHTML') == "Solution" or answer.get_attribute('innerHTML') == "Show Solution":
					answer.click()
					time.sleep(1)
					driver.find_element_by_css_selector('button.text-default.py-2.m-2').click()
					time.sleep(1)

		if pimage_name == []:
			js = '''var div = document.getElementsByClassName("text-3xl font-semibold text-left mb-2")[0];
			var input = document.createElement("textarea");
			input.name = "tempcodebox";
			input.className = "tempcodebox";
			input.maxLength = "10000";
			input.cols = "50";
			input.rows = "10";
			div.appendChild(input);'''
			driver.execute_script(js)
		else:
			js = '''var div = document.getElementsByClassName("mb-10")[0];
			var input = document.createElement("textarea");
			input.name = "tempcodebox";
			input.className = "tempcodebox";
			input.maxLength = "10000";
			input.cols = "50";
			input.rows = "10";
			div.appendChild(input);'''
			driver.execute_script(js)		
		answers = driver.find_elements_by_css_selector('div.styles__CodeEditorStyled-sc-2pjuhh-0.dgoHVT')
		if answers != []:
			bckpath = os.getcwd()

			for answer in range(len(answers)):
				clipboard = answers[answer].find_element_by_xpath('../..')
				clipboard = clipboard.find_elements_by_css_selector('button.Button-sc-1i9ny0d-0.CircleButton-sc-1w51ure-0.Widget__CopyButton-csjrsw-3.styles__Buttons_Copy-sc-2pjuhh-3.kamgiT')
				# print(clipboard)
				if clipboard != []:
					try:
						# clipboard[0].click()
						js = '''document.getElementsByClassName("Button-sc-1i9ny0d-0 CircleButton-sc-1w51ure-0 Widget__CopyButton-csjrsw-3 styles__Buttons_Copy-sc-2pjuhh-3 kamgiT")[0].click();'''
						driver.execute_script(js)
						print("Clicked on Solution Clipboard")
						textbox = driver.find_element_by_css_selector("textarea.tempcodebox")
						textbox.click()
						time.sleep(1)
						textbox.send_keys(Keys.CONTROL, "a")
						textbox.send_keys(Keys.CONTROL, "v")
						time.sleep(1)
						print("Paste complete")
						if str(image_count)+"-Codes" not in os.listdir():
							os.mkdir(str(image_count)+"-Codes")
						os.chdir(os.getcwd()+"\\"+str(image_count)+"-Codes")					
						f = open('Solution'+str(answer)+'.txt' , 'w',encoding='utf-8')
						f.write(textbox.get_attribute('value'))
						f.close()
					except Exception as e:
						print("Error copying text")
						print(e)
						pass
				else:
					js = '''document.getElementsByClassName("styles__CodeEditorStyled-sc-2pjuhh-0 dgoHVT")['''+str(answer)+'''].style.height = "3000px";'''
					driver.execute_script(js)
			os.chdir(bckpath)
		js = '''document.getElementsByClassName("tempcodebox")[0].remove();'''
		driver.execute_script(js)
		

		# Slides
		slides = driver.find_elements_by_css_selector('button.Button-sc-1i9ny0d-0.CircleButton-sc-1w51ure-0.styles__AnimationPlus-sc-8tvqhb-13.gjbvCG')
		if slides != []:
			for slide in slides:
				slide.click()
			print("Slides opened")
			time.sleep(10)
		else:
			print("Slides skipped")


		S = lambda X: driver.execute_script('return document.body.parentNode.scroll'+X)
		driver.set_window_size(1920,S('Height'))
		time.sleep(1)
		
		for char in range(len(image_name)):
			if image_name[char] == "#" or image_name[char] == ":" or image_name[char] == "?" or image_name[char] == "/" or image_name[char]=='"' or image_name[char] == "|"  or image_name[char] == "*" or image_name[char] == "\\":
				image_name = image_name[:char] + " " + image_name[char+1:]
		driver.find_element_by_xpath("/html/body/div[1]/div[2]/div[2]").screenshot(str(image_count)+"-"+image_name+".png")
		print("Image Created")

		if pimage_name == []:
			js = '''var div = document.getElementsByClassName("text-3xl font-semibold text-left mb-2")[0];
			var input = document.createElement("textarea");
			input.name = "tempcodebox";
			input.className = "tempcodebox";
			input.maxLength = "10000";
			input.cols = "50";
			input.rows = "10";
			div.appendChild(input);'''
			driver.execute_script(js)
		else:
			js = '''var div = document.getElementsByClassName("mb-10")[0];
			var input = document.createElement("textarea");
			input.name = "tempcodebox";
			input.className = "tempcodebox";
			input.maxLength = "10000";
			input.cols = "50";
			input.rows = "10";
			div.appendChild(input);'''
			driver.execute_script(js)			
		c1,c2 = 0,0

		# Main Case
		containers = driver.find_elements_by_css_selector('div.code-container')
		if containers != []:
		
			bckpath = os.getcwd()
			if str(image_count)+"-Codes" not in os.listdir():
				os.mkdir(str(image_count)+"-Codes")
			os.chdir(os.getcwd()+"\\"+str(image_count)+"-Codes")
			cdbckpath = os.getcwd()

			for container in containers:
				codebox_1 = container.find_element_by_xpath('../..')
				codebox_1_ul = codebox_1.find_elements_by_css_selector('ul.styles__TabNav-sc-2pjuhh-15.bbbOxq.nav.nav-tabs')
				codebox_2 = container.find_elements_by_css_selector('div.Widget__MultiFiles-csjrsw-6.styles__MultiFiles-sc-2pjuhh-8.bXHbra')
				
				# Case 1 Ul tag with or without Filebox
				if codebox_1_ul != []:
					print("------Case 1-------")
					os.chdir(cdbckpath)
					if "Box"+str(c1) not in os.listdir():
						os.makedirs("Box"+str(c1))
					os.chdir(os.getcwd()+"\\Box"+str(c1))
					c1+=1

					tabs_ul = codebox_1_ul[0].find_elements_by_css_selector('span.desktop-only.styles__DesktopOnly-sc-2pjuhh-19.agoNC')
					for tab_ul in tabs_ul:
						tab_ul.click()
						time.sleep(1)
						print("Tab clicked of Ul tag")
						tab_lang = tab_ul.find_element_by_css_selector('span.styles__TabTitle-sc-2pjuhh-14.hndpvI').get_attribute('innerHTML')

						# case 2 Ul tag with file box
						file_box = codebox_1.find_elements_by_css_selector('div.styles__Files-sc-2pjuhh-10.klYjb')
						if file_box != []:
							print("------Case 2--------")
							files = file_box[0].find_elements_by_css_selector('div.Widget__NavigaitonTab-csjrsw-2.styles__File-sc-2pjuhh-11.jFUhiu')
							try:
								codes = code_copy(codebox_1,driver)
								lang = file_box[0].find_element_by_css_selector('div.Widget__NavigaitonTab-csjrsw-2.styles__File-sc-2pjuhh-11.gIgnvf').get_attribute('innerHTML')
								fname = tab_lang+lang+".txt"
								f = open(fname , "w", encoding='utf-8')
								f.write(codes)
								f.close()
								print("Txt File Created")
							except:
								print("Error cannot create txt file")

							for file in files:
								print("Tab Clicked of File Box")
								file.click()
								time.sleep(1)
								try:
									codes = code_copy(codebox_1,driver)
									lang = file_box[0].find_element_by_css_selector('div.Widget__NavigaitonTab-csjrsw-2.styles__File-sc-2pjuhh-11.gIgnvf').get_attribute('innerHTML')					
									fname = tab_lang+lang+".txt"
									f = open(fname , "w", encoding='utf-8')
									f.write(codes)
									f.close()
									print("Txt File Created")
								except:
									print("Error cannot create txt file")
						else:
							# Only Ul tag , and no file box is present
							try:
								codes = code_copy(codebox_1,driver)
								lang = tab_ul.find_element_by_css_selector('span.styles__TabTitle-sc-2pjuhh-14.hndpvI').get_attribute('innerHTML')

								fname = tab_lang+".txt"
								f = open(fname , "w", encoding='utf-8')
								f.write(codes)
								f.close()
								print("Txt File Created")
							except:
								print("Error cannot create txt file")

				elif codebox_1_ul == [] and codebox_2 != []:
					#  Case 3 > No Ul tag but only file box
					print("-------Case 3-----------")

					os.chdir(cdbckpath)
					if "Box"+str(c1) not in os.listdir():
						os.makedirs("Box"+str(c1))
					os.chdir(os.getcwd()+"\\Box"+str(c1))
					c1+=1

					files = codebox_2[0].find_elements_by_css_selector('div.Widget__NavigaitonTab-csjrsw-2.styles__File-sc-2pjuhh-11.jFUhiu')
					try:
						codes = code_copy(codebox_2[0],driver)
						lang = codebox_2[0].find_element_by_css_selector('div.Widget__NavigaitonTab-csjrsw-2.styles__File-sc-2pjuhh-11.gIgnvf').get_attribute('innerHTML')
						fname = lang+".txt"
						f = open(fname , "w", encoding='utf-8')
						f.write(codes)
						f.close()
						print("Txt File Created")
					except:
						print("Error cannot create txt file")

					for file in files:
						print("Tab Clicked of File Box")
						file.click()
						time.sleep(1)
						try:
							codes = code_copy(codebox_2[0],driver)
							lang = codebox_2[0].find_element_by_css_selector('div.Widget__NavigaitonTab-csjrsw-2.styles__File-sc-2pjuhh-11.gIgnvf').get_attribute('innerHTML')					
							fname = lang+".txt"
							f = open(fname , "w", encoding='utf-8')
							f.write(codes)
							f.close()
							print("Txt File Created")
						except:
							print("Error cannot create txt file")				

				elif codebox_1_ul == [] and codebox_2 == []:
					# Case 4 No ul tag , No File box is present
					print("--------Case 4-------")
					os.chdir(cdbckpath)
					try:
						codes = code_copy(container,driver)
						fname = "CodeBox"+str(c1)+".txt"

						f = open(fname , "w", encoding='utf-8')
						f.write(codes)
						f.close()
						print("Txt File Created")
					except:
						print("Error , cannot create txt file")
						pass
					c1+=1
			os.chdir(bckpath)

		# Case 5
		containers = driver.find_elements_by_css_selector('div.styles__Spa_Container-sc-1vx22vv-62.jquSGK')
		if containers != []:
			print("-------Case 5--------")
			bckpath = os.getcwd()
			if str(image_count)+"-Codes" not in os.listdir():
				os.mkdir(str(image_count)+"-Codes")
			os.chdir(os.getcwd()+"\\"+str(image_count)+"-Codes")
			cdbckpath = os.getcwd()
			for container in containers:
				os.chdir(cdbckpath)
				if "BoxT2-"+str(c2) not in os.listdir():
					os.makedirs("BoxT2-"+str(c2))
				os.chdir(os.getcwd()+"\\BoxT2-"+str(c2))
				c2+=1
				driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
				params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': os.getcwd()}}
				driver.execute("send_command", params)
				try:
					container.find_elements_by_css_selector("svg.w-7.h-7")[1].click()
					time.sleep(2)
					print("Downloaded Zip File")
				except:
					print("Zip File not Downloaded")
					pass
				# files = container.find_element_by_css_selector('div.children')
				# tabs = files.find_elements_by_css_selector('span.styles__NavIcon-sc-1vx22vv-21.cueaXz')
				# for tab in tabs:
				# 	if tab.get_attribute('innerHTML') == "":
				# 		tab = tab.find_element_by_xpath('../..')
				# 		tab = tab.find_element_by_css_selector('span.node')
				# 		print("Tab Clicked")
				# 		tab.click()
				# 		time.sleep(1)

				# 		lang = tab.get_attribute('innerHTML')[58:]
				# 		codes = code_copy(container,driver)
	
				# 		fname = lang+".txt"
				# 		f = open(fname , "w",encoding='utf-8')
				# 		f.write(codes)
				# 		f.close()
			os.chdir(bckpath)


		driver.set_window_size(1920,1080)
	except Exception as e:
		flag = 1
		driver.refresh()
		os.chdir(bckpath)
		print(e)
		pass
	print(flag)
	
	if flag == 0:
		try:
			if driver.find_elements_by_css_selector('button.outlined-primary.m-0')[0].get_attribute('innerHTML')[:11] == "Next Module":
				# file = open(str(image_count)+"-NewModule.txt" ,"w")
				# file.write("New Module at pos "+str(image_count))
				# file.close()
				driver.quit()
				break
			# time.sleep(1)
			# driver.find_elements_by_css_selector('button.outlined-primary.m-0')[0].click()
			js = '''document.getElementsByClassName('outlined-primary m-0')[0].click();'''
			driver.execute_script(js)
			print("Next Page")
			image_count+=1
		except Exception as e:
			print(e)
			driver.quit()
			break
	else:
		pass
print("Finished")
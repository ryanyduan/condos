import os
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
import time
import pandas as pd

load_dotenv()

def is_valid_condo_listing(condo):
    return "Create an account" not in condo and len(condo) >= 8 and condo[0] is not None

def parsed_condos_html(html):
	condos = []
	soup = BeautifulSoup(html, 'html.parser')
	list_row = soup.find(id='listRow')
	if not list_row:
		return False
	list_row_children = list_row.children
	for child in list_row_children:
		condo = child.get_text(separator=', ', strip=True)
		if is_valid_condo_listing(condo):
			split_condo = condo.split(', ')
			zeroth = split_condo[0][1:]
			if ',' in zeroth:
				zeroth = "".join(zeroth.split(','))
			if not zeroth.isnumeric():
				split_condo = split_condo[1:]
			condos.append(split_condo)
	return condos

total_condos = []
page_num = 1

URL = "https://condos.ca/toronto/condos-for-sale?beds=1.1-1.9,1-1&sale_price_range=0,650000&neighbourhood_id=746,751,754,753,752,747,750,748,760,759, \
       862,755,756,757,758&map_bounds=-79.43009432625107,43.6276717305289,-79.35489993762302,43.67944188260435&size_range=500,999999999"
driver = webdriver.Chrome()

wait = WebDriverWait(driver, 10)

driver.get(URL)

wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Log in')]")))
login_button = driver.find_element_by_xpath("//button[contains(.,'Log in')]")

login_button.send_keys(Keys.ENTER)
login_button.send_keys(Keys.ENTER)
login_button.send_keys(Keys.ENTER)
login_button.send_keys(Keys.ENTER)
login_button.send_keys(Keys.ENTER)
login_button.send_keys(Keys.ENTER)

wait.until(EC.element_to_be_clickable((By.ID, "login")))
username = driver.find_element_by_id("login")
password = driver.find_element_by_id("password")

username.send_keys(os.getenv("username"))
password.send_keys(os.getenv("password"))

driver.find_element_by_css_selector("div:nth-child(3) > #appButton").send_keys(Keys.ENTER)

time.sleep(10)

condos_html = driver.page_source

current_condos_list = parsed_condos_html(condos_html)

total_condos += current_condos_list

page_num = 2

while True:
	URL = "https://condos.ca/toronto/condos-for-sale?beds=1.1-1.9,1-1&sale_price_range=0,650000&neighbourhood_id=746,751,754,753,752,747,750,748,760,759, \
              862,755,756,757,758&map_bounds=-79.43009432625107,43.6276717305289,-79.35489993762302,43.67944188260435&size_range=500,999999999&page={page}".format(page=page_num)
	
	driver.get(URL)
	
	time.sleep(3)
	
	condos_html = driver.page_source
	
	current_condos_list = parsed_condos_html(condos_html)
	
	if not current_condos_list:
		break
	else:
		total_condos += current_condos_list
		page_num += 1



data = []
columns = ['Price', 'Address', 'Bd', 'Ba', 'Parking', 'Sqft', 'Maint. Fee', 'Time on market']

for i in range(len(total_condos)):
    condo = total_condos[i]
    condo.pop(-2)
    condo.pop(1)
    if (len(condo) == 7):
        obj = {'Price': condo[0], 'Address': condo[1], 'Bd': condo[2], 'Ba': condo[3], 'Parking': condo[4], 'Sqft': condo[5], 'Time on Market': condo[6]}
        data.append(obj)
    else:
        obj = dict(zip(columns, condo))
        data.append(obj)

df = pd.DataFrame(data, columns=columns)

df.to_csv('condos.csv')

driver.quit()

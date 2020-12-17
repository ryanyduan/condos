import os
import sys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotVisibleException, ElementNotInteractableException
from bs4 import BeautifulSoup
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

def get_condos_data(driver):
	try:
		total_condos = []
		page_num = 1

		URL = "https://condos.ca/toronto/condos-for-sale?beds=1.1-1.9,1-1&sale_price_range=0,650000&neighbourhood_id=746,751,754,753,752,747,750,748,760,759, \
			862,755,756,757,758&map_bounds=-79.43009432625107,43.6276717305289,-79.35489993762302,43.67944188260435&size_range=500,999999999"

		wait = WebDriverWait(driver, 10)

		driver.get(URL)

		wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Log in')]")))
		login_button = driver.find_element_by_xpath("//button[contains(.,'Log in')]")

		time.sleep(10)

		login_button.click()

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
			
			time.sleep(10)
			
			condos_html = driver.page_source
			
			current_condos_list = parsed_condos_html(condos_html)
			
			if not current_condos_list:
				break
			else:
				total_condos += current_condos_list
				page_num += 1
		
		return total_condos
	
	except (TimeoutException, NoSuchElementException, ElementNotVisibleException, ElementNotInteractableException):
		return -1
	except:
		return -2

def condos_to_df(condos):
	data = []
	columns = [
			   'Address',
			   'Bd',
			   'Ba',
			   'Parking',
			   'Sqft',
			   'Maint Fee'
			   'Price',
			   ]

	for i in range(len(condos)):
		condo = condos[i]
		condo = condo[:-2]
		condo.pop(1)
		condo[0] = "".join(condo[0][1:].split(','))
		condo[5] = condo[5][:-5]
		if (len(condo) == 7):
			obj = {
				'Price': condo[0],
				'Address': condo[1],
				'Bd': condo[2],
				'Ba': condo[3],
				'Parking': condo[4],
				'Sqft': condo[5],
				'Maint Fee': condo[6][12:]
				}
			data.append(obj)
		else:
			obj = dict(zip(columns, condo))
			data.append(obj)

	df = pd.DataFrame(data, columns=columns)
	df['Price'] = pd.to_numeric(df['Price'])

	return df

def is_scrape_failed(condos):
	if condos == -1 or condos == -2:
		return True
	return False

def calculate_max_price(row):
    max_price = row.get('Max_Price')
    if pd.isnull(max_price):
        return row.get('Price')
    else:
        return max(row.get('Price'), row.get('Max_Price'))

def calculate_daily_change(row):
    if not pd.isnull(yesterday_price := row.get('Yesterday_Price')):
        return row.get('Price') - yesterday_price
    else:
        return 'New'

def merge_dfs(today_df, yesterday_df):
	yesterday_df = yesterday_df.rename({'Price': 'Yesterday_Price'}, axis='columns')
	yesterday_df['Yesterday_Price'] = pd.to_numeric(yesterday_df['Yesterday_Price'])
	new_df = today_df.merge(yesterday_df[['Yesterday_Price', 'Address']], on='Address', how='left')
	new_df['Max_Price'] = new_df.apply(lambda row: calculate_max_price(row), axis=1)
	new_df['Daily_Change'] = new_df.apply(lambda row: calculate_daily_change(row), axis=1)
	return new_df

if __name__ == '__main__':
	REDO_ATTEMPTS = 0
	MAX_ATTEMPTS = 3
	firefox_options = Options()
	firefox_options.add_argument("--headless")
	driver = webdriver.Firefox(options=firefox_options)
	while (condos := get_condos_data(driver)) == -1 and REDO_ATTEMPTS < MAX_ATTEMPTS:
		condos = get_condos_data(driver)
		REDO_ATTEMPTS += 1
	
	if is_scrape_failed(condos):
		# Send Email
		driver.quit()
		sys.exit(-1)

	df = condos_to_df(condos)
	
	if not (yesterday_df := pd.read_csv('condos.csv')).empty if os.path.exists('condos.csv') else None:
		new_df = merge_dfs(df, yesterday_df)
		new_df.to_csv('condos.csv')
	else:
		df.to_csv('condos.csv')

	driver.quit()
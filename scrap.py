import time, json, re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BUILDING_ROOMS = {
    "IM2AG_F": {
        "search_term": "IM2AG_Bâtiment F",
        "display_name": "IM2AG",
        "rooms": [
            'f018','f022','f316','f320','f107','f109','f111','f112',
            'f113','f114','f115','f116','f117','f118','f218','f319',
            'f321','f201','f202','f203','f204','f211','f212','f213',
            'f214','f215','f216','f217'
        ]
    }
}

"""
open a single url in a headless chrome browser, and return the corresponding driver
"""
def openSingleLink(link) :
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    # Add arguments for headless operation
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(link)
    return driver

"""
Scrape the content of a building, as an element of the BUILDING_ROOMS
Find each rooms taken today, for a given search query
Do not use for weekly or for too many places at once, this **will** crash. 
"""
def scrape_building(search_term, building_rooms):
    """
    Scrapes all room data for a single building.
    Returns a dictionary of room schedules.
    """
    driver = None
    roomDict = {}
    
    try:
        driver = openSingleLink("https://redirect.univ-grenoble-alpes.fr/ADE_ENSEIGNANTS")
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="x-auto-15-input"]'))).click()
        driver.find_element(By.XPATH, '/html/body/div[4]/div/div[1]').click()
        time.sleep(2)
        
        search = driver.find_element(By.XPATH, '//*[@id="x-auto-111-input"]')
        search.send_keys(search_term)
        
        driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/table/tbody/tr/td[1]/table/tbody/tr/td[1]/table/tbody/tr[2]/td[2]/em/button').click()
        
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div/div[4]')))
        
        source = driver.page_source
        occurences = re.findall('<div unselectable="on"(.*?)>', source)
        
        for element in occurences :
            times = re.findall(r'([0-9][0-9]h[0-9][0-9])', element)

            if len(times) >= 2 :
                timeStart = times[0]
                timeEnd = times[1]
                
                found_rooms_for_event = []
                for room_name in building_rooms:
                    escaped_room_name = re.escape(room_name)
                    
                    pattern1 = r'{}\[=\"\"'.format(escaped_room_name)
                    pattern2 = r'{}=\"\"'.format(escaped_room_name)
                    
                    if re.search(pattern1, element) or re.search(pattern2, element):
                        found_rooms_for_event.append(room_name)

                for room in found_rooms_for_event :
                    if room not in roomDict :
                        roomDict[room] = [[timeStart, timeEnd]]
                    else :
                        roomDict[room].append([timeStart, timeEnd])

        for room in building_rooms:
            if room not in roomDict:
                roomDict[room] = [] # Represented as an empty list of bookings
                
    except Exception as e:
        print(f"ERROR: Failed to scrape {search_term}: {e}", flush=True)
        return {}
    finally:
        if driver:
            driver.quit()
            
    return roomDict


if __name__ == "__main__":
    
    all_schedules = {}

    print(f"Starting scrape for {len(BUILDING_ROOMS)} building(s)...", flush=True)

    for building_key, building_data in BUILDING_ROOMS.items():
        
        print(f"Scraping: {building_key} ({building_data['search_term']})...", flush=True)
        
        schedule_data = scrape_building(
            building_data["search_term"],
            building_data["rooms"]
        )
        
        all_schedules[building_data["display_name"]] = schedule_data

    print("Scraping complete. Final JSON output:", flush=True)
    print(json.dumps(all_schedules, indent=2, sort_keys=True))
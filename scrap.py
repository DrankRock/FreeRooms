import time, json, re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- DEBUG FLAG ---
# Set to True for verbose, step-by-step logging inside the scraper
# Set to False for standard, quieter operation
DEBUG = False
# ------------------

BUILDING_ROOMS = {
    "IM2AG_F": {
        # --- FIX ---
        # This MUST be the building search term, not a single room.
        # The script searches this page, then finds all rooms in the list.
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
    print("  Initializing Chrome driver with anti-detection options...", flush=True)
    chrome_options = Options()
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
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
    print(f"  Scraping {search_term}...", flush=True)
    
    try:
        driver = openSingleLink("https://redirect.univ-grenoble-alpes.fr/ADE_ENSEIGNANTS")
        print(f"  Page opened. Waiting for elements...", flush=True)
        # Increased wait time slightly in case of slow loads
        WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="x-auto-15-input"]'))).click()
        driver.find_element(By.XPATH, '/html/body/div[4]/div/div[1]').click()
        time.sleep(2)
        
        search = driver.find_element(By.XPATH, '//*[@id="x-auto-111-input"]')
        search.send_keys(search_term)
        print(f"  Searching for '{search_term}'...", flush=True)
        
        driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/table/tbody/tr/td[1]/table/tbody/tr/td[1]/table/tbody/tr[2]/td[2]/em/button').click()
        
        WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div/div[4]')))
        print("  Calendar grid loaded. Scraping page source...", flush=True)
        
        source = driver.page_source
        occurences = re.findall('<div unselectable="on"(.*?)>', source)
        print(f"  Found {len(occurences)} potential event elements.", flush=True)
        
        if DEBUG:
            event_counter = 0
            
        for element in occurences :
            if DEBUG:
                event_counter += 1
                print(f"\n---[ Parsing Event Block {event_counter} ]---", flush=True)
                print(f"  RAW HTML: {element}", flush=True)
            
            times = re.findall(r'([0-9][0-9]h[0-9][0-9])', element)
            
            if DEBUG:
                print(f"  Times Found: {times}", flush=True)

            if len(times) >= 1 : 
                timeStart = min(times)
                timeEnd = max(times)
                
                if DEBUG:
                    print(f"  Extracted Min Start: {timeStart}, Max End: {timeEnd}", flush=True)
                
                found_rooms_for_event = []
                
                if DEBUG:
                    # Truncate list to avoid spamming the console
                    print(f"  Checking against rooms list (first 5): {building_rooms[:5]}...", flush=True)

                for room_name in building_rooms:
                    escaped_room_name = re.escape(room_name)
                    pattern1_str = r'{}\[=\"\"'.format(escaped_room_name)
                    pattern2_str = r'{}=\"\"'.format(escaped_room_name)
                    found1 = re.search(pattern1_str, element)
                    found2 = re.search(pattern2_str, element)
                    
                    if found1 or found2:
                        if DEBUG:
                            print(f"    [MATCH] Found room: '{room_name}' (Pattern 1: {bool(found1)}, Pattern 2: {bool(found2)})", flush=True)
                        found_rooms_for_event.append(room_name)

                if DEBUG:
                    print(f"  Rooms found *for this event*: {found_rooms_for_event}", flush=True)

                for room in found_rooms_for_event :
                    if room not in roomDict :
                        roomDict[room] = [[timeStart, timeEnd]]
                        if DEBUG:
                            print(f"    Adding new entry for '{room}': [{timeStart}, {timeEnd}]", flush=True)
                    else :
                        if [timeStart, timeEnd] not in roomDict[room]:
                            roomDict[room].append([timeStart, timeEnd])
                            if DEBUG:
                                print(f"    Appending to existing entry for '{room}': [{timeStart}, {timeEnd}]", flush=True)
                        elif DEBUG:
                            print(f"    Skipping duplicate entry for '{room}': [{timeStart}, {timeEnd}]", flush=True)
            else:
                if DEBUG:
                    print(f"  Skipping block: No time data found.", flush=True)
            
            if DEBUG:
                print("---[ End Event Block ]---\n", flush=True)

        if DEBUG:
            print("\nFinished parsing all event blocks.", flush=True)
            
        for room in building_rooms:
            if room not in roomDict:
                if DEBUG:
                    print(f"  Adding empty list for un-found room: '{room}'", flush=True)
                roomDict[room] = [] # Represented as an empty list of bookings
        
        print(f"  Processed all elements. Found data for {len(roomDict)} rooms.", flush=True)
            
    except Exception as e:
        print(f"ERROR: Failed to scrape {search_term}: {e}", flush=True)
        return {} # Return empty dict on failure
    finally:
        if driver:
            print(f"  Closing driver for {search_term}.", flush=True)
            driver.quit()
            
    return roomDict


if __name__ == "__main__":
    
    all_schedules = {}
    output_filename = "schedule.json"

    print(f"Starting scrape for {len(BUILDING_ROOMS)} building(s)...", flush=True)

    for building_key, building_data in BUILDING_ROOMS.items():
        
        print(f"Processing: {building_key} (Search Term: '{building_data['search_term']}')...", flush=True)
        
        schedule_data = scrape_building(
            building_data["search_term"],
            building_data["rooms"]
        )
        
        # Get timestamp *after* scraping is complete for this building
        update_time_iso = datetime.now().isoformat()
        
        if schedule_data:
            print(f"Successfully scraped data for {building_key}.", flush=True)
        else:
            print(f"No data found or error during scrape for {building_key}.", flush=True)

        # Structure the data with last_update and room schedules
        all_schedules[building_data["display_name"]] = {
            "last_update": update_time_iso,
            "rooms": schedule_data
        }

    print("All scraping complete.", flush=True)

    # Save the final dictionary to the specified JSON file
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_schedules, f, indent=2, sort_keys=True, ensure_ascii=False)
        print(f"Successfully saved schedules to {output_filename}", flush=True)
    except Exception as e:
        print(f"ERROR: Failed to write to {output_filename}: {e}", flush=True)

    if DEBUG:
        print("\n--- Final JSON Output ---")
        print(json.dumps(all_schedules, indent=2, sort_keys=True))
        print("-------------------------\n")
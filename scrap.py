import time, json, re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- DEBUG FLAG ---
DEBUG = True
# ------------------

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
    }, 
    "Fac droit": {
        "search_term": "Droit_Aile", 
        "display_name": "Fac Droit",
         "rooms": [
            'Droit A _ Salle 306', 'Droit A _ Séminaire 1', 'Droit A _ Séminaire 2', 
            'Droit A _ Séminaire 3', 'Droit B_ salle B001', 'Droit B_ salle B002', 
            'Droit B_ salle B004', 'Droit B_ salle B005', 'Droit B_ salle B101 Langues', 
            'Droit B_ salle B102 Langues', 'Droit B_ salle B103 Langues', 
            'Droit B_ salle B104 Langues', 'Droit B_ salle B106 Langues', 
            'Droit B_ salle B107', 'Droit B_ salle B108', 'Droit B_ salle B109', 
            'Droit B_ salle B209', 'Droit B_ salle B212', 'Droit B_ salle B213', 
            'Droit B_ Salle B214 idex', 'Droit B_ Salle B215 idex', 
            'Droit B_ Salle B313', 'Droit B_ Salle B406', 'Droit B_ Salle B407', 
            'Droit B_ Salle soutenance B321', 'Droit B_ Salle soutenance B321'
        ]
    }, 
    "Fac Eco Gestion": {
        "search_term": "FEG_Salle", 
        "display_name": "Fac Eco Gestion",
        "rooms": [
            'Salle 101', 'Salle 104', 'Salle 106', 'Salle 108', 
            'Salle 110', 'Salle 400', 'Salle 524', 'Salle EG09', 
            'Salle EPE (204-205)', 'Salle Entresol', 'Salle Fardeheb', 
            'Salle IES', 'Salle EG01', 'Salle EG02', 'Salle EG03', 
            'Salle EG04', 'Salle EG05', 'Salle 107 Info', 
            'Salle 112 Info', 'Salle EG06', 'Salle EG07 Info'
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
    
    # --- STABILITY FIX ---
    # Add disable-gpu flag for CI environments
    chrome_options.add_argument("--disable-gpu")
    # ---------------------
    
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
        print(f"   Page opened. Waiting for elements...", flush=True)

        # --- STABILITY FIX: Wait for the main "loading" overlay to disappear ---
        try:
            print("   Waiting for 'loading' spinner to disappear...", flush=True)
            WebDriverWait(driver, 30).until(
                EC.invisibility_of_element_located((By.XPATH, "/html/body/div/div/img"))
            )
            print("   'loading' spinner gone. Proceeding.", flush=True)
        except TimeoutException:
            print("   WARN: 'loading' spinner did not disappear. Page might be stuck. Trying to proceed anyway...", flush=True)
        # ---------------------------------------------------------------------


        # 1. Wait for and click the *first* element (the "Resources" dropdown)
        print("   Clicking resource dropdown...", flush=True)
        WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="x-auto-15-input"]'))).click()
        
        # 2. Wait for the *next* element ("Salles" in the list) to be clickable
        print("   Clicking 'Salles' from dropdown...", flush=True)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[4]/div/div[1]'))).click()
        
        # 3. Wait for the search box to be ready
        print("   Waiting for search box...", flush=True)
        search = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="x-auto-111-input"]')))
        
        search.send_keys(search_term)
        print(f"   Searching for '{search_term}'...", flush=True)
        
        driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/table/tbody/tr/td[1]/table/tbody/tr/td[1]/table/tbody/tr[2]/td[2]/em/button').click()
        
        # Increased main calendar wait
        WebDriverWait(driver, 35).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div/div[4]')))
        print("   Calendar grid loaded. Scraping page source...", flush=True)
        
        source = driver.page_source
        occurences = re.findall('<div unselectable="on"(.*?)>', source)
        print(f"   Found {len(occurences)} potential event elements.", flush=True)
        
        if DEBUG:
            event_counter = 0
            
        for element in occurences :
            if DEBUG:
                event_counter += 1
                print(f"\n---[ Parsing Event Block {event_counter} ]---", flush=True)
                print(f"   RAW HTML: {element}", flush=True)
            
            times = re.findall(r'([0-9][0-9]h[0-9][0-9])', element)
            
            if DEBUG:
                print(f"   Times Found: {times}", flush=True)

            if len(times) >= 1 : 
                timeStart = min(times)
                timeEnd = max(times)
                
                if DEBUG:
                    print(f"   Extracted Min Start: {timeStart}, Max End: {timeEnd}", flush=True)
                
                found_rooms_for_event = []
                
                if DEBUG:
                    print(f"   Checking against rooms list (first 5): {building_rooms[:5]}...", flush=True)

                for room_name in building_rooms:
                    search_name = room_name 
                    if room_name.startswith('Droit A _ '):
                        search_name = room_name[10:] 
                    elif room_name.startswith('Droit B_ '):
                        search_name = room_name[9:] 

                    search_words = search_name.split(' ')
                    all_words_found = True
                    
                    if DEBUG:
                        print(f"     Checking for room: '{room_name}' (Simplified: '{search_name}')", flush=True)

                    for word in search_words:
                        if not word: 
                            continue
                        
                        escaped_word = re.escape(word)
                        if not re.search(escaped_word, element, re.IGNORECASE):
                            all_words_found = False
                            if DEBUG:
                                print(f"       [MISS] Word '{word}' not found.", flush=True)
                            break 
                    
                    if all_words_found:
                        if DEBUG:
                             print(f"     [MATCH] Found room: '{room_name}' (All parts matched)", flush=True)
                        found_rooms_for_event.append(room_name)

                if DEBUG:
                    print(f"   Rooms found *for this event*: {found_rooms_for_event}", flush=True)

                for room in found_rooms_for_event :
                    if room not in roomDict :
                        roomDict[room] = [[timeStart, timeEnd]]
                        if DEBUG:
                            print(f"     Adding new entry for '{room}': [{timeStart}, {timeEnd}]", flush=True)
                    else :
                        if [timeStart, timeEnd] not in roomDict[room]:
                            roomDict[room].append([timeStart, timeEnd])
                            if DEBUG:
                                print(f"     Appending to existing entry for '{room}': [{timeStart}, {timeEnd}]", flush=True)
                        elif DEBUG:
                            print(f"     Skipping duplicate entry for '{room}': [{timeStart}, {timeEnd}]", flush=True)
            else:
                if DEBUG:
                    print(f"   Skipping block: No time data found.", flush=True)
            
            if DEBUG:
                print("---[ End Event Block ]---\n", flush=True)

        if DEBUG:
            print("\nFinished parsing all event blocks.", flush=True)
            
        for room in building_rooms:
            if room not in roomDict:
                if DEBUG:
                    print(f"   Adding empty list for un-found room: '{room}'", flush=True)
                roomDict[room] = [] 
        
        print(f"   Processed all elements. Found data for {len(roomDict)} rooms.", flush=True)
            
    except TimeoutException as te:
        print(f"ERROR: Timed out waiting for an element in {search_term}. Page might not have loaded correctly or element is missing.", flush=True)
        print(f"TimeoutException details: {te.msg}", flush=True)
        return {} 
    except Exception as e:
        print(f"ERROR: A non-timeout error occurred scraping {search_term}.", flush=True)
        print(f"Exception Type: {type(e)}", flush=True)
        print(f"Exception Details: {e}", flush=True)
        return {} 
    finally:
        if driver:
            print(f"   Closing driver for {search_term}.", flush=True)
            driver.quit()
            
    return roomDict


if __name__ == "__main__":
    
    all_schedules = {}
    output_filename = "schedule.json"

    # --- Retry Configuration ---
    MAX_RETRIES_PER_BUILDING = 5
    RETRY_DELAY_SECONDS = 30
    # ---------------------------

    print(f"Starting scrape for {len(BUILDING_ROOMS)} building(s)...", flush=True)

    for building_key, building_data in BUILDING_ROOMS.items():
        
        print(f"Processing: {building_key} (Search Term: '{building_data['search_term']}')...", flush=True)
        
        schedule_data = {}  # Default to empty
        attempts = 0
        
        while attempts < MAX_RETRIES_PER_BUILDING:
            attempts += 1
            print(f"   Attempt {attempts}/{MAX_RETRIES_PER_BUILDING} for {building_key}...", flush=True)
            
            schedule_data = scrape_building(
                building_data["search_term"],
                building_data["rooms"]
            )
            
            # If scrape_building returns data (i.e., not {}), it was a success.
            # A successful run (even with no events) will return a dict
            # with room names as keys and empty lists as values.
            # A crash will return {}.
            if schedule_data:
                print(f"   Successfully scraped data for {building_key} on attempt {attempts}.", flush=True)
                break # Exit the retry loop
            
            # If we are here, schedule_data is {} (a failure)
            print(f"   Attempt {attempts} failed.", flush=True)
            
            if attempts < MAX_RETRIES_PER_BUILDING:
                print(f"   Waiting {RETRY_DELAY_SECONDS} seconds before next attempt...", flush=True)
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print(f"   All {MAX_RETRIES_PER_BUILDING} attempts failed for {building_key}. Giving up.", flush=True)

        # --- End of retry loop ---

        update_time_iso = datetime.now().isoformat()
        
        if not schedule_data:
             print(f"No data will be saved for {building_key} after all attempts.", flush=True)

        all_schedules[building_data["display_name"]] = {
            "last_update": update_time_iso,
            "rooms": schedule_data # This will be {} if all retries failed
        }

    print("All scraping complete.", flush=True)

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
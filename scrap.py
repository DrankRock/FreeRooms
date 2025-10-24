import argparse, time# arguments parsing, sleep
import re # scrape calendar data
from selenium import webdriver # open chromium webdriver
from selenium.webdriver.common.by import By # parse data from selenium
from selenium.webdriver.chrome.options import Options # options, to avoid singleLink autoclosing.
from selenium.webdriver.support.ui import WebDriverWait # Wait for the cookie
from selenium.webdriver.support import expected_conditions as EC # Same as above
from selenium.common.exceptions import TimeoutException # Same as above

BUILDING_ROOMS = {
    "IM2AG_Bâtiment F": [
        'f018','f022','f316','f320','f107','f109','f111','f112',
        'f113','f114','f115','f116','f117','f118','f218','f319',
        'f321','f201','f202','f203','f204','f211','f212','f213',
        'f214','f215','f216','f217'
    ]
    # You can add other buildings here, e.g.:
    # "IM2AG_Bâtiment G": ['g101', 'g102', ...]
}


def openSingleLink(link) :
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)

    # Add arguments for headless operation
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080") # Specify window size to avoid element rendering issues
    chrome_options.add_argument("--no-sandbox") # Bypasses OS security model, often required in containers
    chrome_options.add_argument("--disable-dev-shm-usage") # Overcomes limited resource problems

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(link)
    return driver

def args():
    parser = argparse.ArgumentParser(description='Cherche une salle libre sur ADE')
    parser.add_argument('-s', '--sallelibre', help='Cherche une salle libre dans la tranche horraire donnée en parametres', required=True, action='store', nargs=2)
    return parser.parse_args()

def hourToValue(hour): #takes a string "18h30"
        timeSplit = hour.split("h")
        return int(timeSplit[0])*60 + int(timeSplit[1])

def hourListProcess(timeList, wantedTimeStart, wantedTimeEnd):

    wantedStart = hourToValue(wantedTimeStart)
    wantedEnd = hourToValue(wantedTimeEnd)
    timeValues = []
    for elemnt in timeList :
        timeValueStart = hourToValue(elemnt[0])
        timeValueEnd = hourToValue(elemnt[1])
        timeValues.append([timeValueStart, timeValueEnd])
    sortedList = sorted(timeValues, key=lambda x: x[0])
    if len(sortedList) == 1 :
        if wantedEnd < sortedList[0][0] or wantedStart > sortedList[0][1] :
            return True
        else :
            return False
    else :
        if wantedEnd < sortedList[0][0] :
            return True
        for i in range(len(sortedList)-1) :
            if wantedStart > sortedList[i][1] and wantedEnd < sortedList[i+1][0] :
                return True
        if wantedStart > sortedList[len(sortedList)-1][1] :
            return True

    return False

    # print("Element : {} ; times : {} - {}".format(elemnt, timeValueStart, timeValueEnd))


if __name__ == "__main__":
    args = args()

    if hourToValue(args.sallelibre[0]) > hourToValue(args.sallelibre[1]) :
        print("ERREUR : L'heure de début est après l'heure de fin !")
        exit(0)
    
    roomDict = {}
    
    # Use the first building defined in the dictionary
    search_building = list(BUILDING_ROOMS.keys())[0]
    ROOMS = BUILDING_ROOMS[search_building]
    
    # This prefix is used by the regex. Update if room names change (e.g., 'g' for G building)
    roomPrefix = ['f'] 
    
    driver = openSingleLink("https://redirect.univ-grenoble-alpes.fr/ADE_ENSEIGNANTS")
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="x-auto-15-input"]'))).click()
    driver.find_element(By.XPATH, '/html/body/div[4]/div/div[1]').click()
    time.sleep(2)
    search = driver.find_element(By.XPATH, '//*[@id="x-auto-111-input"]')
    search.send_keys(search_building)
    driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/table/tbody/tr/td[1]/table/tbody/tr/td[1]/table/tbody/tr[2]/td[2]/em/button').click()
    #print(driver.page_source)
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div/div[4]')))
    source = driver.page_source
    occurences = re.findall('<div unselectable="on"(.*?)>', source)
    for element in occurences :
        # 1. Use a simpler regex to find all "XXhXX" patterns
        times = re.findall(r'([0-9][0-9]h[0-9][0-9])', element)

        # 2. Check if we found at least two times (start and end)
        if len(times) >= 2 :
            print("------------------------",element)
            print("Found times:", times) # Better debug print
            
            rooms = []
            for prefix in roomPrefix :
                # 3. Use raw strings (r"...") to fix the SyntaxWarning
                room = re.findall(r'{}[0-9]*\[=\"\"'.format(prefix), element)
                room2 = re.findall(r'{}[0-9]*=\"\"'.format(prefix), element)
                room = room + room2
                rooms = rooms + room
            
            # 4. Directly assign times. No need for another regex.
            timeStart = times[0]
            timeEnd = times[1]
            
            okRoom = []
            for elem in room :
                for prefix in roomPrefix :
                    # 3. Use raw strings (r"...") here too
                    x = re.findall(r'{}[0-9]*'.format(prefix), elem)
                    if len(x) > 0 :
                        okRoom.append(x[0])
            
            # print("Ok rooms = {} -- {} - {}".format(okRoom, timeStart, timeEnd))
            for room in okRoom :
                if room not in roomDict :
                    roomDict[room] = [[timeStart, timeEnd]]
                else :
                    roomDict[room].append([timeStart, timeEnd])
            driver.close()

            # Add rooms that are not in the dictionary (i.e., completely free)
            for room in ROOMS:
                if room not in roomDict:
                    roomDict[room] = [] # Represented as an empty list of bookings
                    
            # Output the entire dictionary as a JSON string
            # sort_keys=True ensures the output file is consistent for git diffs
            print(json.dumps(roomDict, indent=2, sort_keys=True))
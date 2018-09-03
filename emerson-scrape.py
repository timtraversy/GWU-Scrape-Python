def create_offering(newOffering):
    classTimesArray = []
    if newOffering.classTimes:
        for classTime in newOffering.classTimes:
            classTime = {
                u'location': classTime.location,
                u'startTime': classTime.startTime,
                u'endTime': classTime.endTime,
                u'sunday': classTime.sunday,
                u'monday': classTime.monday,
                u'tuesday': classTime.tuesday,
                u'wednesday': classTime.wednesday,
                u'thursday': classTime.thursday,
                u'friday': classTime.friday,
                u'saturday': classTime.saturday
            }
            classTimesArray.append(classTime)
    extrasDict = {
        u'Attributes': newOffering.attributes,
        u'Levels':newOffering.levels,
        u'Total Seats': newOffering.totalSeats,
        u'Taken Seats': newOffering.takenSeats,
        u'Total Waitlist Seats': newOffering.totalWaitlistSeats,
        u'Taken Waitlist Seats': newOffering.takenWaitlistSeats
    }
    return {
        u'sectionNumber': newOffering.sectionNumber,
        u'status': newOffering.status,
        u'id': newOffering.id,
        u'instructors': newOffering.instructors,
        u'classTimes': classTimesArray,
        u'extras': extrasDict
    }

class Offering:
    status = None
    levels = None
    id = None
    departmentName = None
    departmentAcronym = None
    departmentNumberString = None
    departmentNumber = None
    sectionNumber = None
    name = None
    credit = None
    classTimes = None
    startDate = None
    endDate = None
    comment = None
    attributes = None
    booksLink = None
    bulletinLink = None
    description = None
    instructors = None
    totalSeats = None
    takenSeats = None
    totalWaitlistSeats = None
    takenWaitlistSeats = None
class ClassTime:
    location = None
    startTime = None
    endTime = None
    sunday = False
    monday = False
    tuesday = False
    wednesday = False
    thursday = False
    friday = False
    saturday = False

import requests
from datetime import datetime
import pytz
from pytz import timezone
eastern = timezone('EST')

import re
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.cloud.exceptions
import urllib

print ("-------- EMERSON COURSE SCRAPE ----------")

cred = credentials.Certificate('./credentials.json')
firebase_admin.initialize_app(cred)
#
db = firestore.client()

# Make request and load offerings
data = {'begin_ap':'a','begin_hh':'0','begin_mi':'0','end_ap':'a','end_hh':'0','end_mi':'0',
'sel_attr':['dummy','%'],'sel_camp':['dummy','%'],'sel_crse':'','sel_day':'dummy','sel_from_cred':'',
'sel_insm':'dummy','sel_instr':['dummy','%'],'sel_levl':['dummy','%'],'sel_ptrm':['dummy','%'],
'sel_schd':['dummy','%'],'sel_sess':'dummy','sel_subj':['dummy','BC','MB','CM','CD','CC','DA','DD','EC',
'EXT','FL','LF','HI','HS','IN','JR','LI','MK','MT','MU','PA','PH','PL','PF','PDE','CE','PS','PB','RL',
'SOC','SA','SC','SW','SO','LS','TH','VM','WDC','WR'],'sel_title':'','sel_to_cred':'','term_in':'201910'}
url = "https://ssb.emerson.edu/PURPLE/bwckschd.p_get_crse_unsec"

# get departments and instructors first
print("Fetching homepage...")
dataHomepage = dict(data)
dataHomepage['sel_subj'] = 'dummy'
r = requests.post(url, data=dataHomepage)
soup = BeautifulSoup(r.content, "html.parser")

unlistedDepts = {
    "Bsns of Creative Enterprises": "BC",
    "Civic Media": "CM",
    "External Program Course": "EXT VAL",
    "Prof Development Experience":"PDE",
    "School of Communication":"SOC",
    "Washington Program":"DC"
}

print("Page fetched. Uploading departments...")
departments = soup.find('td', class_='dedefault').find_all('option')
departmentsArray = []
for department in departments:
    info = department.text.split("(")
    if len(info)>1:
        deptDict = {
            u'departmentAcronym':re.sub('[^A-Z]','', info[1].strip()),
            u'departmentName':info[0].strip()
        }
    else:
        deptDict = {
            u'departmentAcronym':unicode(unlistedDepts[info[0].strip()]),
            u'departmentName':info[0].strip()
        }
    departmentsArray.append(deptDict)

doc_ref = db.collection(u'schools/emerson/lists').document('departments')
doc_ref.set({u'list':departmentsArray})
print("Departments uploaded. Uploading instructors...")

instructors = soup.find('select', attrs={"name": "sel_instr"}).find_all('option')
instructorsArray = []
for p in range(1,len(instructors)):
    instructor = re.sub(' +', ' ',instructors[p].text.strip())
    if not instructor in instructorsArray:
        instructorsArray.append(instructor)
doc_ref = db.collection(u'schools/emerson/lists').document('instructors')
doc_ref.set({u'list':instructorsArray})
print("Instructors uploaded. Uploading courses. Fetching all courses on one page...")

# Long, full networking request
r = requests.post(url, data=data)
print("Page fetched. Parsing and uploading...")
soup = BeautifulSoup(r.content,"html.parser")

# Speedier file test
# file = urllib.urlopen("file:///Users/timtraversy/Google Drive//Development/Course Gnome/code/GWU-Scrape-Python/test.html")
# soup = BeautifulSoup(file,"html.parser")

offering_table = soup.find('table', class_='datadisplaytable')
offerings = offering_table.find_all('tr', recursive=False)

courseArray = []

# Loop over offerings two at a time to get both data pieces
count = 0
for i in range(0,len(offerings),2):

    # Set up offering object
    newOffering = Offering()

    data = offerings[i].text.split(' - ')

    # Hack to account for class names that have a " - "
    offset = 0
    if len(data) > 4:
        concatName = data[0].strip()
        for m in range(1, len(data)-3):
            concatName += " - "
            concatName += data[m].strip()
            offset += 1
        newOffering.name = concatName
    else:
        newOffering.name = data[0].strip()
    if newOffering.name == 'Cancelled':
        continue

    newOffering.id = data[1+offset].strip()
    newOffering.departmentAcronym = data[2+offset].strip().split(' ')[0]
    if newOffering.departmentAcronym == "EXT":
        newOffering.departmentAcronym = unicode("EXT VAL")
        newOffering.departmentName = unicode("External Program Course")
    else:
        for dept in departmentsArray:
            if dept[u'departmentAcronym'] == newOffering.departmentAcronym:
                newOffering.departmentName = dept[u'departmentName']
        newOffering.departmentNumber = data[2+offset].strip().split(' ')[1]
    newOffering.sectionNumber = data[3+offset].strip()

    # Get seat details + status
    url = "https://ssb.emerson.edu" + offerings[i].find('a')['href']
    r = requests.post(url)
    detailSoup = BeautifulSoup(r.content,"html.parser")
    seats = detailSoup.find_all('td', class_="dddefault")

    # Seats
    newOffering.totalSeats = seats[1].text
    newOffering.takenSeats = seats[2].text
    # newOffering.totalWaitlistSeats = seats[4].text
    # newOffering.takenWaitlistSeats = seats[5].text

    # Status
    if newOffering.totalSeats > newOffering.takenSeats:
        newOffering.status = u'OPEN'
    elif newOffering.totalWaitlistSeats == '0':
        newOffering.status = u"CLOSED"
    else:
        newOffering.status = u"WAITLIST"

    # get levels and attributes
    data = offerings[i+1].find_all('span')
    for span in data:
        if span.text.strip() == 'Levels:':
            newOffering.levels = span.next_sibling.strip()
        elif span.text.strip() == 'Attributes:':
            newOffering.attributes = span.next_sibling.strip()

    # Credits
    catalog_entry = offerings[i+1].find('a')
    credits = catalog_entry.previous_sibling.previous_sibling.previous_sibling.strip()
    credits = re.sub('Credits','', credits).strip()
    credits = re.sub('\.0+','', credits).strip()
    credits = re.sub('OR','or', credits)
    credits = re.sub('TO','to', credits)
    credits = re.sub(' +',' ', credits)
    newOffering.credit = unicode(credits)

    # Description from catalog entry
    url = "https://ssb.emerson.edu" + catalog_entry['href']
    r = requests.post(url)
    catalogSoup = BeautifulSoup(r.content,"html.parser")
    newOffering.description = catalogSoup.find('td', class_="ntdefault").text.split('\n')[1].strip()

    #Class Times
    instructors = []
    classTimes=[]
    class_time_table = offerings[i+1].find('table',class_='datadisplaytable')
    if class_time_table:
        class_time_table = class_time_table.find_all('tr')
        for j in range(1,len(class_time_table)):
            newClassTime = ClassTime()
            details = class_time_table[j].find_all('td',class_='dddefault')
            for k in range (1,len(details)):
                text = details[k].text.strip()
                valid = True
                if k == 1:
                    if text != 'TBA':
                        times = text.split('-')
                        newClassTime.startTime = eastern.localize(datetime.strptime(times[0].strip(), '%I:%M %p'))
                        newClassTime.endTime = eastern.localize(datetime.strptime(times[1].strip(), '%I:%M %p'))
                    else:
                        valid = False
                        break
                if k == 2:
                    if 'U' in text:
                        newClassTime.sunday = True
                    if 'M' in text:
                        newClassTime.monday = True
                    if 'T' in text:
                        newClassTime.tuesday = True
                    if 'W' in text:
                        newClassTime.wednesday = True
                    if 'R' in text:
                        newClassTime.thursday = True
                    if 'F' in text:
                        newClassTime.friday = True
                    if 'S' in text:
                        newClassTime.saturday = True
                if k == 3:
                    # location
                    newClassTime.location = text
                if k == 6:
                    insts = re.sub('\([A-z]\)','', text).split(',')
                    for inst in insts:
                        if inst == "TBA":
                            instructors = None
                            break
                        newInst = inst.strip()
                        if not newInst in instructors:
                            instructors.append(newInst)
            if valid:
                classTimes.append(newClassTime)

    if classTimes:
        newOffering.classTimes = classTimes

    if instructors:
        newOffering.instructors = instructors

    courseArray.append(newOffering)
    print('Parsed: {id}, Count:{len}'.format(id=unicode(newOffering.id), len=len(courseArray)))

count = 0
for indx, course in enumerate(courseArray):
    offeringsArray = [create_offering(course)]
    index = indx + 1
    while index < len(courseArray):
        courseTwo = courseArray[index]
        if (course.name == courseTwo.name and course.departmentNumber == courseTwo.departmentNumber and course.departmentAcronym == courseTwo.departmentAcronym):
            offeringsArray.append(create_offering(courseTwo))
            del courseArray[index]
        index += 1
    dictionary = {
        u'departmentName': course.departmentName,
        u'departmentAcronym': course.departmentAcronym,
        u'departmentNumber': course.departmentNumber,
        u'name': course.name,
        u'credit': course.credit,
        u'description': course.description,
        u'offerings': offeringsArray,
    }

    identifier = unicode(course.departmentAcronym + str(course.departmentNumber))
    db.collection(u'schools/emerson/fall2018_courses').document(identifier).set(dictionary)
    count += 1
    print('Uploaded ({count}/{total}): {id}'.format(count=count, total=len(courseArray), id=course.id))

# Updating version number
doc_ref = db.collection(u'schools').document(u'emerson')
try:
    doc = doc_ref.get()
    version = doc.to_dict()['version']
    print(u'Updating from version {}'.format(doc.to_dict()['version']))
    doc_ref.set({u'version':version + 1})
except google.cloud.exceptions.NotFound:
    print(u'No metadata, something is wrong.')
    exit(1)


print ("----- EMERSON COURSE SCRAPE COMPLETE ------")

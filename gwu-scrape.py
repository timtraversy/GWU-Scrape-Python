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
        u'Start Date': newOffering.startDate,
        u'End Date': newOffering.endDate,
        u'Comment': newOffering.comment,
        u'Attributes': newOffering.attributes,
        u'Books Link': newOffering.booksLink,
        u'Bulletin Link': newOffering.bulletinLink
    }
    return {
        u'sectionNumber': newOffering.sectionNumber,
        u'status': newOffering.status,
        u'id': newOffering.crn,
        u'instructors': newOffering.instructors,
        u'classTimes': classTimesArray,
        u'extras': extrasDict
    }

class Offering:
    status = None
    crn = None
    departmentAcronym = None
    departmentName = None
    departmentNumberString = None
    departmentNumber = None
    sectionNumber = None
    name = None
    credit = None
    instructors = None
    classTimes = None
    startDate = None
    endDate = None
    comment = None
    attributes = None
    booksLink = None
    bulletinLink = None
    description = None
    offerings = None
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
import re
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.cloud.exceptions

print ("-------- GWU COURSE SCRAPE ----------")

cred = credentials.Certificate('./credentials.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

# get departments and instructors first
print("Fetching page...")
r = requests.post("https://my.gwu.edu/mod/pws/coursesearch.cfm")
soup = BeautifulSoup(r.content, "html.parser")

print("Page fetched. Uploading departments...")
departments = soup.find('select', attrs={"name": "dept"}).find_all('option')
departmentsArray = []
for x in range(1,len(departments)):
    deptDict = {
        u'departmentAcronym':departments[x]['value'],
        u'departmentName':departments[x].text.strip()
    }
    departmentsArray.append(deptDict)
doc_ref = db.collection(u'schools/gwu/lists').document('departments')
doc_ref.set({u'list':departmentsArray})
print("Departments uploaded. Parsing each seach result page...")

# Get instructors as we go
instructorsArray = []

# Starting search indices and offering counter (901-1000)
startIndex = 901
endIndex = 1000
count = 0

# Array for all courses
courseArray = []

while True:
    print "Index: ", startIndex, " - ", endIndex
    print "Count: ", count
    pageNum = 1
    while True:
        print "Page:", pageNum
        # Make request and load offerings
        r = requests.post('https://my.gwu.edu/mod/pws/searchresults.cfm',
            data = {'term':'201803',
                    'Submit':'Search',
                    'campus':'1',
                    'srchType':'All',
                    'courseNumSt': startIndex,
                    'courseNumEn': endIndex,
                    'PageNum':pageNum})
        c = r.content
        soup = BeautifulSoup(c,"html.parser")
        offerings = soup.find_all('table', class_='courseListing')

        # Loop over offerings
        for offering in offerings:

            # Set up offering object
            newOffering = Offering()

            # Get row one
            offeringRowOne = offering.find_all("tr")[0]

            # Get cells in row one
            cells = offeringRowOne.find_all("td")

            # Status
            status = cells[0].text.strip()
            if status == 'OPEN':
                newOffering.status = u'OPEN'
            elif status == 'CLOSED':
                newOffering.status = u"CLOSED"
            elif status == 'WAITLIST':
                newOffering.status = u"WAITLIST"
            elif status == 'CANCELLED':
                continue

            # Crn
            crn = cells[1].text.strip()
            if crn:
                newOffering.crn = crn

            # Deparment and Number
            subject = cells[2].text.strip().split()[0]
            if subject:
                newOffering.departmentAcronym = subject
                for dept in departmentsArray:
                    if dept[u'departmentAcronym'] == newOffering.departmentAcronym:
                        newOffering.departmentName = dept[u'departmentName']
            # newOffering.setDepartmentName
            number = cells[2].text.strip().split()[1]
            if number:
                newOffering.departmentNumberString = number
                newOffering.departmentNumber = (int(re.sub('[^0-9]','', number)))

            # Get description and link
            bulletinLink = cells[2].find_next("a")['href']
            newOffering.bulletinLink = bulletinLink
            descriptionResults = requests.get(bulletinLink)
            descriptionContent = descriptionResults.content
            descriptionSoup = BeautifulSoup(descriptionContent, "html.parser")
            description = descriptionSoup.find_all("p", class_="courseblockdesc")
            if (description):
                newOffering.description = description[0].text
            # offerings = soup.find_all('table', class_='courseListing')

            # Section Number
            sectionNumber = cells[3].text.strip()
            if sectionNumber:
                newOffering.sectionNumber = sectionNumber

            # Name
            name = cells[4].text.strip()
            if name:
                newOffering.name = name

            # Credit
            credit = re.sub('[^0-9]','',cells[5].text.strip().split(".")[0])
            if credit:
                newOffering.credit = int(credit)

            # Instructors
            instructors = cells[6].text.strip().split(';')
            instructorList = []
            for instructor in instructors:
                if instructor:
                    instructorList.append(instructor)
            if instructorList:
                newOffering.instructors = instructorList
            else:
                newOffering.instructors = None

            # Class times

            # Declare array to hold them
            classTimes = []

            # Get location
            for location in cells[7].find_all("a"):
                classTime = ClassTime()
                classTimes.append(classTime)
                newLocation = location.text
                newLocation += location.nextSibling
                classTime.location = newLocation

            # Get times
            for (index, time) in enumerate(cells[8].find_all("br")[::3]):
                # If time exists that there was no location for, make new time
                if index == len(classTimes):
                    classTime = ClassTime()
                    classTimes.append(classTime)

                days = time.previousSibling
                if 'U' in days:
                    classTimes[index].sunday = True
                if 'M' in days:
                    classTimes[index].monday = True
                if 'T' in days:
                    classTimes[index].tuesday = True
                if 'W' in days:
                    classTimes[index].wednesday = True
                if 'R' in days:
                    classTimes[index].thursday = True
                if 'F' in days:
                    classTimes[index].friday = True
                if 'S' in days:
                    classTimes[index].saturday = True

                startTime = datetime.strptime(time.nextSibling.split(" - ")[0], '%I:%M%p')
                endTime = datetime.strptime(time.nextSibling.split(" - ")[1], '%I:%M%p')

                eastern = timezone('EST')
                classTimes[index].startTime = eastern.localize(startTime)
                classTimes[index].endTime = eastern.localize(endTime)

            if classTimes:
                newOffering.classTimes = classTimes

            # Dates
            startDate = cells[9].text.strip().split(" - ")[0]
            if startDate:
                newOffering.startDate = startDate

            endDate = cells[9].text.strip().split(" - ")[1]
            if endDate:
                newOffering.endDate = endDate

            # Next row
            offeringRowTwo = offering.find_all("tr")[1]
            cells = offeringRowTwo.find_all("td")

            # Comments and Attributes
            for index, div in enumerate(cells[0].find_all("div")):
                if "Comments" in div.text:
                    newOffering.comment = re.sub('Comments: ', '', div.text)
                if "Course Attributes" in div.text:
                    courseAttributes = cells[0].find_all("div")[index+1].find_all("tr")
                    attributeString = ""
                    for attribute in courseAttributes:
                        attributeString += re.sub(':', '', attribute.find_next("td").text).strip()
                        attributeString += ', '
                    attributeString = attributeString[:-2]
                    newOffering.attributes = attributeString

            # BOOKS LINK
            newOffering.booksLink = (cells[2].find_next("a")['href'])
            courseArray.append(newOffering)

            count += 1

        if ('Next Page' not in soup.body.text):
            break

        pageNum+=1

    # Break here if just testing and don't want whole set
    # break
    startIndex += 100
    endIndex += 100
    if endIndex > 10000:
        break

print("All courses parsed. Sorting, combining, and uploading courses...")

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

    identifier = course.departmentAcronym + str(course.departmentNumber)
    db.collection(u'schools/gwu/fall2018_courses').document(unicode(identifier)).set(dictionary)
    count += 1
    print('Uploaded ({count}/{total}): {id}'.format(count=count, total=len(courseArray), id=course.crn))


print "Done uploading courses, total= ", count

# Instructor upload
print "Uploading instructors..."
doc_ref = db.collection(u'schools/gwu/lists').document('instructors')
doc_ref.set({u'list':instructorsArray})
print "Instructors uploaded"

# Updating version number
doc_ref = db.collection(u'schools').document(u'gwu')
try:
    doc = doc_ref.get()
    version = doc.to_dict()['version']
    print(u'Updating from version {}'.format(doc.to_dict()['version']))
    doc_ref.set({u'version':version + 1})
except google.cloud.exceptions.NotFound:
    print(u'No metadata, something is wrong.')
    exit(1)

print ("----- GWU COURSE SCRAPE COMPLETE -------")

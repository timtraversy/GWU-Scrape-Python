class Offering:
    status = None
    crn = None
    departmentAcronym = None
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

cred = credentials.Certificate('./credentials.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

# Increment version counter
doc_ref = db.collection(u'schools').document(u'gwu')
try:
    doc = doc_ref.get()
    version = doc.to_dict()['version'] + 1
    db.collection(u'schools').document(u'gwu').set({u'version': version})
except google.cloud.exceptions.NotFound:
    print(u'No such document!')

# Starting search indices and offering counter
startIndex = 2601
endIndex = 2700
count = 0

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
                newOffering.status = True
            elif status == 'CLOSED':
                newOffering.status = False
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
            instructors = cells[6].text.strip()
            if instructors:
                newOffering.instructors = instructors

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

            classTimesDict = []
            if classTimes:
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
                    classTimesDict.append(classTime)

            dictionary = {
                u'status': newOffering.status,
                # u'departmentName': newOffering.departmentName,
                u'departmentAcronym': newOffering.departmentAcronym,
                u'departmentNumber': newOffering.departmentNumber,
                u'departmentNumberString': newOffering.departmentNumberString,
                u'sectionNumber': newOffering.sectionNumber,
                u'name': newOffering.name,
                u'credit': newOffering.credit,
                u'instructors': newOffering.instructors,
                u'startDate': newOffering.startDate,
                u'endDate': newOffering.endDate,
                u'comment': newOffering.comment,
                u'attributes': newOffering.attributes,
                u'booksLink': newOffering.booksLink,
                u'classTimes': classTimesDict,
                u'description': newOffering.description,
                u'bulletinLink': newOffering.bulletinLink
            }

            doc_ref = db.collection(u'schools/gwu/seasons/fall2018/offerings').document(newOffering.crn)
            doc_ref.set(dictionary)

            print "Added", newOffering.name
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

print "Total= ", count

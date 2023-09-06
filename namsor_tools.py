import sys

import uuid
import getopt
import argparse

import hashlib
import argparse
import os.path
from synchronized_set import SynchronizedSet
from argparse import ArgumentError

import logging
from namsor_exception import NamSorToolException

#API imports
import openapi_client
from openapi_client.apis.tags import admin_api
from openapi_client.apis.tags import personal_api
from openapi_client import ApiClient
from openapi_client.apis.tags import indian_api
from openapi_client.rest import ApiException

#import models
from openapi_client.models import BatchFirstLastNameDiasporaedOut
from openapi_client.models import BatchFirstLastNameGenderedOut
from openapi_client.models import BatchFirstLastNameGeoIn
from openapi_client.models import BatchPersonalNameGeoSubdivisionIn
from openapi_client.models import BatchFirstLastNameIn
from openapi_client.models import BatchFirstLastNameOriginedOut
from openapi_client.models import BatchFirstLastNameUSRaceEthnicityOut
from openapi_client.models import BatchPersonalNameGenderedOut
from openapi_client.models import BatchPersonalNameGeoIn
from openapi_client.models import BatchPersonalNameIn
from openapi_client.models import BatchPersonalNameParsedOut
from openapi_client.models import FirstLastNameGeoSubclassificationOut
from openapi_client.models import FirstLastNameDiasporaedOut
from openapi_client.models import FirstLastNameGenderedOut
from openapi_client.models import PersonalNameGeoOut
from openapi_client.models import FirstLastNameGeoIn
from openapi_client.models import FirstLastNameIn
from openapi_client.models import FirstLastNameOriginedOut
from openapi_client.models import FirstLastNameUSRaceEthnicityOut
from openapi_client.models import PersonalNameGenderedOut
from openapi_client.models import PersonalNameReligionedOut
from openapi_client.models import PersonalNameCastegroupOut

from openapi_client.models import PersonalNameGeoIn
from openapi_client.models import PersonalNameGeoSubdivisionIn
from openapi_client.models import PersonalNameSubdivisionIn
from openapi_client.models import PersonalNameIn
from openapi_client.models import PersonalNameParsedOut

# From v2.0.27, output file is named .namsor_py.txt
NAMSOR_EXT = ".namsor_py.txt"

DEFAULT_DIGEST_ALGO = "MD5"

BATCH_SIZE = 100

NAMSOR_OPTION_USRACEETHNICITY_TAXO = "X-OPTION-USRACEETHNICITY-TAXONOMY"
NAMSOR_OPTION_USRACEETHNICITY_TAXO_4CLASSES = "USRACEETHNICITY-4CLASSES"
NAMSOR_OPTION_USRACEETHNICITY_TAXO_4CLASSESCLASSIC = "USRACEETHNICITY-4CLASSES-CLASSIC"
NAMSOR_OPTION_USRACEETHNICITY_TAXO_6CLASSES = "USRACEETHNICITY-6CLASSES"
NAMSOR_OPTION_RELIGION_STATS = "X-OPTION-RELIGION-STATS"


INPUT_DATA_FORMAT_FNLN  = "fnln"
INPUT_DATA_FORMAT_FNLNGEO = "fnlngeo"
INPUT_DATA_FORMAT_FULLNAME = "name"
INPUT_DATA_FORMAT_FULLNAMEGEO = "namegeo"
INPUT_DATA_FORMAT_FULLNAMEGEOSUB = "namegeosub"

INPUT_DATA_FORMAT = [
    INPUT_DATA_FORMAT_FNLN,
    INPUT_DATA_FORMAT_FNLNGEO,
    INPUT_DATA_FORMAT_FULLNAME,
    INPUT_DATA_FORMAT_FULLNAMEGEO,
    INPUT_DATA_FORMAT_FULLNAMEGEOSUB
]

INPUT_DATA_FORMAT_HEADER = [
    ["firstName", "lastName"],
    ["firstName", "lastName", "countryIso2"],
    ["fullName"],
    ["fullName", "countryIso2"],
    ["fullName", "countryIso2","subDivisionIso31662"], 
]

SERVICE_NAME_PARSE = "parse"
SERVICE_NAME_GENDER = "gender"
SERVICE_NAME_ORIGIN = "origin"
SERVICE_NAME_COUNTRY = "country"
SERVICE_NAME_RELIGION = "religion"
SERVICE_NAME_CASTEGROUP = "castegroup"
SERVICE_NAME_DIASPORA = "diaspora"
SERVICE_NAME_USRACEETHNICITY = "usraceethnicity"
SERVICE_NAME_SUBDIVISION = "subdivision"

SERVICES = [
    SERVICE_NAME_PARSE,
    SERVICE_NAME_GENDER,
    SERVICE_NAME_ORIGIN,
    SERVICE_NAME_COUNTRY,
    SERVICE_NAME_RELIGION,
    SERVICE_NAME_CASTEGROUP,
    SERVICE_NAME_DIASPORA,
    SERVICE_NAME_USRACEETHNICITY,
    SERVICE_NAME_SUBDIVISION    
]

OUTPUT_DATA_PARSE_HEADER = ["firstNameParsed", "lastNameParsed", "nameParserType", "nameParserTypeAlt", "nameParserTypeScore", "script"]
OUTPUT_DATA_GENDER_HEADER = ["likelyGender", "probabilityCalibrated", "likelyGenderScore", "genderScale", "script"]
OUTPUT_DATA_ORIGIN_HEADER  = ["region", "topRegion", "subRegion", "countryOrigin", "countryOriginAlt", "probabilityCalibrated", "probabilityAltCalibrated", "countryOriginScore", "countryOriginTop", "script"]
OUTPUT_DATA_COUNTRY_HEADER = ["region","topRegion","subRegion","country", "countryAlt", "probabilityCalibrated", "probabilityCalibratedAlt", "countryScore", "countryTop", "script"]
OUTPUT_DATA_RELIGION_HEADER = ["religion", "religionAlt", "probabilityCalibrated", "probabilityCalibratedAlt", "religionScore", "religionsTop", "script"]
OUTPUT_DATA_CASTEGROUP_HEADER = ["castegroup", "castegroupAlt", "probabilityCalibrated", "probabilityCalibratedAlt", "castegroupScore", "castegroupsTop", "script"]
OUTPUT_DATA_DIASPORA_HEADER = ["ethnicity", "ethnicityAlt", "probabilityCalibrated", "probabilityCalibratedAlt", "ethnicityScore", "script"]
OUTPUT_DATA_USRACEETHNICITY_HEADER = ["raceEthnicity", "raceEthnicityAlt", "probabilityCalibrated", "probabilityCalibratedAlt",  "raceEthnicityScore", "raceEthnicityTop", "script"]
OUTPUT_DATA_SUBDIVISION_HEADER = ["subClassification", "subClassificationAlt", "probabilityCalibrated", "probabilityCalibratedAlt", "subclassificationScore", "subclassificationTop", "script"]
OUTPUT_DATA_RELIGIONSTAT_HEADER = ["religion", "religionPct", "religionAlt", "religionAltPct"]

OUTPUT_DATA_HEADERS = [
    OUTPUT_DATA_PARSE_HEADER,
    OUTPUT_DATA_GENDER_HEADER,
    OUTPUT_DATA_ORIGIN_HEADER,
    OUTPUT_DATA_COUNTRY_HEADER,
    OUTPUT_DATA_RELIGION_HEADER,
    OUTPUT_DATA_CASTEGROUP_HEADER,
    OUTPUT_DATA_DIASPORA_HEADER,
    OUTPUT_DATA_USRACEETHNICITY_HEADER,
    OUTPUT_DATA_SUBDIVISION_HEADER
]

rowId = 0


class NamsorTools:

    def __init__(self, commandLineOptions):

        self.__done = SynchronizedSet(set(), synchronized=True)

        self.__separatorOut = "|"
        self.__separatorIn = "|"


        self.__TIMEOUT = 30000
        self.__withUID = False
        self.__recover = False
        self.__digest = None
        self.__religionoption = False
        self.__usraceethnicityoption = None

        self.__firstLastNamesGeoIn = {}
        self.__firstLastNamesIn = {}
        self.__personalNamesIn = {}
        self.__personalNamesGeoIn = {}
        self.__personalNamesGeoSubIn = {}

        self.__commandLineOptions = commandLineOptions

        configuration = openapi_client.Configuration()
        configuration.api_key['X-API-KEY'] = commandLineOptions["apiKey"]
        configuration.__TIMEOUT = self.__TIMEOUT
        
        if commandLineOptions["usraceethnicityoption"] :
            self.__client = ApiClient(configuration,NAMSOR_OPTION_USRACEETHNICITY_TAXO,commandLineOptions["usraceethnicityoption"])
            self.__usraceethnicityoption = commandLineOptions["usraceethnicityoption"]
        else :
            self.__client = ApiClient(configuration)

        if commandLineOptions["religionoption"] :
            # add a new http header for religion stats to API client
            self.__client.set_default_header(NAMSOR_OPTION_RELIGION_STATS, "True")
            self.__religionoption = True
        
        # need to explicitely set API Key (was previously part of configuration)
        self.__client.set_default_header('X-API-KEY', commandLineOptions["apiKey"])


        self.__api = personal_api.PersonalApi(self.__client)
        self.__indianApi = indian_api.IndianApi(self.__client)
        self.__adminApi = admin_api.AdminApi(self.__client)
        self.__withUID = commandLineOptions["uid"]

        self.__recover = commandLineOptions["recover"]


        if commandLineOptions["digest"]:
            try:
                self.__digest = hashlib.md5()
            except Exception as ex:
                logging.getLogger(NamsorTools.__class__.__name__).log(logging.CRITICAL, "Digest algo not found " + DEFAULT_DIGEST_ALGO, ex)


    def digest(self, inClear:str):
        if self.getDigest() == None or inClear == None or inClear == '':
            return inClear
        else:
            self.__digest.update(inClear.encode())
            hashbytes = self.__digest.digest()

            return hashbytes.hex()


    #TODO : line 433
    def process(self,service,reader,writer,softwareNameAndVersion):
        
        lineId = 0
        inputDataFormat = self.__commandLineOptions["inputDataFormat"]
        inputHeaders = None
        for i in range( len(INPUT_DATA_FORMAT)):
            if (INPUT_DATA_FORMAT[i]==inputDataFormat):
                inputHeaders = INPUT_DATA_FORMAT_HEADER[i]
                break
        if inputHeaders == None:
            raise NamSorToolException("Invalid inputFileFormat " + inputDataFormat)
        outputHeaders = None
        for i in range(len(SERVICES)):
            if (SERVICES[i]==service):
                outputHeaders = OUTPUT_DATA_HEADERS[i]
                break
        if (outputHeaders == None):
            raise NamSorToolException("Invalid service " + service)
        appendHeader = "header" in self.getCommandLineOptions()

        if (appendHeader and not self.isRecover()) or (self.isRecover() and not self.__done):
            self.appendHeader(writer, inputHeaders, outputHeaders)

        dataLenExpected = len(inputHeaders) + 1 if self.isWithUID() else len(inputHeaders)

        dataFormatExpected = ""

        if self.isWithUID():
            dataFormatExpected += "uid" + self.__separatorIn

        countryIso2Default = self.getCommandLineOptions()["countryIso2"]

        for i in range (len(inputHeaders)):
            dataFormatExpected += inputHeaders[i]
            if (i < len(inputHeaders) - 1):
                dataFormatExpected+=(self.__separatorIn)

        line = reader.readline()

        while(line):
            if (line and not line.startswith("#")):

                if line.endswith("|"):
                    line = line + " "
                lineData = line.split("|")

                if len(lineData) != dataLenExpected:
                    raise NamSorToolException("Line " + str(lineId) + ", expected input with format : " + dataFormatExpected + " line = " + line)

                uid = ""

                col = 0

                if (self.isWithUID()):
                    uid = lineData[col]
                    col+=1
                else:
                    # generate a uuid
                    uid = str(uuid.uuid4())                    
                if (self.isRecover() and uid in self.__done):
                    pass
                else:
                    if (inputDataFormat == INPUT_DATA_FORMAT_FNLN):
                        firstName = lineData[col]
                        col+=1
                        lastName = lineData[col]
                        col+=1
                        firstLastNameIn = FirstLastNameIn(
                        id = uid,
                        firstName = firstName,
                        lastName = str(lastName.replace("\n",""))
                        )
                        self.__firstLastNamesIn[uid] = firstLastNameIn
                    elif inputDataFormat == INPUT_DATA_FORMAT_FNLNGEO :
                        firstName = lineData[col]
                        col+=1
                        lastName = lineData[col]
                        col+=1
                        countryIso2 = lineData[col]
                        col+=1
                        if ((countryIso2 == None or not countryIso2.strip()) and countryIso2Default != None):
                            countryIso2 = countryIso2Default
                        firstLastNameGeoIn = FirstLastNameGeoIn(
                        id = uid,
                        first_name = firstName,
                        last_name = lastName.replace("\n","")
                        )
                        firstLastNameGeoIn.country_iso2 = countryIso2.replace("\n","")
                        self.__firstLastNamesGeoIn[uid] = firstLastNameGeoIn
                    elif inputDataFormat == INPUT_DATA_FORMAT_FULLNAME :
                        fullName = lineData[col]
                        col+=1
                        personalNameIn = PersonalNameIn(
                        id = uid,
                        name = fullName.replace("\n","")
                        )
                        self.__personalNamesIn[uid] = personalNameIn
                    elif (inputDataFormat == INPUT_DATA_FORMAT_FULLNAMEGEO):
                        fullName = lineData[col]
                        col+=1
                        countryIso2 = lineData[col]
                        col+=1
                        if ((countryIso2 == None) or not countryIso2.strip()) and countryIso2Default != None:
                            countryIso2 = countryIso2Default
                        personalNameGeoIn = PersonalNameGeoIn(
                        id = uid,
                        name = fullName.replace("\n",""),
                        country_iso2 = countryIso2.replace("\n","")
                        )
                        self.__personalNamesGeoIn[uid] = personalNameGeoIn
                    elif (inputDataFormat == INPUT_DATA_FORMAT_FULLNAMEGEOSUB):
                        fullName = lineData[col]
                        col+=1
                        countryIso2 = lineData[col]
                        col+=1
                        if ((countryIso2 == None) or not countryIso2.strip()) and countryIso2Default != None:
                            countryIso2 = countryIso2Default
                        subDivisionIso31662 = lineData[col]
                        col+=1
                        personalNameGeoIn = PersonalNameGeoSubdivisionIn(
                        id = uid,
                        name = fullName.replace("\n",""),
                        country_iso2 = countryIso2.replace("\n","")
                        )
                        personalNameGeoIn.subdivision_iso = subDivisionIso31662.replace("\n","")
                        self.__personalNamesGeoSubIn[uid] = personalNameGeoIn


                    self.processData(service, outputHeaders, writer, False, softwareNameAndVersion)

            lineId+=1
            line = reader.readline()

        self.processData(service, outputHeaders, writer, True, softwareNameAndVersion)


    def getCommandLineOptions(self):
        return self.__commandLineOptions


    def run(self):

        apiKey = self.getCommandLineOptions()["apiKey"]
        if apiKey==None or not apiKey:
            raise NamSorToolException("Missing API KEY")
        softwareNameAndVersion = None
        try:
            softwareNameAndVersion = self.__adminApi.software_version().body['softwareNameAndVersion']
            print("NamSor software name and version : ", softwareNameAndVersion)
        except ApiException as ex:
            logging.getLogger(NamsorTools.__class__.__name__).log(logging.CRITICAL, None, ex)
            raise NamSorToolException("Can't get the API version " + ex)


        try:
            service = self.getCommandLineOptions()["service"]
            inputFileName = self.getCommandLineOptions()["inputFile"]

            if(inputFileName==None or not inputFileName):
                raise NamSorToolException("Missing inputFile")
            inputFile = None

            try:
                inputFile = open(inputFileName,'r')
            except:
                raise NamSorToolException("Can't read inputFile " + inputFileName)

            outputFileName = self.getCommandLineOptions()["outputFile"]
            if(outputFileName==None or not outputFileName):
                outputFileName = inputFileName + "." + service + ("_"+self.__usraceethnicityoption if self.__usraceethnicityoption!=None else "") + ("_religion" if self.__religionoption else "") + (".digest" if self.__digest!=None else "") + NAMSOR_EXT
                logging.getLogger(NamsorTools.__class__.__name__).info("Outputing to " + outputFileName)

            outputFile = open(outputFileName,'w+')

            outputFileOverwrite =  self.getCommandLineOptions()["overwrite"]
            if os.path.exists(outputFileName) and not outputFileOverwrite and not self.isRecover():
                raise NamSorToolException("OutputFile " + inputFileName + " already exists, use -r to recover and continue job")
            if outputFileOverwrite and self.isRecover():
                raise NamSorToolException("You can overwrite OR recover to " + inputFileName)
            if self.isRecover() and not self.isWithUID():
                raise  NamSorToolException("You can't recover without a uid " + inputFileName)
            encoding = self.getCommandLineOptions()["encoding"]
            if encoding==None or not encoding:
                encoding = "UTF-8"
            if self.isRecover() and os.path.exists(inputFileName):
                logging.getLogger(NamsorTools.__class__.__name__).info("Recovering from existing " + outputFileName)
                print("Recovering from existing " + outputFileName)
                readerDone = open(inputFileName,'r',encoding=encoding)

                doneLine = readerDone.readline()
                line = 0
                length = 1
                while(doneLine):
                    if not doneLine.startswith("#") and not doneLine:
                        existingData = doneLine.split("|")
                        if length<0:
                            length = len(existingData)
                        elif length != len(existingData):
                            logging.getLogger(NamsorTools.__class__.__name__).warning("Line " + str(line) + " doneLine=" + doneLine + " len=" + str(existingData.length) + "!=" + str(length))
                        self.__done.add(existingData[0])
                    doneLine = readerDone.readline()
                    if line%1000 == 0:
                        logging.getLogger(NamsorTools.__class__.__name__).info("Loading from existing " + outputFileName + ":" + str(line))
                        print("Loading from existing " + outputFileName + ":" + str(line))
                    line+=1
                readerDone.close()

            reader = open(inputFileName,'r',encoding = encoding)
            mode = 'a' if self.isRecover() else 'w'

            writer = open(outputFileName,mode,encoding=encoding)

            self.process(service,reader,writer,softwareNameAndVersion)

        except Exception as ex:
            logging.getLogger(NamsorTools.__class__.__name__).log(logging.CRITICAL, ex)
            sys.exit(1)


    def appendHeader(self, writer, inputHeaders, outputHeaders):
        writer.write('#uid' + self.__separatorOut)

        for inputHeader in inputHeaders:
            writer.write(inputHeader + self.__separatorOut)

        for outputHeader in outputHeaders:
            writer.write(outputHeader + self.__separatorOut)
        if(self.__religionoption) :
            for outputHeader in OUTPUT_DATA_RELIGIONSTAT_HEADER :
                writer.write(outputHeader + self.__separatorOut)        
        writer.write('version' + self.__separatorOut)
        writer.write('rowId'+"\n")


    #names -> list[FirstLastNameGeoIn]
    def processDiaspora(self, names):
        result = {}
        body = BatchFirstLastNameGeoIn(
        personalNames = names
        )
        origined:BatchFirstLastNameDiasporaedOut = self.__api.diaspora_batch(body=body)

        for personalName in origined.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[FirstLastNameGeoIn]
    def processOriginGeo(self, names):
        namesNoGeo = []
        for name in names:
            nameNoGeo = FirstLastNameIn(
            id = name.id,
            firstName = name.first_name,
            lastName = name.last_name
            )
            namesNoGeo.append(nameNoGeo)

        return self.processOrigin(namesNoGeo)

    
    #names -> list[FirstLastNameIn]
    def processOrigin(self, names):
        result = {}
        body = BatchFirstLastNameIn(
        personalNames = names
        )
        origined = self.__api.origin_batch(body=body)

        for personalName in origined.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result


    #names -> list[FirstLastNameIn]
    def processGender(self, names):
        result = {}
        body = BatchFirstLastNameIn(
            personalNames = names
        )
        gendered = self.__api.gender_batch(body=body)

        for personalName in gendered.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[PersonalNameIn]
    def processGenderFull(self, names):
        result = {}
        body = BatchPersonalNameIn(
            personalNames = names
        )
        gendered = self.__api.gender_full_batch(body=body)

        for personalName in gendered.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[PersonalNameIn]
    def processCountry(self, names):
        result = {}
        body = BatchPersonalNameIn(
            personalNames = names
        )
        countries = self.__api.country_batch(body=body)

        for personalName in countries.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[PersonalNameGeoIn]
    def processGenderFullGeo(self, names):
        result = {}
        body = BatchPersonalNameGeoIn(
            personalNames = names
        )
        gendered = self.__api.gender_full_geo_batch(body=body)

        for personalName in gendered.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[PersonalNameGeoSubIn]
    def processReligion(self, names):
        result = {}
        body = BatchPersonalNameGeoSubdivisionIn(
            personalNames = names
        )
        religioned = self.__api.religion_full_batch(body=body)

        for personalName in religioned.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    # create an adapter for an array of PersonalNameGeoSubdivisionIn to be transformed into an array of PersonalNameSubdivisionIn
    #names -> list[PersonalNameGeoSubdivisionIn]
    def adaptIndia(self, names):

        result = []
        for name in names:
            nameNoGeo = PersonalNameSubdivisionIn(
            id = name.id,
            name = name.name,
            subdivisionIso = name.subdivision_iso
            )
            result.append(nameNoGeo)
        return result


    #names -> list[PersonalNameGeoSubIn]
    def processCastegroup(self, names):
        result = {}
        body = BatchPersonalNameGeoSubdivisionIn(
            personalNames = self.adaptIndia(names)
        )
        religioned = self.__indianApi.castegroup_indian_full_batch(body=body)

        for personalName in religioned.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result



    #names -> list[PersonalNameIn]
    def processParse(self, names):
        result = {}
        body = BatchPersonalNameIn(
            personalNames = names
        )
        parsed = self.__api.parse_name_batch(body=body)

        for personalName in parsed.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[FirstLastNameGeoIn]
    def processGenderGeo(self, names):
        result = {}
        body = BatchFirstLastNameGeoIn(
            personalNames = names
        )
        gendered = self.__api.gender_geo_batch(body=body)

        for personalName in gendered.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[FirstLastNameGeoIn]
    def processSubdivision(self, names):
        result = {}
        body = BatchFirstLastNameGeoIn(
            personalNames = names
        )
        subdivisioned = self.__api.subclassification_batch(body=body)

        for personalName in subdivisioned.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[PersonalNameGeoIn]
    def processParseGeo(self, names):
        result = {}
        body = BatchPersonalNameGeoIn(
            personalNames = names
        )
        parsed = self.__api.parse_name_geo_batch(body=body)

        for personalName in parsed.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result

    #names -> list[FirstLastNameGeoIn]
    def processUSRaceEthnicity(self, names):
        result = {}
        body = BatchFirstLastNameGeoIn(
            personalNames = names
        )
        racedEthnicized = self.__api.us_race_ethnicity_batch(body=body)

        for personalName in racedEthnicized.body["personalNames"]:
            result[personalName["id"]] = personalName

        return result


    def processData(self, service:str, outputHeaders, writer, flushBuffers, softwareNameAndVersion):
        if(flushBuffers and len(self.__firstLastNamesIn) != 0 or len(self.__firstLastNamesIn) >= BATCH_SIZE):
            if service == SERVICE_NAME_ORIGIN:
                origins = self.processOrigin(list(self.__firstLastNamesIn.values()))
                self.append(writer, outputHeaders, self.__firstLastNamesIn, origins, softwareNameAndVersion)
            elif service == SERVICE_NAME_GENDER:
                genders = self.processGender(list(self.__firstLastNamesIn.values()))
                self.append(writer, outputHeaders, self.__firstLastNamesIn, genders, softwareNameAndVersion)
            self.__firstLastNamesIn.clear()

        if(flushBuffers and len(self.__firstLastNamesGeoIn) != 0 or len(self.__firstLastNamesGeoIn) >= BATCH_SIZE):
            if service == SERVICE_NAME_ORIGIN:
                origins = self.processOriginGeo(list(self.__firstLastNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__firstLastNamesGeoIn, origins, softwareNameAndVersion)
            elif service == SERVICE_NAME_GENDER:
                genders = self.processGenderGeo(list(self.__firstLastNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__firstLastNamesGeoIn, genders, softwareNameAndVersion)
            elif service == SERVICE_NAME_DIASPORA:
                diasporas = self.processDiaspora(list(self.__firstLastNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__firstLastNamesGeoIn, diasporas, softwareNameAndVersion)
            elif service == SERVICE_NAME_USRACEETHNICITY:
                usRaceEthnicities = self.processUSRaceEthnicity(list(self.__firstLastNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__firstLastNamesGeoIn, usRaceEthnicities, softwareNameAndVersion)
            elif service == SERVICE_NAME_SUBDIVISION:
                subdivisions = self.processSubdivision(list(self.__firstLastNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__firstLastNamesGeoIn, subdivisions, softwareNameAndVersion)

            self.__firstLastNamesGeoIn.clear()

        if(flushBuffers and len(self.__personalNamesIn) != 0 or len(self.__personalNamesIn) >= BATCH_SIZE):
            if service == SERVICE_NAME_PARSE:
                parseds = self.processParse(list(self.__personalNamesIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesIn, parseds, softwareNameAndVersion)
            elif service == SERVICE_NAME_GENDER:
                genders = self.processGenderFull(list(self.__personalNamesIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesIn, genders, softwareNameAndVersion)
            elif service == SERVICE_NAME_COUNTRY:
                countries = self.processCountry(list(self.__personalNamesIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesIn, countries, softwareNameAndVersion)

            self.__personalNamesIn.clear()

        if(flushBuffers and len(self.__personalNamesGeoIn) != 0 or len(self.__personalNamesGeoIn) >= BATCH_SIZE):
            if service == SERVICE_NAME_PARSE:
                parseds = self.processParseGeo(list(self.__personalNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesGeoIn, parseds, softwareNameAndVersion)
            elif service == SERVICE_NAME_GENDER:
                genders = self.processGenderFullGeo(list(self.__personalNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesGeoIn, genders, softwareNameAndVersion)

            self.__personalNamesGeoIn.clear()

        if(flushBuffers and len(self.__personalNamesGeoSubIn) != 0 or len(self.__personalNamesGeoSubIn) >= BATCH_SIZE):
            if service == SERVICE_NAME_RELIGION:
                religions = self.processReligion(list(self.__personalNamesGeoSubIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesGeoSubIn, religions, softwareNameAndVersion)
            elif service == SERVICE_NAME_CASTEGROUP:
                castegroups = self.processCastegroup(list(self.__personalNamesGeoSubIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesGeoSubIn, castegroups, softwareNameAndVersion)
            self.__personalNamesGeoSubIn.clear()


    def appendReligionStat(self, writer, religion_stats, religion_stats_alt):

        if religion_stats != None and len(religion_stats)>0:
            writer.write(str(religion_stats[0].religion) + self.__separatorOut + str(religion_stats[0].pct) + self.__separatorOut)
        else: 
            writer.append("" + self.__separatorOut + "" + self.__separatorOut)
        if religion_stats_alt != None and len(religion_stats_alt)>0:
            writer.write(str(religion_stats_alt[0].religion) + self.__separatorOut + str(religion_stats_alt[0].pct) + self.__separatorOut)
        else: 
            writer.append("" + self.__separatorOut + "" + self.__separatorOut)
    
            

    def append(self, writer, outputHeaders, inp, output, softwareNameAndVersion):
        global rowId

        flushedUID = set()
        for idObj in inp.keys():
            uid = str(idObj)
            flushedUID.add(uid)
            inputObj = inp.get(uid)
            outputObj = output.get(uid)
            writer.write(uid+self.__separatorOut)

            if isinstance(inputObj, FirstLastNameIn):
                writer.write(self.digest(inputObj["firstName"]) + self.__separatorOut + self.digest(inputObj["lastName"]) + self.__separatorOut)
            elif isinstance(inputObj, FirstLastNameGeoIn):
                writer.write(self.digest(inputObj["firstName"]) + self.__separatorOut + self.digest(inputObj["lastName"]) + self.__separatorOut + inputObj["countryIso2"] + self.__separatorOut)
            elif isinstance(inputObj, PersonalNameIn):
                writer.write(self.digest(inputObj["name"]) + self.__separatorOut)
            elif isinstance(inputObj, PersonalNameGeoIn):
                writer.write(self.digest(inputObj["name"]) + self.__separatorOut + inputObj["countryIso2"] + self.__separatorOut)
            elif isinstance(inputObj, PersonalNameGeoSubdivisionIn):
                writer.write(self.digest(inputObj["name"]) + self.__separatorOut + inputObj["countryIso2"] + self.__separatorOut + inputObj["subdivisionIso"] + self.__separatorOut)
            else:
                raise ValueError("Serialization of " + inputObj.__class__.__name__ + " not supported")

            if outputObj is None:
                for outputHeader in outputHeaders:
                    writer.write("" + self.__separatorOut)
            elif isinstance(outputObj, FirstLastNameGenderedOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["likelyGender"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["genderScale"]) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, FirstLastNameOriginedOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["regionOrigin"]) + self.__separatorOut + str(outputObj["topRegionOrigin"]) + self.__separatorOut + str(outputObj["subRegionOrigin"]) + self.__separatorOut + str(outputObj["countryOrigin"]) + self.__separatorOut + str(outputObj["countryOriginAlt"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"]) + self.__separatorOut + str(outputObj["probabilityAltCalibrated"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["countriesOriginTop"]) + self.__separatorOut + scriptName + self.__separatorOut)
                if self.__religionoption :
                    # create a function to append religion stats to the output
                    self.appendReligionStat(writer, outputObj["religionStats"], outputObj["religionStatsAlt"])
            elif isinstance(outputObj, FirstLastNameGeoSubclassificationOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["subClassification"]) + self.__separatorOut + str(outputObj["subClassificationAlt"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"]) + self.__separatorOut + str(outputObj["probabilityAltCalibrated"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["subclassificationTop"]) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, PersonalNameReligionedOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["religion"]) + self.__separatorOut + str(outputObj["religionAlt"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"]) + self.__separatorOut + str(outputObj["probabilityAltCalibrated"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["religionsTop"]) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, PersonalNameCastegroupOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["castegroup"]) + self.__separatorOut + str(outputObj["castegroupAlt"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"]) + self.__separatorOut + str(outputObj["probabilityAltCalibrated"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["castegroupTop"]) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, PersonalNameGeoOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["region"]) + self.__separatorOut + str(outputObj["topRegion"]) + self.__separatorOut + str(outputObj["subRegion"]) + self.__separatorOut + str(outputObj["country"]) + self.__separatorOut + str(outputObj["countryAlt"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"]) + self.__separatorOut + str(outputObj["probabilityAltCalibrated"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["countriesTop"]) + self.__separatorOut + scriptName + self.__separatorOut)
                if self.__religionoption :
                    # create a function to append religion stats to the output
                    self.appendReligionStat(writer, outputObj["religionStats"], outputObj["religionStatsAlt"])
            elif isinstance(outputObj, FirstLastNameDiasporaedOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["ethnicity"]) + self.__separatorOut + str(outputObj["ethnicityAlt"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"]) + self.__separatorOut + str(outputObj["probabilityAltCalibrated"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["ethnicitiesTop"])+ self.__separatorOut + scriptName + self.__separatorOut)
                if self.__religionoption :
                    # create a function to append religion stats to the output
                    self.appendReligionStat(writer, outputObj["religionStats"], outputObj["religionStatsAlt"])
            elif isinstance(outputObj, FirstLastNameUSRaceEthnicityOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["raceEthnicity"]) + self.__separatorOut + str(outputObj["raceEthnicityAlt"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"])  + self.__separatorOut + str(outputObj["probabilityAltCalibrated"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["raceEthnicitiesTop"]) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, PersonalNameGenderedOut):
                scriptName = outputObj["script"]
                writer.write(str(outputObj["likelyGender"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + str(outputObj["probabilityCalibrated"]) + self.__separatorOut + str(outputObj["genderScale"]) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, PersonalNameParsedOut):
                firstNameParsed = outputObj["firstLastName"]["firstName"] if outputObj["firstLastName"] else ""
                lastNameParsed = outputObj["firstLastName"]["lastName"] if outputObj["firstLastName"] else ""
                scriptName = outputObj["script"]
                writer.write(firstNameParsed + self.__separatorOut + lastNameParsed + self.__separatorOut + str(outputObj["nameParserType"]) + self.__separatorOut + str(outputObj["nameParserTypeAlt"]) + self.__separatorOut + str(outputObj["score"]) + self.__separatorOut + scriptName + self.__separatorOut)
            else:
                raise ValueError("Serialization of " + outputObj.__class__.__name__ + " not supported")

            writer.write(softwareNameAndVersion + self.__separatorOut)
            writer.write(str(rowId) + "\n")
            rowId+=1

        writer.flush()
        if self.isRecover():
            for k in flushedUID:
                self.__done.add(k)

        if rowId % 100 == 0 and rowId < 1000 or rowId % 1000 == 0 and rowId < 10000 or rowId % 10000 == 0 and rowId < 100000 or rowId % 100000 == 0:
            logging.info("Processed " + str(rowId) + " rows.")
            print("Processed " + str(rowId) + " rows.")




    def isWithUID(self):
        return self.__withUID

    def isRecover(self):
        return self.__recover

    def getDigest(self):
        return self.__digest



def main():
    

    try:
        parser = argparse.ArgumentParser(description="Main parser for namsor_commandline_tool")
        # check if arguments are empty
        if len(sys.argv) == 1:
            parser.print_help(sys.stdout)
            sys.exit(0)
        
        #setting up the main parser
        parser.add_argument('-apiKey','--apiKey', required=True, help="NamSor API Key", dest="apiKey")
        parser.add_argument('-i',"--inputFile", required=True , help="input file name", dest="inputFile")
        parser.add_argument('-countryIso2',"--countryIso2", required = False, help="countryIso2 default", dest="countryIso2")
        parser.add_argument('-o',"--outputFile", required = False, help="output file name", dest="outputFile")
        parser.add_argument('-w',"--overwrite", required = False, help="overwrite existing output file", dest="overwrite", action="store_true")
        parser.add_argument('-r',"--recover", required = False, help="continue from a job (requires uid)", dest="recover", action = "store_true")
        parser.add_argument('-f',"--inputDataFormat", required = True, help="input data format : first name, last name (fnln) / first name, last name, geo country iso2 (fnlngeo) / / first name, last name, geo country iso2, subdivision (fnlngeosub) / full name (name) / full name, geo country iso2 (namegeo) / full name, geo country iso2, subdivision (namegeosub) ", dest="inputDataFormat")
        parser.add_argument("-header","--header", required = False, help="output header", dest="header" ,action = "store_true")
        parser.add_argument("-uid","--uid", required = False, help="input data has an ID prefix", dest="uid",action = "store_true")
        parser.add_argument("-digest","--digest", required = False, help="SHA-256 digest names in output", dest="digest", action = "store_true")
        parser.add_argument("-service","--endpoint", required = True, help="service : parse / gender / origin / country / diaspora / usraceethnicity / religion / castegroup", dest="service")
        parser.add_argument("-e","--encoding", required = False, help="encoding : UTF-8 by default", dest="encoding")
        parser.add_argument("-usraceethnicityoption","--usraceethnicityoption", required = False, help=" extra usraceethnicity option USRACEETHNICITY-4CLASSES USRACEETHNICITY-4CLASSES-CLASSIC USRACEETHNICITY-6CLASSES", dest="usraceethnicityoption")
        parser.add_argument("-religionoption","--religionoption", required = False, help=" extra religion stats option "+NAMSOR_OPTION_RELIGION_STATS +" for country / origin / diaspora", action = "store_true")

        args = parser.parse_args()

        tools = NamsorTools(vars(args))

        if(tools.getDigest()!=None):
            logging.getLogger(NamsorTools.__class__.__name__).info("In output, all names will be digested ex. John Smith -> " + tools.digest("John Smith"))

        tools.run()

    except ArgumentError as ex:
        logging.getLogger(NamsorTools.__class__.__name__).log(logging.CRITICAL, None, ex)
        sys.exit(1)

    except NamSorToolException as ex:
        logging.getLogger(NamsorTools.__class__.__name__).log(logging.CRITICAL, None, ex)
        sys.exit(1)

if __name__ == "__main__":
    main()
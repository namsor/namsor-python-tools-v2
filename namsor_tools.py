import sys

import getopt
import argparse

import hashlib
import argparse
import os.path
from synchronized_set import SynchronizedSet
from argparse import ArgumentError

import logging
from namsor_exception import NamSorToolException
import unicodedata2

#API imports
import openapi_client
from openapi_client import AdminApi
from openapi_client import PersonalApi
from openapi_client import ApiClient
from openapi_client.rest import ApiException

#import models
from openapi_client.models import BatchFirstLastNameDiasporaedOut
from openapi_client.models import BatchFirstLastNameGenderedOut
from openapi_client.models import BatchFirstLastNameGeoIn
from openapi_client.models import BatchFirstLastNameIn
from openapi_client.models import BatchFirstLastNameOriginedOut
from openapi_client.models import BatchFirstLastNameUSRaceEthnicityOut
from openapi_client.models import BatchPersonalNameGenderedOut
from openapi_client.models import BatchPersonalNameGeoIn
from openapi_client.models import BatchPersonalNameIn
from openapi_client.models import BatchPersonalNameParsedOut
from openapi_client.models import FirstLastNameDiasporaedOut
from openapi_client.models import FirstLastNameGenderedOut
from openapi_client.models import FirstLastNameGeoIn
from openapi_client.models import FirstLastNameIn
from openapi_client.models import FirstLastNameOriginedOut
from openapi_client.models import FirstLastNameUSRaceEthnicityOut
from openapi_client.models import PersonalNameGenderedOut
from openapi_client.models import PersonalNameGeoIn
from openapi_client.models import PersonalNameIn
from openapi_client.models import PersonalNameParsedOut


DEFAULT_DIGEST_ALGO = "MD5"

BATCH_SIZE = 100

INPUT_DATA_FORMAT_FNLN  = "fnln"
INPUT_DATA_FORMAT_FNLNGEO = "fnlngeo"
INPUT_DATA_FORMAT_FULLNAME = "name"
INPUT_DATA_FORMAT_FULLNAMEGEO = "namegeo"

INPUT_DATA_FORMAT = [
    INPUT_DATA_FORMAT_FNLN,
    INPUT_DATA_FORMAT_FNLNGEO,
    INPUT_DATA_FORMAT_FULLNAME,
    INPUT_DATA_FORMAT_FULLNAMEGEO
]

INPUT_DATA_FORMAT_HEADER = [
    ["firstName", "lastName"],
    ["firstName", "lastName", "countryIso2"],
    ["fullName"],
    ["fullName", "countryIso2"]
]

SERVICE_NAME_PARSE = "parse"
SERVICE_NAME_GENDER = "gender"
SERVICE_NAME_ORIGIN = "origin"
SERVICE_NAME_DIASPORA = "diaspora"
SERVICE_NAME_USRACEETHNICITY = "usraceethnicity"

SERVICES = [
    SERVICE_NAME_PARSE,
    SERVICE_NAME_GENDER,
    SERVICE_NAME_ORIGIN,
    SERVICE_NAME_DIASPORA,
    SERVICE_NAME_USRACEETHNICITY
]

OUTPUT_DATA_PARSE_HEADER = ["firstNameParsed", "lastNameParsed", "nameParserType", "nameParserTypeAlt", "nameParserTypeScore", "script"]
OUTPUT_DATA_GENDER_HEADER = ["likelyGender", "likelyGenderScore", "probabilityCalibrated", "genderScale", "script"]
OUTPUT_DATA_ORIGIN_HEADER  = ["countryOrigin", "countryOriginAlt", "countryOriginScore", "script"]
OUTPUT_DATA_DIASPORA_HEADER = ["ethnicity", "ethnicityAlt", "ethnicityScore", "script"]
OUTPUT_DATA_USRACEETHNICITY_HEADER = ["raceEthnicity", "raceEthnicityAlt", "raceEthnicityScore", "script"]
OUTPUT_DATA_HEADERS = [
    OUTPUT_DATA_PARSE_HEADER,
    OUTPUT_DATA_GENDER_HEADER,
    OUTPUT_DATA_ORIGIN_HEADER,
    OUTPUT_DATA_DIASPORA_HEADER,
    OUTPUT_DATA_USRACEETHNICITY_HEADER
]

uidGen = 0
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

        self.__firstLastNamesGeoIn = {}
        self.__firstLastNamesIn = {}
        self.__personalNamesIn = {}
        self.__personalNamesGeoIn = {}

        self.__commandLineOptions = commandLineOptions

        configuration = openapi_client.Configuration()
        configuration.api_key['X-API-KEY'] = commandLineOptions["apiKey"]  
        configuration.__TIMEOUT = self.__TIMEOUT       
        self.__client = ApiClient(configuration)

        self.__api = PersonalApi(self.__client)
        self.__adminApi = AdminApi(self.__client)
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
        global uidGen
        
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
                    raise NamSorToolException("Line " + lineId + ", expected input with format : " + dataFormatExpected + " line = " + line)

                uid = ""

                col = 0
                
                if (self.isWithUID()):
                    uid = lineData[col]
                    col+=1
                else:
                    uid = "uid" + str(uidGen)
                    uidGen+=1
                
                if (self.isRecover() and uid in self.__done):
                    pass
                else:
                    if (inputDataFormat == INPUT_DATA_FORMAT_FNLN):
                        firstName = lineData[col]
                        col+=1
                        lastName = lineData[col]
                        col+=1
                        firstLastNameIn = FirstLastNameIn()
                        firstLastNameIn.id = uid
                        firstLastNameIn.first_name = firstName
                        firstLastNameIn.last_name = lastName.replace("\n","")
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
                        firstLastNameGeoIn = FirstLastNameGeoIn()
                        firstLastNameGeoIn.id = uid
                        firstLastNameGeoIn.first_name = firstName
                        firstLastNameGeoIn.last_name = lastName.replace("\n","")
                        firstLastNameGeoIn.country_iso2 = countryIso2.replace("\n","")
                        self.__firstLastNamesGeoIn[uid] = firstLastNameGeoIn
                    elif inputDataFormat == INPUT_DATA_FORMAT_FULLNAME :
                        fullName = lineData[col]
                        col+=1
                        personalNameIn = PersonalNameIn()
                        personalNameIn.id = uid
                        personalNameIn.name = fullName.replace("\n","")
                        self.__personalNamesIn[uid] = personalNameIn
                    elif (inputDataFormat == INPUT_DATA_FORMAT_FULLNAMEGEO):
                        fullName = lineData[col]
                        col+=1
                        countryIso2 = lineData[col]
                        col+=1
                        if ((countryIso2 == None) or not countryIso2.strip()) and countryIso2Default != None:
                            countryIso2 = countryIso2Default
                        personalNameGeoIn = PersonalNameGeoIn()
                        personalNameGeoIn.id = uid
                        personalNameGeoIn.name = fullName.replace("\n","")
                        personalNameGeoIn.country_iso2 = countryIso2.replace("\n","")
                        self.__personalNamesGeoIn[uid] = personalNameGeoIn
                    

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
            softwareNameAndVersion = self.__adminApi.software_version().software_name_and_version
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
                outputFileName = inputFileName + "." + service + (".digest" if self.__digest!=None else "") + ".namsor"
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
                    if line%100000 == 0:
                        logging.getLogger(NamsorTools.__class__.__name__).info("Loading from existing " + outputFileName + ":" + str(line))
                    line+=1
                readerDone.close()
            
            reader = open(inputFileName,'r',encoding = encoding)
            mode = 'a' if self.isRecover() else 'w'
            
            writer = open(outputFileName,mode,encoding=encoding)
            
            self.process(service,reader,writer,softwareNameAndVersion)

        except Exception as ex:
            logging.getLogger(NamsorTools.__class__.__name__).log(logging.CRITICAL, ex)
            

    def appendHeader(self, writer, inputHeaders, outputHeaders):
        writer.write('#uid' + self.__separatorOut)

        for inputHeader in inputHeaders:
            writer.write(inputHeader + self.__separatorOut)
        
        for outputHeader in outputHeaders:
            writer.write(outputHeader + self.__separatorOut)
        
        writer.write('version' + self.__separatorOut)
        writer.write('rowId'+"\n")


    #names -> list[FirstLastNameGeoIn]
    def processDiaspora(self, names):
        result = {}
        body = BatchFirstLastNameGeoIn()
        body.personal_names = names
        origined:BatchFirstLastNameDiasporaedOut = self.__api.diaspora_batch(batch_first_last_name_geo_in=body)

        for personalName in origined.personal_names:
            result[personalName.id] = personalName
        
        return result
    
    #names -> list[FirstLastNameGeoIn]
    def processOriginGeo(self, names):
        namesNoGeo = []
        for name in names:
            nameNoGeo = FirstLastNameIn()
            nameNoGeo.id = name.id
            nameNoGeo.first_name = name.first_name
            nameNoGeo.last_name = name.last_name

            namesNoGeo.append(nameNoGeo)
        
        return self.processOrigin(namesNoGeo)
    
    #names -> list[FirstLastNameIn]
    def processOrigin(self, names):
        result = {}
        body = BatchFirstLastNameIn()
        body.personal_names = names
        origined = self.__api.origin_batch(batch_first_last_name_in=body)

        for personalName in origined.personal_names:
            result[personalName.id] = personalName
        
        return result
    
    #names -> list[FirstLastNameIn]
    def processGender(self, names):
        result = {}
        body = BatchFirstLastNameIn()
        body.personal_names = names
        gendered = self.__api.gender_batch(batch_first_last_name_in=body)

        for personalName in gendered.personal_names:
            result[personalName.id] = personalName
        
        return result
    
    #names -> list[PersonalNameIn]
    def processGenderFull(self, names):
        result = {}
        body = BatchPersonalNameIn()
        body.personal_names = names
        gendered = self.__api.gender_full_batch(batch_personal_name_in=body)

        for personalName in gendered.personal_names:
            result[personalName.id] = personalName
        
        return result
    
    #names -> list[PersonalNameGeoIn]
    def processGenderFullGeo(self, names):
        result = {}
        body = BatchPersonalNameGeoIn()
        body.personal_names = names
        gendered = self.__api.gender_full_geo_batch(batch_personal_name_geo_in=body)

        for personalName in gendered.personal_names:
            result[personalName.id] = personalName
        
        return result

    #names -> list[PersonalNameIn]
    def processParse(self, names):
        result = {}
        body = BatchPersonalNameIn()
        body.personal_names = names
        parsed = self.__api.parse_name_batch(batch_personal_name_in=body)

        for personalName in parsed.personal_names:
            result[personalName.id] = personalName
        
        return result

    #names -> list[FirstLastNameGeoIn]
    def processGenderGeo(self, names):
        result = {}
        body = BatchFirstLastNameGeoIn()
        body.personal_names = names
        gendered = self.__api.gender_geo_batch(batch_first_last_name_geo_in=body)

        for personalName in gendered.personal_names:
            result[personalName.id] = personalName
        
        return result
    
    #names -> list[PersonalNameGeoIn]
    def processParseGeo(self, names):
        result = {}
        body = BatchPersonalNameGeoIn()
        body.personal_names = names
        parsed = self.__api.parse_name_geo_batch(batch_personal_name_geo_in=body)

        for personalName in parsed.personal_names:
            result[personalName.id] = personalName
        
        return result

    #names -> list[FirstLastNameGeoIn]
    def processUSRaceEthnicity(self, names):
        result = {}
        body = BatchFirstLastNameGeoIn()
        body.personal_names = names
        racedEthnicized = self.__api.us_race_ethnicity_batch(batch_first_last_name_geo_in=body)

        for personalName in racedEthnicized.personal_names:
            result[personalName.id] = personalName
        
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
        
            self.__firstLastNamesGeoIn.clear()

        if(flushBuffers and len(self.__personalNamesIn) != 0 or len(self.__personalNamesIn) >= BATCH_SIZE):
            if service == SERVICE_NAME_PARSE:
                parseds = self.processParse(list(self.__personalNamesIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesIn, parseds, softwareNameAndVersion)
            elif service == SERVICE_NAME_GENDER:
                genders = self.processGenderFull(list(self.__personalNamesIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesIn, genders, softwareNameAndVersion)
            
            self.__personalNamesIn.clear()

        if(flushBuffers and len(self.__personalNamesGeoIn) != 0 or len(self.__personalNamesGeoIn) >= BATCH_SIZE):
            if service == SERVICE_NAME_PARSE:
                parseds = self.processParseGeo(list(self.__personalNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesGeoIn, parseds, softwareNameAndVersion)
            elif service == SERVICE_NAME_GENDER:
                genders = self.processGenderFullGeo(list(self.__personalNamesGeoIn.values()))
                self.append(writer, outputHeaders, self.__personalNamesGeoIn, genders, softwareNameAndVersion)
            
            self.__personalNamesGeoIn.clear()
        


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
                writer.write(self.digest(inputObj.first_name) + self.__separatorOut + self.digest(inputObj.last_name) + self.__separatorOut)
            elif isinstance(inputObj, FirstLastNameGeoIn):
                writer.write(self.digest(inputObj.first_name) + self.__separatorOut + self.digest(inputObj.last_name) + self.__separatorOut + inputObj.country_iso2 + self.__separatorOut)
            elif isinstance(inputObj, PersonalNameIn):
                writer.write(self.digest(inputObj.name) + self.__separatorOut)
            elif isinstance(inputObj, PersonalNameGeoIn):
                writer.write(self.digest(inputObj.name) + self.__separatorOut + inputObj.country_iso2 + self.__separatorOut)
            else: 
                raise ValueError("Serialization of " + inputObj.__class__.__name__ + " not supported")

            if outputObj is None: 
                for outputHeader in outputHeaders:
                    writer.write("" + self.__separatorOut)
            elif isinstance(outputObj, FirstLastNameGenderedOut):
                scriptName = computeScriptFirst(outputObj.last_name)
                writer.write(str(outputObj.likely_gender) + self.__separatorOut + str(outputObj.score) + self.__separatorOut + str(outputObj.probability_calibrated) + self.__separatorOut + str(outputObj.gender_scale) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, FirstLastNameOriginedOut):
                scriptName = computeScriptFirst(outputObj.last_name)
                writer.write(str(outputObj.country_origin) + self.__separatorOut + str(outputObj.country_origin_alt) + self.__separatorOut + str(outputObj.score) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, FirstLastNameDiasporaedOut):
                scriptName = computeScriptFirst(outputObj.last_name)
                writer.write(str(outputObj.ethnicity) + self.__separatorOut + str(outputObj.ethnicity_alt) + self.__separatorOut + str(outputObj.score) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, FirstLastNameUSRaceEthnicityOut):
                scriptName = computeScriptFirst(outputObj.last_name)
                writer.write(str(outputObj.race_ethnicity) + self.__separatorOut + str(outputObj.race_ethnicity_alt) + self.__separatorOut + str(outputObj.score) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, PersonalNameGenderedOut):
                scriptName = computeScriptFirst(outputObj.name)
                writer.write(str(outputObj.likely_gender) + self.__separatorOut + str(outputObj.score) + self.__separatorOut + str(outputObj.gender_scale) + self.__separatorOut + scriptName + self.__separatorOut)
            elif isinstance(outputObj, PersonalNameParsedOut):
                firstNameParsed = outputObj.first_last_name.first_name if outputObj.first_last_name else ""
                lastNameParsed = outputObj.first_last_name.last_name if outputObj.first_last_name else ""
                scriptName = computeScriptFirst(outputObj.name)
                writer.write(firstNameParsed + self.__separatorOut + lastNameParsed + self.__separatorOut + str(outputObj.name_parser_type) + self.__separatorOut + str(outputObj.name_parser_type_alt) + self.__separatorOut + str(outputObj.score) + self.__separatorOut + scriptName + self.__separatorOut)
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



    def isWithUID(self):
        return self.__withUID
    
    def isRecover(self):
        return self.__recover
    
    def getDigest(self):
        return self.__digest



def computeScriptFirst(someString):
    for i in range(len(someString)):
        c = someString[i]
        script = unicodedata2.script_cat(c)[0]
        if script == "Common":
            continue

        return script
    
    return None


def main():
    try:
        parser = argparse.ArgumentParser(description="Main parcer for namsor_commandline_tool")
        help_parser = argparse.ArgumentParser(description="Help option parcer for namsor_commandline_tool", add_help=False, formatter_class=argparse.HelpFormatter)
        
        #setting up the main parser
        parser.add_argument('-apiKey','--apiKey', required=True, help="NamSor API Key", dest="apiKey")
        parser.add_argument('-i',"--inputFile", required=True , help="input file name", dest="inputFile")
        parser.add_argument('-countryIso2',"--countryIso2", required = False, help="countryIso2 default", dest="countryIso2")
        parser.add_argument('-o',"--outputFile", required = False, help="output file name", dest="outputFile")
        parser.add_argument('-w',"--overwrite", required = False, help="overwrite existing output file", dest="overwrite", action="store_true")
        parser.add_argument('-r',"--recover", required = False, help="continue from a job (requires uid)", dest="recover",action = "store_true")
        parser.add_argument('-f',"--inputDataFormat", required = True, help="input data format : first name, last name (fnln) / first name, last name, geo country iso2 (fnlngeo) / full name (name) / full name, geo country iso2 (namegeo) ", dest="inputDataFormat")
        parser.add_argument("-header","--header", required = False, help="output header", dest="header" ,action = "store_true")
        parser.add_argument("-uid","--uid", required = False, help="input data has an ID prefix", dest="uid",action = "store_true")
        parser.add_argument("-digest","--digest", required = False, help="SHA-256 digest names in output", dest="digest",action = "store_true")
        parser.add_argument("-service","--endpoint", required = True, help="service : parse / gender / origin / diaspora / usraceethnicity", dest="service")
        parser.add_argument("-e","--encoding", required = False, help="encoding : UTF-8 by default", dest="encoding")

        
        args = parser.parse_args()
        
        tools = NamsorTools(vars(args))

        if(tools.getDigest()!=None):
            logging.getLogger(NamsorTools.__class__.__name__).info("In output, all names will be digested ex. John Smith -> " + tools.digest("John Smith"))
          
        tools.run()

    except ArgumentError as ex:
        logging.getLogger(NamsorTools.__class__.__name__).log(logging.CRITICAL, None, ex)
    
    except NamSorToolException as ex:
        logging.getLogger(NamsorTools.__class__.__name__).log(logging.CRITICAL, None, ex)

if __name__ == "__main__":
    main()
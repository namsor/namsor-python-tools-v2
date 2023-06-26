# namsor-python-tools
NamSor Python command line tools, to append gender, origin, diaspora or us 'race'/ethnicity to a CSV file. The CSV file should in UTF-8 encoding, pipe-| demimited. It can be very large. Check out also the Java CLT (https://github.com/namsor/namsor-tools-v2)


Please install https://github.com/namsor/namsor-python-sdk2 and synchronized-set dependencies, 

```bash
pip install git+https://github.com/namsor/namsor-python-sdk2.git
pip install synchronized-set
```
NB: we use Unix conventions for file paths, ex. samples/some_fnln.txt but on MS Windows that would be samples\some_fnln.txt

Then clone this project and start from the base directory. 
```bash
git clone https://github.com/namsor/namsor-python-tools-v2/
cd namsor-python-tools-v2
```

## Running

```bash
python namsor_tools.py
python3 namsor_tools.py  	[-h] -apiKey APIKEY -i INPUTFILE [-countryIso2 COUNTRYISO2] [-o OUTPUTFILE] [-w] 
							[-r] -f INPUTDATAFORMAT [-header] [-uid] [-digest] -service SERVICE [-e ENCODING]
							[-usraceethnicityoption USRACEETHNICITYOPTION]                   
```

## Detailed usage		  

```	
python3
usage: namsor_tools.py 	[-h] -apiKey APIKEY -i INPUTFILE [-countryIso2 COUNTRYISO2] [-o OUTPUTFILE] [-w] 
						[-r] -f INPUTDATAFORMAT [-header] [-uid] [-digest] -service SERVICE [-e ENCODING]
						[-usraceethnicityoption USRACEETHNICITYOPTION]

Main parser for namsor_commandline_tool

options:
  -h, --help            show this help message and exit
  -apiKey APIKEY, --apiKey APIKEY
                        NamSor API Key
  -i INPUTFILE, --inputFile INPUTFILE
                        input file name
  -countryIso2 COUNTRYISO2, --countryIso2 COUNTRYISO2
                        countryIso2 default
  -o OUTPUTFILE, --outputFile OUTPUTFILE
                        output file name
  -w, --overwrite       overwrite existing output file
  -r, --recover         continue from a job (requires uid)
  -f INPUTDATAFORMAT, --inputDataFormat INPUTDATAFORMAT
                        input data format : first name, last name (fnln) / first name, last name, geo country iso2
                        (fnlngeo) / / first name, last name, geo country iso2, subdivision (fnlngeosub) / full name
                        (name) / full name, geo country iso2 (namegeo) / full name, geo country iso2, subdivision
                        (namegeosub)
  -header, --header     output header
  -uid, --uid           input data has an ID prefix
  -digest, --digest     SHA-256 digest names in output
  -service SERVICE, --endpoint SERVICE
                        service : parse / gender / origin / country / diaspora / usraceethnicity / religion /
                        castegroup
  -e ENCODING, --encoding ENCODING
                        encoding : UTF-8 by default
  -usraceethnicityoption USRACEETHNICITYOPTION, --usraceethnicityoption USRACEETHNICITYOPTION
                        extra usraceethnicity option USRACEETHNICITY-4CLASSES USRACEETHNICITY-4CLASSES-CLASSIC
                        USRACEETHNICITY-6CLASSES
```

## Examples

To append the likely name gender to a list of first and last names : John|Smith

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -f fnln -i samples/some_fnln.txt -service gender
```

To append the likely name origin to a list of first and last names : John|Smith

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -f fnln -i samples/some_fnln.txt -service origin
```

To append the likely country of residence to a list of full names : John Smith

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -f name -i samples/some_name.txt -service country
```


To parse names into first and last name components (John Smith or Smith, John -> John|Smith)

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -f name -i samples/some_name.txt -service parse
```

The recommended input format is to specify a unique ID and a geographic context (if known) as a countryIso2 code. 

To append gender to a list of id, first and last names, geographic context : id12|John|Smith|US

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -uid -f fnlngeo -i samples/some_idfnlngeo.txt -service gender
```

To append the ethnicity (in the sense of cultural heritage / country of origin of ascendents) from a list of id, first and last names, geographic context : id12|John|Smith|US

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -uid -f fnlngeo -i samples/some_idfnlngeo.txt -service diaspora
```

To append US'race'/ethnicity to a list of id, first and last names, geographic context : id12|John|Smith|US

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -uid -f fnlngeo -i samples/some_idfnlnUS.txt -service usraceethnicity
```
To append US'race'/ethnicity to a list of id, first and last names, geographic context : id12|John|Smith|US with option USRACEETHNICITY-6CLASSES

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -uid -f fnlngeo -i samples/some_idfnlnUS.txt -service usraceethnicity --usraceethnicityoption USRACEETHNICITY-6CLASSES
```

To parse name into first and last name components, a geographic context is recommended (esp. for Latam names) : id12|John Smith|US

```bash
python namsor_tools.py -apiKey <yourAPIKey> -w -header -uid -f namegeo -i samples/some_idnamegeo.txt -service parse
```
On large input files with a unique ID, it is possible to recover from where the process crashed and append to the existint output file, for example :

```bash
python namsor_tools.py -apiKey <yourAPIKey> -r -header -uid -f fnlngeo -i samples/some_idfnlngeo.txt -service gender
```

For Indian names (for now), you can infer the likely india state or union territory (ie. a subdivision of the country as per ISO 3166-2:IN)

```bash
python namsor_tools.py -apiKey <yourAPIKey>  -r -header -uid -f fnlngeo -i samples/some_indian_idfnlngeo.txt -service subdivision
```

For Indian names (for now), you can infer the likely religion (provided the IN country code and state/union territory as per ISO 3166-2:IN)

```bash
python namsor_tools.py -apiKey <yourAPIKey>  -r -header -uid -f namegeosub -i samples/some_indian_idnamegeosub.txt -service subdivision
```

For Indian names (for now), you can infer the likely caste group (provided the IN country code and state/union territory as per ISO 3166-2:IN)

```bash
python namsor_tools.py -apiKey <yourAPIKey>  -r -header -uid -f namegeosub -i samples/some_indian_idnamegeosub.txt -service castegroup
```


## Anonymizing output data
The -digest option will digest personal names in file outpus, using a non reversible MD-5 hash. For example, John Smith will become 6117323d2cabbc17d44c2b44587f682c.
Please note that this doesn't apply to the PARSE output. 

## Understanding output
Please read and contribute to the WIKI
https://github.com/namsor/namsor-tools-v2/wiki/NamSor-Tools-V2

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

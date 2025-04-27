# Written by Aep (https://github.com/Aeplexi) on March 30th, 2025.
# Downloads the latest files from NUS from http://nus.shop.wii.com/nus/services/NetUpdateSOAP

import sys
import libWiiPy
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

# Request setup
NUS_BASE_URL = "http://nus.shop.wii.com"
NUS_NET_UPDATE_SOAP_PATH = "/nus/services/NetUpdateSOAP"
headers = {"Content-Type": "application/xml", "SOAPAction": "urn:nus.wsapi.broadon.com/GetSystemUpdate", "User-Agent": "wii libnup/1.0"}

# Installing boot2 WADs can be very dangerous in some cases so to be safe, they are only downloaded if the user confirms they would like to download it
BOOT2_TITLE_ID = "0000000100000001"
SKIP_BOOT2 = True # Enabled by default

# Values for the SOAP Request
REGION = ""
DEVICE_ID = "5555555555" # For some reason there seems to be some sort of algorithm with this, but 5555555555 works always so we use it here

# The actual SOAP request
SOAP_REQUEST = ""

def parse_region(region: str):
    # We want to tell the user that only "USA", "EUR", "JPN", "TWN", and "KOR" are supported
    global REGION
    if region == "USA" or region == "EUR" or region == "JPN" or region == "KOR" or region == "TWN": # Probably a better way to handle this line but whatever tbh
        REGION = region
    else:
        print("You have entered an invalid region. Valid regions are: USA, EUR, JPN, KOR, TWN")
        sys.exit(1)

def generate_soap_request():
    global SOAP_REQUEST # Must be global as we use it elsewhere
    SOAP_REQUEST = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/2001/XMLSchema"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Body>
    <GetSystemUpdateRequest xmlns="urn:nus.wsapi.broadon.com">
      <Version>1.0</Version>
      <MessageId>0</MessageId>
      <DeviceId>{DEVICE_ID}</DeviceId>
      <RegionId>{REGION}</RegionId>
    </GetSystemUpdateRequest>
  </soapenv:Body>
</soapenv:Envelope>"""
    

def download_title(title_id: str, version: str):
    title = libWiiPy.title.Title()
    try:
        title.load_tmd(libWiiPy.title.download_tmd(title_id, version, wiiu_endpoint=False))
    except ValueError:
        print(f"Skipping Title ID {title_id} Version {version}, because the TMD was not found.")
    try:
        title.load_ticket(libWiiPy.title.download_ticket(title_id, wiiu_endpoint=False))
    except ValueError:
        print(f"Skipping Title ID {title_id} Version {version}, because the ticket is not freely available on the NUS servers.")

    # Get the content for this Title. (from https://github.com/NinjaCheetah/NUSGet-Web-Backend)
    title.load_content_records()
    title.content.content_list = libWiiPy.title.download_contents(title_id, title.tmd, wiiu_endpoint=False)
    # Build the retail certificate chain.
    title.load_cert_chain(libWiiPy.title.download_cert_chain(wiiu_endpoint=False))
    # Generate required metadata and return the response.
    #ver_final = version if version else title.tmd.title_version
    
    working_directory = Path.cwd() / f"system-update.py Downloads ({REGION})"
    working_directory.mkdir(exist_ok=True)

    file_path = working_directory / f"{title_id}-v{version}.wad"
    file_path.write_bytes(title.dump_wad())

# ENTRY
if len(sys.argv) < 2:
    print("Usage: system-update.py <REGION>")
    print("You can also add --boot2 in the arguments to download the latest boot2 from NUS as well. However, installing this may be dangerous and this is why it is skipped by default.")
    sys.exit(1)

# Check if they want to continue with downloading boot2, and potentially installing it
if "--boot2" in sys.argv:
    confirmation = input("You have specified to download boot2 along with everything else from the System Update. Modifying boot2 is not recommended and often not necessary for many reasons, however if you are SURE you want to do this, type YES: ").strip().lower()
    SKIP_BOOT2 = confirmation != "yes"

parse_region(sys.argv[1])
generate_soap_request()

response = requests.post(NUS_BASE_URL + NUS_NET_UPDATE_SOAP_PATH, data=SOAP_REQUEST, headers=headers)

# Now parse the response and download all the titles I guess
root = ET.fromstring(response.text)
ns = {'ns': 'urn:nus.wsapi.broadon.com'}

# parse all the title versions
for title in root.findall(".//ns:TitleVersion", ns):
    title_id = title.find("ns:TitleId", ns).text
    if (title_id == BOOT2_TITLE_ID and SKIP_BOOT2):
        continue
    version = title.find("ns:Version", ns).text
    fs_size = title.find("ns:FsSize", ns).text
    print(f"Downloading Title ID: {title_id}, Version: {version}, Size: {fs_size}")
    try:
        download_title(title_id, version)
        print(f"Downloading Title ID: {title_id}, Version: {version}: Success!")
    except:
        print(f"Failed to download Title ID: {title_id}, Version: {version}. Is the endpoint down? Report this on the GitHub issues page.")

print("Successfully downloaded all files!")

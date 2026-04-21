import csv
import os
import sys
import urllib3
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, Settings
from zeep.transports import Transport
from zeep.exceptions import Fault
from dotenv import load_dotenv

# Deshabilitar advertencias de certificados no válidos (común en entornos de laboratorio)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. Cargar configuración desde .env
load_dotenv()

CUCM_ADDRESS = os.getenv("CUCM_ADDRESS")
USERNAME = os.getenv("AXL_USERNAME")
PASSWORD = os.getenv("AXL_PASSWORD")
WSDL_FILE = 'schema/AXLAPI.wsdl'
CSV_FILE = "sip_trunk_lista_csv.csv"

# Validación de variables
if not all([CUCM_ADDRESS, USERNAME, PASSWORD]):
    print("ERROR: Faltan variables en el .env (CUCM_ADDRESS, AXL_USERNAME o AXL_PASSWORD).")
    sys.exit(1)

# 2. Configurar la conexión AXL (Zeep)
session = Session()
session.verify = False
session.auth = HTTPBasicAuth(USERNAME, PASSWORD)
transport = Transport(session=session, timeout=20)
settings = Settings(strict=False, xml_huge_tree=True)

try:
    client = Client(WSDL_FILE, settings=settings, transport=transport)
    service = client.create_service(
        '{http://www.cisco.com/AXLAPIService/}AXLAPIBinding',
        f'https://{CUCM_ADDRESS}:8443/axl/'
    )
except Exception as e:
    print(f"ERROR: No se pudo inicializar el cliente Zeep: {e}")
    sys.exit(1)

# 3. Leer CSV y crear troncales

with open(CSV_FILE, newline='', encoding='utf-8') as csv_file:
    reader = csv.DictReader(csv_file)
    for row in reader:
        trunk_name = row["trunk_name"]
        print(f"\nCreando SIP TRUNK {trunk_name}")

        sip_trunk_data = {
            'name': trunk_name,
            'description': row['description'],
            'product': 'SIP Trunk',
            'class': 'Trunk',
            'protocol': 'SIP',
            'protocolSide': 'Network',
            'devicePoolName': 'Default',
            'locationName': 'Hub_None',
            'securityProfileName': 'Non Secure SIP Trunk Profile',
            'sipProfileName': 'Standard SIP Profile',
            'presenceGroupName': 'Standard Presence group',
            'callingAndCalledPartyInfoFormat': 'Deliver DN only in connected party',

            'destinations': []
        }

        # Destination
        sip_trunk_data['destinations'].append({
            'destination': {
                'addressIpv4': row['dest_ip'],
                'port': '5060',
                'sortOrder': 1
            }
        })

        try:
            service.addSipTrunk(sip_trunk_data)
            print(f"[OK] SIP Trunk '{trunk_name}' creada")
        except Fault as err:
            print(f"[ERROR] No se pudo crear '{trunk_name}'")
            print(err)

print("\nProceso finalizado.")


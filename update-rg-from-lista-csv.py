import csv
import os
import sys
import urllib3
from collections import defaultdict
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
CSV_FILE = "routegroup_devices2.csv"

# Validación de variables
if not all([CUCM_ADDRESS, USERNAME, PASSWORD]):
    print("ERROR: Faltan variables en el .env (CUCM_ADDRESS, AXL_USERNAME o AXL_PASSWORD).")
    sys.exit(1)

# 2. Configurar la conexión AXL (Zeep)
session = Session()
session.verify = False
session.auth = HTTPBasicAuth(USERNAME, PASSWORD)
transport = Transport(session=session, timeout=2)
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

# 3. Leer CSV y agrupar devices por Route Group
route_groups = defaultdict(list)

try:
    with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rg = row.get("route_group")
            device = row.get("device_name")
            if not rg or not device:
                continue

            order = row.get("selection_order", "1")
            # Estructura requerida por AXL para los miembros del Route Group
            route_groups[rg].append({
                'deviceSelectionOrder': order,
                'deviceName': device,
                'port': "0"  # Valor por defecto común en AXL
            })
except FileNotFoundError:
    print(f"ERROR: Archivo {CSV_FILE} no encontrado.")
    sys.exit(1)

# 4. Procesar y actualizar cada Route Group
contador = 0
for rg_name, members in route_groups.items():
    contador = contador + 1
    print(f"\n---{contador}- Procesando Route Group: {rg_name} ---")

    try:
        # Primero verificamos si el Route Group existe
        # Nota: getRouteGroup requiere el nombre
        try:
            service.getRouteGroup(name=rg_name)
        except Fault:
            print(f"[SKIP] El Route Group '{rg_name}' no existe en el CUCM.")
            continue

        # Actualizamos los miembros
        # El metodo updateRouteGroup reemplaza los miembros actuales con la lista enviada
        service.updateRouteGroup(
            name=rg_name,
            members={'member': members}
        )
        print(f"[OK] Miembros actualizados exitosamente en '{rg_name}'.")

    except Fault as e:
        print(f"[ERROR] Error de AXL en '{rg_name}': {e}")
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")

print("\nScript finalizado.")

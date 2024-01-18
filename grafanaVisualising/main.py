import argparse
from threading import Thread, Event
import serial
import time
from lib.realtime import Ratekeeper
from panda.python import Panda
import lib.clients.UDS_client as UDS
from lib.protocols.UDS import UdsClient
from lib.protocols.OBD import OBDClient
from grafanaVisualising.config_params import primary_params, secondary_params, samplingRate, \
    parametersToQuery_0x7D2, parametersToQuery_0x700, parametersToQuery_0x7F0
from DB import MySQL_DB

####  Process arguments
parser = argparse.ArgumentParser(description='')
parser.add_argument('--gps', action='store_true')
parser.add_argument('-d', '--deleteDB', action='store_true')
parser.add_argument('-od', '--overwriteDate', action='store_true')
parser.add_argument('-f', '--frequency', type=int)
args = parser.parse_args()


def processList(incomingParams: dict):
    for p in incomingParams:
        primary_params[p] = incomingParams[p]


def calculate_secondary_params(mileageOnStartup):
    if "co2_emissions" in secondary_params:
        co2_emissions = 0.001518 * primary_params.get("exhausts_co2_concentration") * (
                primary_params.get("engine_exhaust_flow_rate") / 3600)
        secondary_params["co2_emissions"] = co2_emissions

    if "distance_travelled_since_startup" in secondary_params:
        distanceTravelledSinceStartup = primary_params.get("total_distance_travelled") - mileageOnStartup
        secondary_params["distance_travelled_since_startup"] = distanceTravelledSinceStartup

    if "motor_power_delivered" in secondary_params:
        motor_power_delivered = primary_params.get("motor_torque") * primary_params.get(
            "motor_revolution") / 9.548 / 1000
        secondary_params["motor_power_delivered"] = motor_power_delivered


latest_gps_location = {"latitude": None, "longitude": None, "altitude": None}
if args.gps:
    def gpsLocationThread(debug=True):
        try:
            ser = serial.Serial(port='/dev/ttyACM0', baudrate=115200, parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=10)
            if ser.is_open:
                print("GPS -> Serial GPS device connected successfully.")
            while 1:
                line = ser.readline()
                if line != b"" and line != b"\n":
                    line = line.decode()[:-1]
                    try:
                        fix, numSat, latitude, longitude, altitude, HDOP = line[:-2].split(",", 5)
                    except ValueError:
                        continue
                    if fix == "1":
                        latest_gps_location["latitude"] = latitude
                        latest_gps_location["longitude"] = longitude
                        latest_gps_location["altitude"] = altitude
                        if debug:
                            print("fixed: ", fix, ", satellites found: ", numSat, ", latitude: ", latitude,
                                  ", longitude: ", longitude, ", altitude: ", altitude, ", HDOP: ", HDOP)
                    else:
                        if debug:
                            print("fixed: 0, satellites found: ", numSat,
                                  ", latitude: None, longitude: None, altitude: None, HDOP: None")
        except serial.SerialException as e:
            print(e)
            raise
        except IOError as e:
            print(e)
            raise


def dbInsertionThread(insert_db: Event()):
    while True:
        insert_db.wait()
        print(primary_params)
        DB.insertRecords(primary_params, secondary_params, latest_gps_location, str(time.time()))
        insert_db.clear()

#### Initialise Panda
panda = Panda()
panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
bus = 0

#### Clients instantiation (one per ECU)
UDS_client_0x7D2 = UdsClient(panda, 0x7D2, bus, timeout=1, debug=False)
UDS_client_0x700 = UdsClient(panda, 0x700, bus, timeout=1, debug=False)
OBD_client_0x7C0 = OBDClient(panda, 0x7C0, bus, timeout=1, debug=False)
UDS_client_0x7F0 = UdsClient(panda, 0x7F0, bus, timeout=5, debug=False)  # timeout 5s in case CO2 agent reboots

#### Prepare dynamically defined data identifiers for multiple parameters UDS queries
if len(parametersToQuery_0x7D2) > 0:
    UDS.prepareDynamicallyDefinedData(UDS_client_0x7D2, parametersToQuery_0x7D2)
if len(parametersToQuery_0x700) > 0:
    UDS.prepareDynamicallyDefinedData(UDS_client_0x700, parametersToQuery_0x700)

#### Initialise DB connection
DB = MySQL_DB(primary_params, secondary_params, includeGPS=args.gps, deleteOnStartUp=args.deleteDB,
              overwriteDate=args.overwriteDate, verbose=False)


def main(debug: bool = False, frequency: int = samplingRate):
    # DB insertions are done on a separate thread to save up querying time
    insert_db = Event()
    db_thread = Thread(target=dbInsertionThread, args=(insert_db,), daemon=True)
    db_thread.start()

    if args.gps:
        gps_thread = Thread(target=gpsLocationThread, args=(debug,), daemon=True)
        gps_thread.start()
        while latest_gps_location["latitude"] is None or latest_gps_location["longitude"] is None:
            time.sleep(0.5)  # Wait to get first GPS measurement

    # Auxiliary values for calculating derived params:
    # mileageOnStartup = UDS.readDataByIdentifier(UDS_client_0x700,
    #                                            next(filter(lambda x: x.name == "total_distance_travelled",
    #                                                        paramsToQuery)), loop=False, debug=False)

    frequency = args.frequency if args.frequency else frequency
    rk = Ratekeeper(frequency, boot_time=time.time(), print_delay_threshold=0.01)
    while 1:
        for i in range(frequency):

            #### Calculate primary params
            processList(UDS.readDataByIdentifier_dynamicallyAllocated(uds_client=UDS_client_0x7D2, parameter_list=parametersToQuery_0x7D2, loop=False, debug=debug))
            processList(UDS.readDataByIdentifier_dynamicallyAllocated(uds_client=UDS_client_0x700, parameter_list=parametersToQuery_0x700, loop=False, debug=debug))
            primary_params["exhausts_co2_concentration"] = UDS.readDataByIdentifier(uds_client=UDS_client_0x7F0, parameter=parametersToQuery_0x7F0[0], loop=False, debug=debug)

            #### Calculate secondary params
            # calculate_secondary_params(mileageOnStartup)

            #  Trigger DB insertion
            insert_db.set()

            rk.keep_time()


main(debug=False)

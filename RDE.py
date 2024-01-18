import argparse
from threading import Thread
import pyqtgraph as pg
from panda.python import Panda
import serial
from lib.clients import UDS_client as UDS
from lib.clients import OBD_client as OBD
from lib.protocols.UDS import UdsClient
from lib.protocols.OBD import OBDClient
from lib.parameters import parameters as IP
from lib.parameters import importantParameters
from datetime import datetime
import time
from lib.realtime import Ratekeeper

parser = argparse.ArgumentParser(description='')
parser.add_argument('--gps', action='store_true')
parser.add_argument('--plot', action='store_true')
parser.add_argument('--percentage', action='store_true')
args = parser.parse_args()

writeResults = False

panda = Panda()
panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
bus = 0

if args.plot:
    pw = pg.plot(name="CO2 measurement")
    if args.percentage:
        pw.setLabel("left", "CO2 concentration (%)")
    else:
        pw.setLabel("left", "CO2 concentration (PPM)")
    pw.showGrid(y=True, alpha=10000)
    pw.setLabel("bottom", "no. reads")


    def PPMtoPercentage(val):
        return val / 10000


    def update_plot(values):
        pw.plot(values, clear=True, pen="r")
        pg.QtGui.QApplication.processEvents()

co2 = []

# Query parameters definition divided by ECU query address
parametersToQuery_0x700 = [  # Engine
    # IP["atmospheric_pressure"],
    # IP["calculate_load"],
    IP["coolant_temperature"],
    IP["engine_exhaust_flow_rate"],
    IP["mass_air_flow"],
    IP["total_distance_travelled"],
    IP["vehicle_speed"],
]

parametersToQuery_0x7D2 = [  # Hybrid System
    # IP["ac_consumption_power"],
    # IP["drive_mode"],
    IP["deceleration_sensor"],
    IP["engine_mode"],
    IP["engine_speed"],
    IP["ev_mode_status"],
    IP["execute_engine_power"],
    # IP["hybrid_battery_current"],
    IP["hybrid_battery_soc"],
    # IP["hybrid_battery_voltage"],
    IP["lack_of_fuel"],
    IP["motor_revolution"],
    IP["motor_torque"],
    # IP["p_control_request_status"],
    # IP["powertrain_mode_switch"],
    # IP["target_engine_power"],
    # IP["target_engine_revolution"],
]

parametersToQuery_0x7C0 = [  # Combination Meter
    # IP["fuel_input_volume"],
]

parametersToQuery_0x7F0 = [  # CO2 agent
    IP["exhausts_co2_concentration"],
]

# Clients instantiation
UDS_client_0x700 = UdsClient(panda, 0x700, bus, timeout=1, debug=False)
UDS_client_0x7D2 = UdsClient(panda, 0x7D2, bus, timeout=1, debug=False)
OBD_client_0x7C0 = OBDClient(panda, 0x7C0, bus, timeout=1, debug=False)
UDS_client_0x7F0 = UdsClient(panda, 0x7F0, bus, timeout=10,
                             debug=False)  # 10 seconds of timeout in case CO2 sensor reboots

# Initialise memory objects for logging sorted by name to facilitate logging in csv file:
paramsToQuery = parametersToQuery_0x700 + parametersToQuery_0x7D2 + parametersToQuery_0x7C0 + parametersToQuery_0x7F0
paramsToQuery.sort(key=lambda x: x.name)
realtime_params = {}
for p in paramsToQuery:
    realtime_params[p.name] = -1

# Calculated derived params
_calculated_params = [  # Sorted alphabetically
    "co2_emissions (g/s)",
    "distance_travelled_since_startup (miles)",
    # "fuel_used_since_startup (US Gallons)",
    # "motor_power_delivered (KW)",
]
_calculated_params.sort()
calculated_params = {}
for p in calculated_params:
    calculated_params[p] = -1


def query(param: importantParameters, debug=False):
    if param.address == 0x700:
        value = UDS.readDataByIdentifier(UDS_client_0x700, param, loop=False, debug=debug)
    elif param.address == 0x7F0:
        value = UDS.readDataByIdentifier(UDS_client_0x7F0, param, loop=False, debug=debug)
        if args.percentage:
            co2.append(PPMtoPercentage(value))
        else:
            co2.append(value)
    elif param.address == 0x7D2:
        value = UDS.readDataByIdentifier(UDS_client_0x7D2, param, loop=False, debug=debug)
    elif param.address == 0x7C0:
        value = OBD.readDataByIdentifier(OBD_client_0x7C0, param, loop=False, debug=debug)
    realtime_params[param.name] = value


def get_headers():
    if args.gps:
        headers = "timestamp,latitude,longitude,"
    else:
        headers = "timestamp,"
    for param in paramsToQuery:
        headers += param.name
        if param.unit != "":
            headers += " (" + param.unit + "),"
        else:
            headers += ","

    for param in _calculated_params:
        headers += param + ","

    return headers


def write_results(log_file, timestamp):
    if args.gps:
        line = timestamp + "," + latest_gps_coordinates["latitude"] + "," + latest_gps_coordinates["longitude"] + ","
    else:
        line = timestamp + ","
    for v in realtime_params:
        line += str(realtime_params[v]) + ","
    for v in calculated_params:
        line += str(calculated_params[v]) + ","
    log_file.write(line + "\n")


def calculate_derived_params(mileageOnStartup):
    co2_emissions = 0.001518 * realtime_params.get("exhausts_co2_concentration") * (
                realtime_params.get("engine_exhaust_flow_rate") / 3600)
    calculated_params["co2_emissions (g/s)"] = co2_emissions

    distanceTravelledSinceStartup = realtime_params.get("total_distance_travelled") - mileageOnStartup
    calculated_params["distance_travelled_since_startup (miles)"] = distanceTravelledSinceStartup

    # motor_power_delivered = realtime_params.get("motor_torque") * realtime_params.get("motor_revolution") / 9.548 / 1000
    # calculated_params["motor_power_delivered (KW)"] = motor_power_delivered


if args.gps:
    latest_gps_coordinates = {"latitude": None, "longitude": None}


    def gpsLocationThread():
        ser = serial.Serial(port='/dev/ttyACM0', baudrate=115200, parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
        while 1:
            line = ser.readline()
            if line:
                result = line.decode()
                latitude, longitude = result[:-2].split(",", 2)
                latest_gps_coordinates["latitude"] = latitude
                latest_gps_coordinates["longitude"] = longitude


def main():
    if writeResults:
        date = datetime.now()
        log_file = open("../logs/RDE/" + date.strftime("%m-%d-%Y--%H-%M-%S") + ".csv", "w")
        log_file.write(get_headers() + "\n")

    if args.gps:
        gps_thread = Thread(target=gpsLocationThread, args=())
        gps_thread.start()
        while latest_gps_coordinates["latitude"] is None or latest_gps_coordinates[
            "longitude"] is None:  # wait to get first GPS measurement
            time.sleep(0.5)

    # Auxiliary values for calculating derived params:
    mileageOnStartup = UDS.readDataByIdentifier(UDS_client_0x700, IP["total_distance_travelled"], loop=False,
                                                debug=False)

    frequency = 5
    start = time.time()
    rk = Ratekeeper(frequency, boot_time=start, print_delay_threshold=0.05)
    while 1:
        for i in range(frequency):
            for p in paramsToQuery:
                print(p.name)
                query(p)
            calculate_derived_params(mileageOnStartup)
            elapsed_time = "{0:.4f}".format(time.time() - start)
            if writeResults:
                write_results(log_file, elapsed_time)
            if args.plot:
                update_plot(values=co2)
            rk.keep_time()


main()

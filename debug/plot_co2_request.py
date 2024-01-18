import argparse
from statistics import mean

import pyqtgraph as pg

from lib.parameters import parameters as IP
from lib.clients.UDS_client import readDataByIdentifier
from lib.protocols.UDS import UdsClient
from panda.python import Panda
import time

global start
pw = pg.plot(name="CO2 measurement")
pw.setLabel("left", "CO2 concentration (PPM)")
pw.showGrid(y=True, alpha=10000)
pw.setLabel("bottom", "time (s)")


def getTimestamp():
    return "{:.5f}".format(time.time() - start)


def PPM_to_Percentage(ppm):
    return ppm / 10000


def update_plot(values, times):
    pw.plot(times, values, clear=True, pen="r")
    pg.QtGui.QApplication.processEvents()


def main(args, saveToDisk=False):
    panda_serial = Panda.list()[0]
    panda = Panda(panda_serial)
    panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    panda.set_power_save(False)
    bus = 0
    panda.can_clear(bus)
    parameter = IP["exhausts_co2_concentration"]
    # parameter = IP["co2_emissions_prediction"]

    values = []
    times = []

    client = UdsClient(panda, parameter.address, bus, timeout=2, debug=False)
    if saveToDisk:
        from datetime import datetime
        date = datetime.now()
        f = open("../../logs/co2/" + date.strftime("%d-%m-%Y--%H-%M-%S") + ".csv", "w")
        f.write("co2 concentration (ppm),timestamp\n")

    start = time.time()
    while True:
        co2_ppm = readDataByIdentifier(uds_client=client, parameter=parameter, sleep=0, loop=False, raw_debug=False,
                                       debug=True)
        if args.percentage:
            values.append(PPM_to_Percentage(co2_ppm))
        else:
            values.append(co2_ppm)
        timestamp = time.time() - start
        times.append(timestamp)
        update_plot(values, times)

        if saveToDisk:
            f.write(str(co2_ppm) + "," + "{0:.4f}".format(timestamp) + "\n")


def singleRequest():
    panda = Panda()
    panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    panda.set_power_save(False)
    bus = 0
    panda.can_clear(bus)
    # parameter = IP["exhausts_co2_concentration"]
    parameter = IP["co2_emissions_prediction"]
    client = UdsClient(panda, parameter.address, bus, timeout=10, debug=False)

    times = []
    for i in range(1000):
        start = time.time()
        co2_ppm = readDataByIdentifier(uds_client=client, parameter=parameter, loop=False, raw_debug=False, debug=True)
        times.append(time.time() - start)
    print("average elapsed time: " + str(mean(times)))


if __name__ == "__main__":
    # singleRequest()
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p', '--percentage', action='store_true')
    args = parser.parse_args()

    if args.percentage:
        pw.setLabel("left", "CO2 concentration (%)")
    main(args, saveToDisk=False)

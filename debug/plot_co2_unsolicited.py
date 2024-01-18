import argparse
import pyqtgraph as pg
from panda.python import Panda
import binascii
import time

p = Panda()
p.set_can_speed_kbps(1, 500)  # Panda MUST listen at 500 Kbps or else won't listen anything
p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
start = time.time()
pw = pg.plot(name="CO2 measurement")
pw.setLabel("left", "CO2 concentration (PPM)")
pw.showGrid(y=True, alpha=10000)
pw.setLabel("bottom", "time (s)")


def getTimestamp():
    return "{:.5f}".format(time.time() - start)


def convert(data):
    ppm = int.from_bytes(data, byteorder="big")
    percentage = ppm / 10000
    return ppm, percentage


def update_plot(values, times):
    pw.plot(times, values, clear=True, pen="r")
    pg.QtGui.QApplication.processEvents()


def main(args, saveToDisk=False):
    addresses = [0x7f0]
    values = []
    times = []
    print_traffic = False

    if saveToDisk:
        from datetime import datetime
        date = datetime.now()
        f = open("../../logs/co2/" + date.strftime("%d-%m-%Y--%H-%M-%S") + ".csv", "w")
        f.write("co2 concentration (ppm),timestamp\n")

    while True:
        can_recv = p.can_recv()
        for address, x, dat, src in can_recv:
            if address in addresses:
                co2_ppm, co2_percentage = convert(dat)
                if args.percentage:
                    values.append(co2_percentage)
                else:
                    values.append(co2_ppm)
                timestamp = time.time() - start
                times.append(timestamp)
                update_plot(values, times)

                if print_traffic:
                    line = str("tmp: " + str(getTimestamp()) + ", address: " + "%04X" % (address)) + ", data: " + str(
                        binascii.hexlify(dat).decode()) + ", bus:" + str(src) + ", value (%): " + str(co2_percentage)
                    print(line)

                if saveToDisk:
                    f.write(str(co2_ppm) + "," + "{0:.4f}".format(timestamp) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p', '--percentage', action='store_true')
    args = parser.parse_args()

    if args.percentage:
        pw.setLabel("left", "CO2 concentration (%)")
    main(args, saveToDisk=False)

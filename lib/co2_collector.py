from panda.python import Panda
from lib.clients import UDS_client as UDS
from lib.protocols.UDS import UdsClient
from lib.parameters import parameters as IP
from datetime import datetime
import time
from lib.realtime import Ratekeeper

writeResults = False
if writeResults:
    date = datetime.now()
    log_file = open("../logs/co2/" + date.strftime("%m-%d-%Y--%H-%M-%S") + ".csv", "w")
    log_file.write("timestamp,co2_concentration(PPM)\n")


def write_results(timestamp, co2_concentration):
    log_file.write(timestamp + "," + co2_concentration + "\n")


def main():
    panda = Panda()
    panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    bus = 0

    UDSClient = UdsClient(panda, 0x7F0, bus, timeout=10, debug=False)
    param = IP["exhausts_co2_concentration"]

    frequency = 20
    start = time.time()
    rk = Ratekeeper(frequency, boot_time=start, print_delay_threshold=None)
    while 1:
        for i in range(frequency):
            co2 = UDS.readDataByIdentifier(UDSClient, parameter=param, loop=False, debug=False)
            elapsed_time = "{0:.4f}".format(time.time() - start)
            if writeResults:
                write_results(elapsed_time, co2)


            print(co2)
            rk.keep_time()


main()

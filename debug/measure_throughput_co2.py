from panda.python import Panda
import time
import struct
from lib.parameters import parameters as IP
from lib.clients.UDS_client import readDataByIdentifier
from lib.protocols.UDS import UdsClient

start = time.time()


def sec_since_boot():
    return time.time()


def getTimestamp():
    return "{:.5f}".format(time.time() - start)


def convert_to_PPM(bytes):
    co2 = struct.unpack('!ff', bytes)[0]
    ppm = co2 * 100
    percentage = ppm / 10000
    return ppm, percentage

def measure_throughput_fromCAN():
    panda_serial = Panda.list()[1]
    panda = Panda(panda_serial)
    panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    panda.set_power_save(False)
    bus = 0
    panda.can_clear(bus)
    messages = 0
    first_time_measuring = True
    while 1:
        can_recv = panda.can_recv()
        for address, x, dat, src in can_recv:
            if (address == 0x6EE and src == 0):
                if first_time_measuring:
                    first_time_measuring = False
                    start_time = time.time()
                else:
                    messages += 1
                    elapsed = time.time() - start_time

                    m_s = messages / elapsed
                    print("\r" + str(m_s) + " messages/s", end="")

def measure_throughput():
    panda_serial = Panda.list()[1]
    panda = Panda(panda_serial)
    panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    panda.set_power_save(False)
    bus = 0
    panda.can_clear(bus)
    # parameter = IP["exhausts_co2_concentration"]
    parameter = IP["co2_emissions_prediction"]
    messages = 0
    first_time_measuring = True

    client = UdsClient(panda, parameter.address, bus, timeout=2, debug=False)
    while 1:
        readDataByIdentifier(uds_client=client, parameter=parameter, sleep=0, loop=False, raw_debug=False, debug=False)
        if first_time_measuring:
            first_time_measuring = False
            start_time = time.time()
        else:
            messages += 1
            elapsed = time.time() - start_time

            m_s = messages / elapsed
            print("\r" + str(m_s) + " messages/s | RTT: " + str(1/m_s) + " s" , end="")




if __name__ == "__main__":
    measure_throughput()
    # measure_throughput_fromCAN()

#!/usr/bin/env python3
import time

from panda.python import Panda
from lib.parameters import parameters as IP
from lib.protocols.OBD import OBDClient, MessageTimeoutError


def readDataByIdentifier(obd_client: OBDClient, parameter, loop: bool = True, sleep: float = 0.3,
                         raw_debug: bool = False, debug: bool = False):
    while 1:
        try:
            response = obd_client.OBD_request(parameter.mode, parameter.pid)
            start_value = 2 + ((parameter.start - 1) * 2)

            if raw_debug:
                print(response)
            value = response[start_value: start_value + parameter.length * 2]
            value = parameter.converter(int(value, 16))
            if debug:
                print(parameter.name, ": ", value, " ", parameter.unit, " | ", response)
            if not loop:
                break
            time.sleep(sleep)
        except MessageTimeoutError:
            print("MessageTimeout Error in ReadDataByIdentifier for parameter identifier ", parameter.pid)
    return value


if __name__ == "__main__":
    panda = Panda()
    panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    panda.set_power_save(False)
    bus = 0
    panda.can_clear(bus)
    parameter = IP["fuel_input_volume"]

    client = OBDClient(panda, parameter.address, bus, timeout=0.5, debug=False)
    readDataByIdentifier(obd_client=client, parameter=parameter, sleep=1, loop=True, raw_debug=False, debug=True)

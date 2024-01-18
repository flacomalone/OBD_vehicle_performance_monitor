# This module sends via CAN bus an UDS request
# for calibrating the CO2 sensor using fresh air (400 PPM)

import binascii
from panda.python import Panda

if __name__ == "__main__":
    p = Panda()
    p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    bus = 0
    p.can_clear(bus)
    p.can_send(0x7F0, b"\x03\x2E\x12\x34\x00\x00\x00\x00", bus)
    while True:
        can_recv = p.can_recv()
        for address, x, dat, src in can_recv:
            if address == 0x7F8 and src == 0:
                if binascii.hexlify(dat).decode() == "066e123400000000":
                    print("Calibration finished successfully!")
                    exit()

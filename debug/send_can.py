#!/usr/bin/env python3
import binascii
import os
import sys
import time
from enum import Enum
from tqdm import tqdm
from lib.parameters import importantParameters as IP

start = time.time()

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from panda.python import Panda

class requests(Enum):
    testerPresent = b"\x02\x3e\x00\x00\x00\x00\x00\x00"
    diagnosticSessionControl = b"\x02\x10\x01\x00\x00\x00\x00\x00"
    diagnosticSessionControlExtended = b"\x02\x10\x03\x00\x00\x00\x00\x00"
    dynamicallyDefineDataIdentifier_clear_f301 = b"\x04\x2c\x03\xf3\x01\x00\x00\x00"
    dynamicallyDefineDataIdentifier_clear_f302 = b"\x04\x2c\x03\xf3\x02\x00\x00\x00"
    dynamicallyDefineDataIdentifier_define_f301_1 = b"\x10\x0c\x2c\x01\xf3\x01\x1f\x5b"
    dynamicallyDefineDataIdentifier_define_f301_2 = b"\x21\x01\x01\x1f\x01\x01\x01\x00"
    readScalingDataByIdentifier = b"\x03\x24\xf3\x01\x00\x00\x00\x00"
    readDataByIdentifier = b"\x03\x22\xf3\x01\x00\x00\x00\x00"


def sec_since_boot():
    return time.time()

def getTimestamp():
    return "{:.5f}".format(time.time() - start)

def heartbeat_thread(p):
    while True:
        try:
            p.send_heartbeat()
            time.sleep(0.5)
        except Exception:
            continue

def sendMessage(p, bus, addr, tx_message=None, timeout: int = 0, verbose=True):
    tx_address = addr
    if tx_message != None:
        message = tx_message
    else:
        message = b"\x03\x22\x1f\x9a\x00\x00\x00\x00"

    p.can_send(tx_address, message, bus)
    if verbose:
        print(str(str(getTimestamp()) + "," + "%04X" % (tx_address)) + "," + str(
            binascii.hexlify(message).decode()) + "," + str(bus) + "\n")

    if timeout == -1:  # Just send the message. No waiting time nor message removal from buffer
        p.can_clear(bus)
        return 0
    elif timeout == 0:  # No timeout, keep listening
        while True:
            can_recv = p.can_recv()
            p.can_clear(bus)
            for address, x, dat, src in can_recv:
                # if address >= 0x700 and src == 0:
                if address == tx_address + 8 and src == 0:
                    data = binascii.hexlify(dat).decode()
                    line = str(str(getTimestamp()) + "," + "%04X" % (address)) + "," + str(data) + "," + str(src) + "\n"
                    print(line)
    else: # Timeout defined in number of tries, not seconds
        for i in range(timeout):
            can_recv = p.can_recv()
            p.can_clear(bus)
            for address, x, dat, src in can_recv:
                # if address >= 0x700:
                if address == tx_address + 8 and src == 0:
                    data = binascii.hexlify(dat).decode()
                    line = str(str(getTimestamp()) + "," + "%04X" % (address)) + "," + str(data) + "," + str(src) + "\n"
                    print(line)
                    print(i)

def readDataByIdentifier_senderLoop(p, bus, parameter:IP):
    print("starting thread: send_loop()")
    pid = parameter.pid
    pid2 = pid[2:]
    pid1 = pid[0:2]
    tx_message = bytes.fromhex("0322" + str(pid1) + str(pid2) + "00000000")
    while True:
        p.can_send(parameter.address, tx_message, bus)
        time.sleep(0.3)


def discoverECU(p, bus):
    # addresses = [0x700 + i for i in range(2304)]
    addresses = [0x700 + i for i in range(256)]
    with tqdm(addresses) as addresses_:
        for addr in addresses_:
            addresses_.set_description(hex(addr))
            p.can_clear(bus)
            p.can_send(addr, b"\x03\x24\x1f\x5b\x00\x00\x00\x00", bus)
            for i in range(50):
                can_recv = p.can_recv()
                p.can_clear(bus)
                for address, x, dat, src in can_recv:
                    if address == addr + 8:
                        data = binascii.hexlify(dat).decode()
                        UDS_service = data[2:4]
                        if 1 or UDS_service == "62":
                            line = str(str(getTimestamp()) + "," + "%04X" % (address)) + "," + str(data) + "," + str(
                                src) + "\n"
                            print(line)
                        break
                    break


def sendBatch(p, bus, messages_to_send):
    for message in messages_to_send:
        sendMessage(p, bus, 0x7D2, message, timeout=1000, verbose=True)
    print("----> Batch has been sent")

if __name__ == "__main__":
    panda_serial = Panda.list()[0]
    p = Panda(panda_serial)
    # p = Panda()
    p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    p.set_power_save(False)
    bus = 0
    p.can_clear(bus)
    #p.set_can_speed_kbps(bus,  500)
    #p.set_can_data_speed_kbps(bus, 2000)
    iter = 0
    while 1:
        if iter % 2 == 0:
            p.can_send(0x700, b"\x03\x22\x12\x34\x00\x00\x00\x00", bus)
        else:
            p.can_send(0x700, b"\x03\x22\x12\x35\x00\x00\x00\x00", bus)
        iter += 1
        print("sent")
        print(".")
        time.sleep(1)
    # discoverECU(p,bus)
    # sendBatch(p,bus)

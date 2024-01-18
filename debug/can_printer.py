#!/usr/bin/env python3

import os
import time
from collections import defaultdict
import binascii
from functools import partial

from lib.protocols.CAN import CanClient
from lib.protocols.ISOTP import IsoTpMessage
from panda.python import Panda

start = time.time()

def sec_since_boot():
  return time.time()

def getTimestamp():
  return "{:.5f}".format(time.time() - start)

def can_printer():
  p = Panda()
  p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

  start = sec_since_boot()
  lp = sec_since_boot()
  msgs = defaultdict(list)
  canbus = int(os.getenv("CAN", "0"))
  while True:
    can_recv = p.can_recv()
    for address, _, dat, src in can_recv:
      if src == canbus:
        msgs[address].append(dat)

    if sec_since_boot() - lp > 0.1:
      dd = chr(27) + "[2J"
      dd += "%5.2f\n" % (sec_since_boot() - start)
      for k, v in sorted(zip(list(msgs.keys()), [binascii.hexlify(x[-1]) for x in list(msgs.values())])):
        dd += "%s(%6d) %s\n" % ("%04X(%4d)" % (k, k), len(msgs[k]), v)
      print(dd)
      lp = sec_since_boot()

def can_printer_file():
  p = Panda()
  p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
  addresses = [0x700,0x708,0x7C0,0x7C8,0x7D2,0x7DA]  # 2002 = 7D2, 2010 = 7DA
  f = open("/home/ubuntu/Desktop/pruebecita.csv", "w+")
  f.write("timestamp,address,data,src\n")
  while True:
    can_recv = p.can_recv()
    for address, x, dat, src in can_recv:
      if address in addresses and src == 0:
        line = str(str(getTimestamp()) + "," + "%04X" % (address)) + "," + str(binascii.hexlify(dat).decode()) +"," + str(src) + "\n"
        print(line)
        f.write(line)
        f.flush()
  f.close()

def can_printer_viewer():
  panda_serial = Panda.list()[0]
  p = Panda(panda_serial)
  p.set_can_speed_kbps(0, 500)
  p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
  while True:
    can_recv = p.can_recv()
    for address, x, dat, src in can_recv:
      if (1 or address >= 0x700):
        data = binascii.hexlify(dat)
        line = str(str(getTimestamp()) + "," + "%04X" % (address)) + "," + str(binascii.hexlify(dat).decode()) + "," + str(src)
        print(line)

if __name__ == "__main__":
  # can_printer_viewer()
  trial_8_inputs()

from lib.protocols.CAN import CanClient
from typing import Optional
import struct
import time

class MessageTimeoutError(Exception):
  pass

class IsoTpMessage():
  def __init__(self, can_client: CanClient, timeout: float = 1, debug: bool = False, max_len: int = 8):
    self._can_client = can_client
    self.timeout = timeout
    self.debug = debug
    self.max_len = max_len

  def send(self, dat: bytes) -> None:
    # throw away any stale data
    self._can_client.recv(drain=True)

    self.tx_dat = dat
    self.tx_len = len(dat)
    self.tx_idx = 0
    self.tx_done = False

    self.rx_dat = b""
    self.rx_len = 0
    self.rx_idx = 0
    self.rx_done = False

    if self.debug:
      print(f"ISO-TP: REQUEST - {hex(self._can_client.tx_addr)} 0x{bytes.hex(self.tx_dat)}")
    self._tx_first_frame()

  def _tx_first_frame(self) -> None:
    if self.tx_len < self.max_len:
      # single frame (send all bytes)
      if self.debug:
        print(f"ISO-TP: TX - single frame - {hex(self._can_client.tx_addr)}")
      msg = (bytes([self.tx_len]) + self.tx_dat).ljust(self.max_len, b"\x00")
      self.tx_done = True
    else:
      # first frame (send first 6 bytes)
      if self.debug:
        print(f"ISO-TP: TX - first frame - {hex(self._can_client.tx_addr)}")
      msg = (struct.pack("!H", 0x1000 | self.tx_len) + self.tx_dat[:self.max_len - 2]).ljust(self.max_len - 2, b"\x00")
    self._can_client.send([msg])

  def recv(self, timeout=None) -> Optional[bytes]:
    if timeout is None:
      timeout = self.timeout

    start_time = time.monotonic()
    try:
      while True:
        for msg in self._can_client.recv():
          self._isotp_rx_next(msg)
          start_time = time.monotonic()
          if self.tx_done and self.rx_done:
            return self.rx_dat
        # no timeout indicates non-blocking
        if timeout == 0:
          return None
        if time.monotonic() - start_time > timeout:
          raise MessageTimeoutError("timeout waiting for response")
    finally:
      if self.debug and self.rx_dat:
        print(f"ISO-TP: RESPONSE - {hex(self._can_client.rx_addr)} 0x{bytes.hex(self.rx_dat)}")

  def _isotp_rx_next(self, rx_data: bytes) -> None:
    # single rx_frame
    if rx_data[0] >> 4 == 0x0:
      self.rx_len = rx_data[0] & 0xFF
      self.rx_dat = rx_data[1:1 + self.rx_len]
      self.rx_idx = 0
      self.rx_done = True
      if self.debug:
        print(f"ISO-TP: RX - single frame - {hex(self._can_client.rx_addr)} idx={self.rx_idx} done={self.rx_done}")
      return

    # first rx_frame
    if rx_data[0] >> 4 == 0x1:
      self.rx_len = ((rx_data[0] & 0x0F) << 8) + rx_data[1]
      self.rx_dat = rx_data[2:]
      self.rx_idx = 0
      self.rx_done = False
      if self.debug:
        print(f"ISO-TP: RX - first frame - {hex(self._can_client.rx_addr)} idx={self.rx_idx} done={self.rx_done}")
      if self.debug:
        print(f"ISO-TP: TX - flow control continue - {hex(self._can_client.tx_addr)}")
      # send flow control message (send all bytes)
      msg = b"\x30\x00\x00".ljust(self.max_len, b"\x00")
      self._can_client.send([msg])
      return

    # consecutive rx frame
    if rx_data[0] >> 4 == 0x2:
      assert not self.rx_done, "isotp - rx: consecutive frame with no active frame"
      self.rx_idx += 1
      assert self.rx_idx & 0xF == rx_data[0] & 0xF, "isotp - rx: invalid consecutive frame index"
      rx_size = self.rx_len - len(self.rx_dat)
      self.rx_dat += rx_data[1:1 + rx_size]
      if self.rx_len == len(self.rx_dat):
        self.rx_done = True
      if self.debug:
        print(f"ISO-TP: RX - consecutive frame - {hex(self._can_client.rx_addr)} idx={self.rx_idx} done={self.rx_done}")
      return

    # flow control
    if rx_data[0] >> 4 == 0x3:
      assert not self.tx_done, "isotp - rx: flow control with no active frame"
      assert rx_data[0] != 0x32, "isotp - rx: flow-control overflow/abort"
      assert rx_data[0] == 0x30 or rx_data[0] == 0x31, "isotp - rx: flow-control transfer state indicator invalid"
      if rx_data[0] == 0x30:
        if self.debug:
          print(f"ISO-TP: RX - flow control continue - {hex(self._can_client.tx_addr)}")
        delay_ts = rx_data[2] & 0x7F
        # scale is 1 milliseconds if first bit == 0, 100 micro seconds if first bit == 1
        delay_div = 1000. if rx_data[2] & 0x80 == 0 else 10000.
        delay_sec = delay_ts / delay_div

        # first frame = 6 bytes, each consecutive frame = 7 bytes
        num_bytes = self.max_len - 1
        start = 6 + self.tx_idx * num_bytes
        count = rx_data[1]
        end = start + count * num_bytes if count > 0 else self.tx_len
        tx_msgs = []
        for i in range(start, end, num_bytes):
          self.tx_idx += 1
          # consecutive tx messages
          msg = (bytes([0x20 | (self.tx_idx & 0xF)]) + self.tx_dat[i:i + num_bytes]).ljust(self.max_len, b"\x00")
          tx_msgs.append(msg)
        # send consecutive tx messages
        self._can_client.send(tx_msgs, delay=delay_sec)
        if end >= self.tx_len:
          self.tx_done = True
        if self.debug:
          print(f"ISO-TP: TX - consecutive frame - {hex(self._can_client.tx_addr)} idx={self.tx_idx} done={self.tx_done}")
      elif rx_data[0] == 0x31:
        # wait (do nothing until next flow control message)
        if self.debug:
          print(f"ISO-TP: TX - flow control wait - {hex(self._can_client.tx_addr)}")

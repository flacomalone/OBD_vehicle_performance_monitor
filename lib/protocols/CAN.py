from typing import Callable, Tuple, List, Deque, Generator
from collections import deque
import time

class CanClient():
  def __init__(self, can_send: Callable[[int, bytes, int], None], can_recv: Callable[[], List[Tuple[int, int, bytes, int]]],
               tx_addr: int, rx_addr: int, bus: int, sub_addr: int = None, debug: bool = False):
    self.tx = can_send
    self.rx = can_recv
    self.tx_addr = tx_addr
    self.rx_addr = rx_addr
    self.rx_buff = deque()  # type: Deque[bytes]
    self.sub_addr = sub_addr
    self.bus = bus
    self.debug = debug

  def _recv_filter(self, bus: int, addr: int) -> bool:
    # handle functional addresses (switch to first addr to respond)
    if self.tx_addr == 0x7DF:
      is_response = addr >= 0x7E8 and addr <= 0x7EF
      if is_response:
        if self.debug:
          print(f"switch to physical addr {hex(addr)}")
        self.tx_addr = addr - 8
        self.rx_addr = addr
      return is_response
    if self.tx_addr == 0x18DB33F1:
      is_response = addr >= 0x18DAF100 and addr <= 0x18DAF1FF
      if is_response:
        if self.debug:
          print(f"switch to physical addr {hex(addr)}")
        self.tx_addr = 0x18DA00F1 + (addr << 8 & 0xFF00)
        self.rx_addr = addr
    return bus == self.bus and addr == self.rx_addr

  def _recv_buffer(self, drain: bool = False) -> None:
    while True:
      msgs = self.rx()
      if drain:
        if self.debug:
          print("CAN-RX: drain - {}".format(len(msgs)))
        self.rx_buff.clear()
      else:
        for rx_addr, _, rx_data, rx_bus in msgs or []:
          if self._recv_filter(rx_bus, rx_addr) and len(rx_data) > 0:
            rx_data = bytes(rx_data)  # convert bytearray to bytes

            if self.debug:
              print(f"CAN-RX: {hex(rx_addr)} - 0x{bytes.hex(rx_data)}")

            # Cut off sub addr in first byte
            if self.sub_addr is not None:
              rx_data = rx_data[1:]

            self.rx_buff.append(rx_data)
      # break when non-full buffer is processed
      if len(msgs) < 254:
        return

  def recv(self, drain: bool = False) -> Generator[bytes, None, None]:
    # buffer rx messages in case two response messages are received at once
    # (e.g. response pending and success/failure response)
    self._recv_buffer(drain)
    try:
      while True:
        yield self.rx_buff.popleft()
    except IndexError:
      pass  # empty

  def send(self, msgs: List[bytes], delay: float = 0) -> None:
    for i, msg in enumerate(msgs):
      if delay and i != 0:
        if self.debug:
          print(f"CAN-TX: delay - {delay}")
        time.sleep(delay)

      if self.sub_addr is not None:
        msg = bytes([self.sub_addr]) + msg

      if self.debug:
        print(f"CAN-TX: {hex(self.tx_addr)} - 0x{bytes.hex(msg)}")
      assert len(msg) <= 8

      self.tx(self.tx_addr, msg, self.bus)
      # prevent rx buffer from overflowing on large tx
      if i % 10 == 9:
        self._recv_buffer()
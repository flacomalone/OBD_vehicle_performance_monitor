"""Utilities for reading real time clocks and keeping soft real time constraints."""
import sys
import time
import multiprocessing
from typing import Optional

class Ratekeeper:
  def __init__(self, rate: int, boot_time: float, print_delay_threshold: Optional[float] = 0.0) -> None:
    """Rate in Hz for ratekeeping. print_delay_threshold must be nonnegative."""
    self._interval = 1. / rate
    self._boot_time = boot_time
    self._next_frame_time = (time.time() - self._boot_time) + self._interval
    self._print_delay_threshold = print_delay_threshold
    self._frame = 0
    self._remaining = 0.0
    self._process_name = multiprocessing.current_process().name

  @property
  def frame(self) -> int:
    return self._frame

  @property
  def remaining(self) -> float:
    return self._remaining

  # Maintain loop rate by calling this at the end of each loop
  def keep_time(self) -> bool:
    lagged = self.monitor_time()
    if self._remaining > 0:
      time.sleep(self._remaining)
    return lagged

  # this only monitor the cumulative lag, but does not enforce a rate
  def monitor_time(self) -> bool:
    lagged = False
    remaining = self._next_frame_time - (time.time() - self._boot_time)
    self._next_frame_time += self._interval
    if self._print_delay_threshold is not None and remaining < -self._print_delay_threshold:
      print("%s lagging by %.2f ms" % (self._process_name, -remaining * 1000), file=sys.stderr)
      lagged = True
    self._frame += 1
    self._remaining = remaining
    return lagged

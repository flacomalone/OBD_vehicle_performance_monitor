from functools import partial

from lib.protocols.CAN import CanClient
from lib.protocols.ISOTP import IsoTpMessage


class InvalidServiceIdError(Exception):
    pass


class MessageTimeoutError(Exception):
    pass


class OBDClient():
    def __init__(self, panda, tx_addr, bus: int = 0, timeout: float = 1, debug: bool = False,
                 tx_timeout: float = 1, response_pending_timeout: float = 5):
        self.bus = bus
        self.tx_addr = tx_addr
        self.rx_addr = self.tx_addr + 8
        self.timeout = timeout
        self.debug = debug
        can_send_with_timeout = partial(panda.can_send, timeout=int(tx_timeout * 1000))
        self._can_client = CanClient(can_send_with_timeout, panda.can_recv, self.tx_addr, self.rx_addr, self.bus,
                                     debug=self.debug)
        self.response_pending_timeout = response_pending_timeout

    def OBD_request(self, mode, pid):
        req = bytes([mode]) + bytes([pid])

        # send request, wait for response
        isotp_msg = IsoTpMessage(self._can_client, self.timeout, self.debug)
        isotp_msg.send(req)
        response_pending = True
        while True:
            timeout = self.response_pending_timeout if response_pending else self.timeout
            resp = isotp_msg.recv(timeout)

            if resp is None:
                continue

            resp_sid = resp[0] if len(resp) > 0 else None

            if mode + 0x40 != resp_sid:  # I should receive a mode equal to 41 for SAE standard mode 1 and 61 for Toyota proprietary mode
                resp_sid_hex = hex(resp_sid) if resp_sid is not None else None
                raise InvalidServiceIdError('invalid response service id: {}'.format(resp_sid_hex))

            # Return everything but mode -> PID and data
            return resp[1:].hex()

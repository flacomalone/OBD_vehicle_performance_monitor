import binascii
import time

from panda import Panda

start = time.time()


def getTimestamp():
    return "{:.5f}".format(time.time() - start)


def trialsimulate():
    """
    This module sends through the CAN bus a series of CAN messages in the same way as the vehicle would do (White Toyota Prius).
    It is assumed that the following parameters are asked in two different DynamicallyDefinedDataIdentifier (see README.md),
    and that these are also the hardcoded values that will be replied
    Message 1 (ECU 0x700):
      mass_air_flow: 		        PID: 1f10 - start: 01, length: 02 -> Response: 0x5dc8 (24000 g/min)
      engine_exhaust_flow_rate: 	PID: 1f9e - start: 01, length: 02 -> Response: 0x012c (300 kg/h)
      coolant_temperature: 	        PID: 1f05 - start: 01, length: 01 -> Response: 0x2B (43 degrees)
      vehicle_speed: 		        PID: 1f0d - start: 01, length: 01 -> Response: 0x38 (56 MPH)
    Message 2 (ECU 0x7D2):
      hybrid_batter_soc: 		    PID: 1f5b - start: 01, length: 01 -> Response: 0x63 (99 %)
      engine_speed:			        PID: 1f0c - start: 01, length: 02 -> Response: 0x1388 (5000 rpm)
      deceleration_sensor: 		    PID: 15ec - start: 01, length: 01 -> Response: 0xad (173 m/s^2)
      engine_mode:				    PID: 1063 - start: 01, length: 01 -> Response: 0x03

    The idea is to use this is script as a way to give the Micro CO2 Predictor the values that the car would in the same way
    For that, connect two white pandas to the same CAN bus and also attach the Micro CO2 Predictor. One of the pandas will
    act as the same panda that would query the Micro CO2 Predictor in a normal scenario, but the other will be in charge of
    sending the "vehicle replies" back to the CAN bus. Remember that you can create just one instance of the same panda,
    so to access to an array of Pandas connected to the PC, use panda=Panda.list()[i], with i being the index position of the
    panda that you want to use for each script.
    """
    panda_serial = Panda.list()[1]
    p = Panda(panda_serial)
    p.set_can_speed_kbps(0, 500)
    p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    while True:
        can_recv = p.can_recv()
        for address, x, dat, src in can_recv:
            if (address in [0x700, 0x7D2] and src == 0):
                data = binascii.hexlify(dat)
                line = str(str(getTimestamp()) + "," + "%04X" % (address)) + "," + str(
                    binascii.hexlify(dat).decode()) + "," + str(src)

                # create_extendedDiagnosticSession
                if str(binascii.hexlify(dat).decode()) == "0210030000000000":
                    if address == 0x700:
                        print("extendedDiagnosticSession (0x700)")
                        p.can_send(0x708, b"\x06\x50\x03\x00\x32\x01\xf4\x00", 0)
                    elif address == 0x7D2:
                        print("extendedDiagnosticSession (0x7D2)")
                        p.can_send(0x7DA, b"\x06\x50\x03\x00\x32\x01\xf4\x00", 0)

                # clearPreviousDynamicallyDefinedDataIdentifier (0x700)
                elif str(binascii.hexlify(dat).decode()) == "042c03f301000000":
                    if address == 0x700:
                        print("clearPreviousDynamicallyDefinedDataIdentifier (0x700)")
                        p.can_send(0x708, b"\x04\x6c\x03\xf3\x01\x00\x00\x00", 0)

                # clearPreviousDynamicallyDefinedDataIdentifier (0x7D2)
                elif str(binascii.hexlify(dat).decode()) == "042c03f302000000":
                    print("clearPreviousDynamicallyDefinedDataIdentifier (0x7D2)")
                    p.can_send(0x7DA, b"\x04\x6c\x03\xf3\x02\x00\x00\x00", 0)

                # createDynamicallyDefinedDataIdentifierByParameterId (first ISO-TP) (0x7D2)
                elif str(binascii.hexlify(dat).decode()) == "10142c01f3021f5b":
                    print("createDynamicallyDefinedDataIdentifierByParameterId (0x7D2)")
                    p.can_send(0x7DA, b"\x30\x00\x00\x00\x00\x00\x00\x00", 0)

                # Not necessary to ACK other data until the last message

                # createDynamicallyDefinedDataIdentifierByParameterId (last ISO-TP) (0x7D2)
                elif str(binascii.hexlify(dat).decode()) == "22ec010110630101":
                    p.can_send(0x7DA, b"\x04\x6c\x01\xf3\x02\x00\x00\x00", 0)


                # createDynamicallyDefinedDataIdentifierByParameterId (first ISO-TP) (0x700)
                elif str(binascii.hexlify(dat).decode()) == "10142c01f3011f10":
                    print("createDynamicallyDefinedDataIdentifierByParameterId (0x700)")
                    p.can_send(0x708, b"\x30\x00\x00\x00\x00\x00\x00\x00", 0)

                # Not necessary to ACK other data until the last message

                # createDynamicallyDefinedDataIdentifierByParameterId (last ISO-TP) (0x700)
                elif str(binascii.hexlify(dat).decode()) == "220501011f0d0101":
                    p.can_send(0x708, b"\x04\x6c\x01\xf3\x01\x00\x00\x00", 0)

                # readDataByIdentifier - dynamic id (part 1) (0x7DA - F302)
                elif str(binascii.hexlify(dat).decode()) == "0322f30200000000":
                    print("readDataByIdentifier (0x7DA - F302)")
                    p.can_send(0x7DA, b"\x10\x08\x62\xf3\x02\x63\x13\x88", 0)

                # readDataByIdentifier - dynamic id (part 1) (0x700 - F301)
                elif str(binascii.hexlify(dat).decode()) == "0322f30100000000":
                    print("readDataByIdentifier (0x700 - F301)")
                    p.can_send(0x708, b"\x10\x09\x62\xf3\x01\x5d\xc8\x01", 0)

                # readDataByIdentifier - dynamic id (part 2)
                elif str(binascii.hexlify(dat).decode()) == "3000000000000000":
                    if address == 0x7D2:
                        p.can_send(0x7DA, b"\x21\xad\x03\x00\x00\x00\x00\x00", 0)
                        # hybrid_batter_soc: 		    1f5b - 01, 01 -> x63 (99)
                        # engine_speed:			        1f0c - 01, 02 -> x1388 (5000)
                        # deceleration_sensor: 		    15ec - 01, 01 -> xad (173)
                        # engine_mode:				    1063 - 01, 01 -> 03
                    elif address == 0x700:
                        p.can_send(0x708, b"\x21\x2c\x2b\x38\x00\x00\x00\x00", 0)
                        # mass_air_flow: 		        1f10 - 01, 02 -> x5dc8 (24000)
                        # engine_exhaust_flow_rate: 	1f9e - 01, 02 -> x012c (300)
                        # coolant_temperature: 	        1f05 - 01, 01 -> 2B (43)
                        # vehicle_speed: 		        1f0d - 01, 01 -> 38 (56)

                print(line)


if __name__ == "__main__":
    trialsimulate()

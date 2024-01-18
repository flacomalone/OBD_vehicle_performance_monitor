import os
import time
import serial
from serial import SerialException


def connectSerial(port="/dev/ttyACM0", baudrate=115200):
    ser = serial.Serial(
        # Serial Port to read the data from
        port=port,

        # Rate at which the information is shared to the communication channel
        baudrate=baudrate,

        # Applying Parity Checking (none in this case)
        parity=serial.PARITY_NONE,

        # Pattern of Bits to be read
        stopbits=serial.STOPBITS_ONE,

        # Total number of bits to be read
        bytesize=serial.EIGHTBITS,

        # Number of serial commands to accept before timing out
        timeout=1
    )
    return ser


def gps(write_results=False):
    if write_results:
        log_file = open(os.path.dirname(os.path.abspath(__file__)) + "/../logs/gps/" + time.strftime("%m-%d-%Y--%H-%M-%S") + ".csv", "w")
        log_file.write("timestamp,latitude,longitude" + "\n")

    try:
        serial = connectSerial()
        firstMeasurement = True
        while 1:
            line = serial.readline()
            if line:
                if firstMeasurement:
                    start = time.time()
                    firstMeasurement = False
                result = line.decode()
                latitude, longitude = result[:-2].split(",", 2)
                elapsed_time = "{0:.4f}".format(time.time() - start)
                print("Time:", elapsed_time, " | latitude:", float(latitude), " | longitude:", float(longitude))
                if write_results:
                    log_file.write(elapsed_time + "," + latitude + "," + longitude + "\n")
    except SerialException as e:
        print(e)
    except:
        print("An unhandled exception occurred while connecting to serial port")

if __name__ == "__main__":
    gps(write_results=False)

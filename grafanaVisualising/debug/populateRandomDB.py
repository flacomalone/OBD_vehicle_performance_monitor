import random
import time
from grafanaVisualising.DB import MySQL_DB
from grafanaVisualising.config_params import primary_params, secondary_params, samplingRate
from lib.realtime import Ratekeeper

if __name__ == "__main__":
    DB = MySQL_DB(primary_params, secondary_params, deleteOnStartUp=True, includeGPS=True, verbose=False)
    start = time.time()
    rk = Ratekeeper(20, boot_time=start, print_delay_threshold=0.05)
    latest_gps_location = {"latitude": None, "longitude": None, "altitude": None}
    while True:
        for i in range(samplingRate):
            for p in primary_params:
                primary_params[p] = random.randint(1, 100)
            for p in secondary_params:
                secondary_params[p] = random.randint(1, 100)
            for p in latest_gps_location:
                latest_gps_location[p] = str(random.randint(1, 100))

            DB.insertRecords(primary_params, secondary_params, latest_gps_location, str(time.time()))
            rk.keep_time()

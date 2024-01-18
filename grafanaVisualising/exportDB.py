import argparse
import datetime
from datetime import datetime

from DB import MySQL_DB
import os


def dateToEpoch(date):
    mm, dd, YYYY, _, HH, MM, SS = date.split("-", maxsplit=6)
    return datetime(int(YYYY), int(mm), int(dd), hour=int(HH), minute=int(MM), second=int(SS)).strftime('%s')


def main(args):
    # Read file name from file "latest_connection_date.txt"
    f = open(os.path.dirname(os.path.abspath(__file__)) + "/latest_connection_date.txt", "r")
    filename = f.readlines()[0]
    f.close()

    # Create connection with DB
    DB = MySQL_DB({}, {}, includeGPS=False, deleteOnStartUp=False, overwriteDate=False, verbose=True)

    # Open CSV file
    f = open("../logs/RDE/" + filename + ".csv", "w")

    # Write headers
    includeGPS = False
    headers = "timestamp,"
    params = []
    tables = DB.query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'grafana';")
    for t in tables:
        if t[0] == "timestamp_samples":
            continue
        elif t[0] == "location_samples":
            includeGPS = True
            continue
        else:
            headers += str(t[0])[:-8] + ","  # remove "_samples" from name
            params.append(str(t[0]))
    if includeGPS:
        headers += "latitude,longitude,altitude"
    else:
        headers = headers[:-1]  # remove last ","
    f.write(headers + "\n")

    # Get results from query
    sentence = "SELECT * FROM timestamp_samples"
    if args.s:
        sentence += ' WHERE timestamp >= "' + dateToEpoch(args.s) + '"'
        if args.f:
            sentence += ' AND timestamp <= "' + dateToEpoch(args.f) + '"'
    sentence += ";"
    tuples = DB.query(sentence)

    for i in range(len(tuples)-1):
        timestampID = str(tuples[i][0])
        timestamp = str(tuples[i][1])
        row = timestamp + ","
        values = {}
        for p in params:
            values[p] = str(DB.query("SELECT value FROM " + p + " INNER JOIN timestamp_samples ON " +
                                     p + ".timestampID = timestamp_samples.rowID WHERE timestamp_samples.rowID = "
                                     + timestampID + ";")[0][0])
        if includeGPS:
            location = DB.query("SELECT latitude,longitude,altitude FROM location_samples "
                                    "INNER JOIN timestamp_samples ON location_samples.timestampID = "
                                    "timestamp_samples.rowID WHERE timestamp_samples.rowID = " + timestampID + ";")
            values["latitude"] = str(location[0][0])
            values["longitude"] = str(location[0][1])
            values["altitude"] = str(location[0][2])

        for v in values:
            value = values[v]
            if value[-11:] == ".0000000000":  # parse to int
                row += str(int(float(value))) + ","
            else:
                row += value + ","
        row = row[:-1]
        f.write(row + "\n")

    f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-s', type=str)  # Starting date in format
    parser.add_argument('-f', type=str)  # Finish date
    args = parser.parse_args()
    main(args)

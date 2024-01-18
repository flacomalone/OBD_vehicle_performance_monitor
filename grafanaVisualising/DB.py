import time

import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os


class MySQL_DB:
    def __init__(self, primaryParams: dict, secondaryParams: dict, includeGPS: bool = False,
                 deleteOnStartUp: bool = False, overwriteDate: bool = False, verbose: bool = True):
        self.connection, self.cursor = self.connect()
        self.verbose = verbose
        self.deleteOnStartUp = deleteOnStartUp
        self.includeGPS = includeGPS
        self.list_params = sorted(list(primaryParams.keys()) + list(secondaryParams.keys()))
        if self.deleteOnStartUp:
            # Delete previous tables and indexes
            self.deleteTables()

            # Create table definitions with defined primary and secondary params
            self.defineTables()
            self.defineIndex()

            self.lastTimestampId = 1
        else:
            self.lastTimestampId = self.query("select count(rowID) from timestamp_samples;")[0][0]

        # Only overwrite the latest connection_date when intending to record and export the gathered data
        if overwriteDate:
            f = open(os.path.dirname(os.path.abspath(__file__)) + "/latest_connection_date.txt", "w")
            f.write(datetime.now().strftime("%m-%d-%Y--%H-%M-%S"))
            f.close()

    def connect(self):
        try:
            connection = mysql.connector.connect(host='localhost',
                                                 database='grafana',
                                                 user='root',
                                                 password='WhatTheHell!')
            if connection.is_connected():
                cursor = connection.cursor(buffered=True)
                cursor.execute("select database();")
                record = cursor.fetchone()
                print("SQL -> Connected successfully to database/s: ", record)

        except Error as e:
            print("Error while connecting to MySQL", e)
        return connection, cursor

    def close(self, connection):
        connection.close()
        if self.verbose:
            print("SQL -> Connection closed")

    def execute(self, sentence: str, verbose=False):
        self.cursor.execute(sentence)
        self.connection.commit()
        if verbose:
            print('SQL -> Command "' + sentence + '" was executed correctly')

    def query(self, sentence: str, verbose: object = False) -> tuple:
        self.cursor.execute(sentence)
        self.connection.commit()
        if verbose:
            print('SQL -> Query \n"' + sentence + '"\n was executed correctly')
        return self.cursor.fetchall()

    def deleteTables(self):
        tables = self.query("SHOW TABLES;")
        for t in tables:
            if t[0] != "timestamp_samples":  # Cannot eliminate this one if there is Foreign Keys associated to it
                self.execute("DROP TABLE IF EXISTS " + str(t[0]) + ";")
        self.execute("DROP TABLE IF EXISTS timestamp_samples;")
        # Given the foreign key constraint set to cascade, it will also delete all child tables.
        if self.verbose:
            print("SQL -> All the tables were deleted.")

    def defineTables(self):
        # timestamp_samples table
        sentence = "CREATE TABLE timestamp_samples (" \
                   "rowID INT NOT NULL AUTO_INCREMENT, " \
                   "timestamp DECIMAL(20,10) NOT NULL, " \
                   "PRIMARY KEY (rowID)) " \
                   "ENGINE=InnoDB;\n\n"
        self.execute(sentence, verbose=self.verbose)

        # primary and secondary params tables
        for i in range(len(self.list_params)):
            sentence = "CREATE TABLE " + self.list_params[i] + "_samples (" + \
                       "rowID INT NOT NULL AUTO_INCREMENT, " + \
                       "timestampID INT NOT NULL, " + \
                       "value DECIMAL (20,10), " + \
                       "PRIMARY KEY (rowID)," \
                       "FOREIGN KEY (timestampID) REFERENCES timestamp_samples(rowId)" \
                       "ON UPDATE CASCADE " + \
                       "ON DELETE CASCADE) " \
                       "ENGINE=InnoDB;\n\n"
            self.execute(sentence, verbose=self.verbose)

        # location_samples table
        if self.includeGPS:
            sentence = "CREATE TABLE location_samples (" + \
                       "rowID INT NOT NULL AUTO_INCREMENT, " + \
                       "timestampID INT NOT NULL, " + \
                       "latitude" + " DECIMAL (20,10), " + \
                       "longitude" + " DECIMAL (20,10), " + \
                       "altitude" + " DECIMAL (20,10), " + \
                       "PRIMARY KEY (rowID)," \
                       "FOREIGN KEY (timestampID) REFERENCES timestamp_samples(rowId)" \
                       "ON UPDATE CASCADE " + \
                       "ON DELETE CASCADE) " \
                       "ENGINE=InnoDB;\n\n"
            self.execute(sentence, verbose=self.verbose)

    def defineIndex(self):
        sentence = "CREATE UNIQUE INDEX timestamp_index ON timestamp_samples (rowID);"
        self.execute(sentence, verbose=self.verbose)

    def insertRecords(self, primaryParams: dict, secondaryParams: dict, latestLocation: dict, timestamp: str):
        list_values = {**primaryParams, **secondaryParams}  # Combine dictionaries

        # timestamp_samples table
        sentence = "INSERT INTO timestamp_samples (timestamp) VALUES (" + timestamp + "); "
        self.execute(sentence, verbose=self.verbose)

        # primary and secondary params tables
        for i in list_values:
            sentence = "INSERT INTO " + i + "_samples (timestampID, value) VALUES (" + \
                       str(self.lastTimestampId) + ", " + str(list_values[i]) + "); "
            self.execute(sentence, verbose=self.verbose)

        # location_samples table
        if self.includeGPS:
            sentence = "INSERT INTO location_samples (timestampID, latitude, longitude, altitude) VALUES (" + \
                       str(self.lastTimestampId) + ", " + \
                       latestLocation["latitude"] + ", " + \
                       latestLocation["longitude"] + ", " + \
                       latestLocation["altitude"] + "); "
            self.execute(sentence, verbose=self.verbose)

        self.lastTimestampId += 1
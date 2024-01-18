import pathlib
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
import argparse
import pandas


def ppmToPercentage(array):
    concentrations_percentage = []
    for i in range(array.size):
        val = array[i]
        concentrations_percentage.append(float(val / 10000))
    return concentrations_percentage


def plot(args):
    columns = ["concentration", "timestamp"]
    df = pandas.read_csv(args.file, usecols=columns)
    concentrations = df["concentration"]
    if args.percentage:
        concentrations = ppmToPercentage(concentrations.values)
    timestamps = df["timestamp"]

    plt = pg.plot()
    plt.setWindowTitle("CO2 concentration")
    if args.percentage:
        plt.setLabel("left", "CO2 concentration (%)")
        plt.showGrid(y=True, alpha=1)
    else:
        plt.setLabel("left", "CO2 concentration (PPM)")
        plt.showGrid(y=True, alpha=1000)
    plt.setLabel("bottom", "time (s)")
    plt.plot(timestamps, concentrations, pen="r")
    QtGui.QApplication.instance().exec_()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Replay previously recorded CO2 measurements')
    parser.add_argument('-f', '--file', required=True, type=pathlib.Path)
    parser.add_argument('-p', '--percentage', action='store_true')
    args = parser.parse_args()
    plot(args)

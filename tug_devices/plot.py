import matplotlib
matplotlib.use('Agg')

import os
import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, HourLocator, DateFormatter

class Plot:
    class PlotItem:
        def __init__(self, plot_config):
            self.parameter = plot_config["parameter"]
            self.on_change = plot_config["on_change"]
            self.time_interval = plot_config["time_interval"]
            self.height = plot_config["height"]
            self.width = plot_config["width"]
            self.file_path = ""
            self.file_name = plot_config["file_name"]
            self.title = plot_config["title"]
            # self.path = plot_config["path"]
            # self.file_name = plot_config["file_name"]

            self.times = []
            self.values = []

        def logValue(self, parameter, time, value):
            if parameter == self.parameter:
                self.times.append(self.getDateTime(time))
                self.values.append(value)

        def generatePlot(self):
            """generate the plot"""
            plt.figure(1)
            fig, ax = plt.subplots( nrows=1, ncols=1, figsize=(8,5) )  # create figure & 1 axis
            # ax.plot([0,1,2], [10,20,3])
            ax.xaxis.set_major_locator(DayLocator())
            ax.xaxis.set_minor_locator(HourLocator(range(0, 25, 6)))
            ax.xaxis.set_major_formatter(DateFormatter('Day #%d'))

            ax.set_ylabel(self.parameter)
            ax.get_yaxis().get_major_formatter().set_useOffset(False)
            plt.title(self.title)
            ax.plot(self.times, self.values, linestyle="solid", marker="o", markersize=6, markeredgecolor="blue", alpha=0.3, color="blue")

            # ax.fmt_xdata = DateFormatter('%H:%M:%S')
            ax.grid(True)
            fig.autofmt_xdate()

            # ticklines = ax.get_xticklines() + ax.get_yticklines()
            # gridlines = ax.get_xgridlines() + ax.get_ygridlines()
            ticklabels = ax.get_xticklabels() + ax.get_yticklabels()
            for label in ticklabels:
                label.set_fontsize('medium')

            # fig.savefig('img.png')   # save the figure to file
            print "parameter = {}".format(self.parameter)
            print "file path = " + self.file_path
            print "save figure to {}".format(os.path.join(self.file_path, self.file_name))
            fig.savefig(os.path.join(self.file_path, self.file_name), format='pdf', dpi=1200)
            plt.close(fig)    # close the figure

        def getDateTime(self, seconds):
            # datetime.datetime.utcfromtimestamp(seconds).strftime('%H:%M:%S')
            return datetime.datetime.utcfromtimestamp(seconds)

    def __init__(self, config):
        try:
            self.resolution = config["resolution"]
            self.plot_items = []
            self.initPlotItems(config["items"])
        except Exception as inst:
            print inst
            raise Exception("Invalid plot parameters ({})".format(inst))

    def initPlotItems(self, items_config):
        for item in items_config:
            self.plot_items.append(Plot.PlotItem(item))

    def generatePlots(self):
        for item in self.plot_items:
            item.generatePlot()

    def logValue(self, parameter, time, value):
        """log values for the plots"""
        for item in self.plot_items:
            item.logValue(parameter, time, value)

    def setFilePaths(self, path):
        for item in self.plot_items:
            item.file_path = path


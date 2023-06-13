import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas,  NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import RectangleSelector

from osgeo import gdal
import datashader as ds
from datashader.mpl_ext import dsshow
import pandas as pd
from matplotlib.widgets import RectangleSelector
import numpy as np
from skimage import exposure
from matplotlib import colors
from .feature_space_dialog import FeatureSpaceDialog
from uuid import uuid4
from qgis.core import QgsRasterLayer, QgsVectorLayer,  QgsProject, QgsProcessingParameterRasterDestination
import processing

cmap = colors.ListedColormap(['red'])

def using_datashader(ax, x, y):

    df = pd.DataFrame(dict(x=x, y=y))
    dsartist = dsshow(
        df,
        ds.Point("x", "y"),
        ds.count(),
        vmin=0,
        vmax=35,
        norm="linear",
        aspect="auto",
        ax=ax,
    )

class GuiProgram(FeatureSpaceDialog):
    def __init__(self, dialog, wcb, wcb2, wcb_red, wcb_green, wcb_blue, sb, sb2, sb_red, sb_green, sb_blue):
        self.dialog = dialog

        self.wcb = wcb
        self.wcb2= wcb2
        self.wcb_red= wcb_red
        self.wcb_green= wcb_green
        self.wcb_blue= wcb_blue

        self.sb = sb
        self.sb2 = sb2
        self.sb_red = sb_red
        self.sb_green = sb_green
        self.sb_blue = sb_blue

        FeatureSpaceDialog.__init__(self)
        self.setupUi(dialog)
        
        figure = Figure()
        axis = figure.add_subplot(111)
        figure2 = Figure()
        axis2 = figure2.add_subplot(111)
        self.initialize_figure(figure, axis, figure2, axis2)

        self.pushButton.clicked.connect(self.change_plot)
        self.add_raster.clicked.connect(self.save_as_raster)
        self.add_vector.clicked.connect(self.save_as_vector)

    def write_tiff(self, data, filename, proj, geo, dtype=gdal.GDT_Float32):
        rows, cols = data.shape
        driver = gdal.GetDriverByName("GTiff")
        DataSet = driver.Create(filename, cols, rows, 1, dtype)
        DataSet.SetGeoTransform(geo)
        DataSet.SetProjection(proj)
        DataSet.GetRasterBand(1).WriteArray(data)
        DataSet.FlushCache()
        DataSet = None

    def on_click(self, event):
        if event.button == 1 or event.button == 3 and not self.rs.active:
            self.rs.set_active(True)
        else:
            self.rs.set_active(False)

    def line_select_callback(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        b1_condition = np.logical_and(self.band1 > x1, self.band1 < x2)
        b2_condition = np.logical_and(self.band2 > y1, self.band2 < y2)
        self.conds = np.logical_and(b1_condition, b2_condition).astype(float)
        self.conds[self.conds == 0]= np.nan

        self.ax2.clear()
        self.ax2.imshow(self.new_im)
        self.ax2.imshow(self.conds, cmap=cmap, alpha=0.6)
        self.ax2.axis('off')
        self.fig2.tight_layout()
        self.canvas2.draw()
        

    def save_as_raster(self):
        dest = QgsProcessingParameterRasterDestination(name=str(uuid4()))
        filename = dest.generateTemporaryDestination()
    
        proj = self.image1.GetProjection()
        geo = self.image1.GetGeoTransform()
        data = self.conds
        self.write_tiff(data, filename, proj, geo)

        layer = QgsRasterLayer(filename, 'feature_space_selected')
        if not layer.isValid():
            print("Layer failed to load!")
        QgsProject.instance().addMapLayer(layer)

    def save_as_vector(self):
        dest = QgsProcessingParameterRasterDestination(name=str(uuid4()))
        filename = dest.generateTemporaryDestination()
        
        proj = self.image1.GetProjection()
        geo = self.image1.GetGeoTransform()
        data = self.conds
        self.write_tiff(data, filename, proj, geo)

        poly_opts = { 'BAND' : 1, 'EXTRA' : f'-mask {filename}', 'INPUT' : filename, 'OUTPUT' : 'TEMPORARY_OUTPUT' }
        vlayer = processing.run("gdal:polygonize", poly_opts)
        vlayer = QgsVectorLayer(vlayer["OUTPUT"], "feature_space_selected_vector")
        QgsProject.instance().addMapLayer(vlayer)

    def get_band_as_array(self, filepath, band_number, flat=False):
        image = gdal.Open(filepath)
        band = image.GetRasterBand(band_number).ReadAsArray()
        if flat:
            return image, band, band.flatten()
        else:
            return image, band
    
    def create_rgb(self, red, green, blue):
        rgb = np.zeros((red.shape[0],red.shape[1], 3))
        rgb[:,:,0] = red
        rgb[:,:,1] = green
        rgb[:,:,2] = blue
        return rgb

    def stretch_im(self, arr, str_clip):
        s_min = str_clip
        s_max = 100 - str_clip
        arr_rescaled = np.zeros_like(arr)
        for band in range(3):
            lower, upper = np.nanpercentile(arr[:,:,band], (s_min, s_max))
            arr_rescaled[:,:,band] = exposure.rescale_intensity(arr[:,:,band], in_range=(lower, upper))
        return arr_rescaled.copy()

    def change_plot(self):
        self.ax.clear()
        self.ax2.clear()

        try:
            self.image1, self.band1, self.x = self.get_band_as_array(self.wcb.currentLayer().source(), int(self.sb.currentText()), True)
            self.image2, self.band2, self.y = self.get_band_as_array(self.wcb2.currentLayer().source(), int(self.sb2.currentText()), True)
            using_datashader(self.ax, self.x, self.y)
            self.ax.set_xlim(min(self.x)+ min(self.x)*0.1, max(self.x)+ max(self.x)*0.1)
            self.ax.set_ylim(min(self.y) + min(self.y)*0.1, max(self.y)+ max(self.y)*0.1)
            # Make sure everything fits inside the canvas
            self.fig.tight_layout()
            self.canvas.draw()
        except:
            pass

        try:
            self.image_red, self.band_red = self.get_band_as_array(self.wcb_red.currentLayer().source(), int(self.sb_red.currentText()))
            self.image_green, self.band_green = self.get_band_as_array(self.wcb_green.currentLayer().source(), int(self.sb_green.currentText()))
            self.image_blue, self.band_blue = self.get_band_as_array(self.wcb_blue.currentLayer().source(), int(self.sb_blue.currentText()))

            self.rgb = self.create_rgb(self.band_red, self.band_green, self.band_blue)
            self.new_im = self.stretch_im(self.rgb, 1)
            self.ax2.imshow(self.new_im)
            self.ax2.axis('off')
            self.fig2.tight_layout()
            self.canvas2.draw()
        except Exception as e:
            print(e)
            pass

    def initialize_figure(self, fig, ax, fig2, ax2):
        self.fig = fig
        self.ax = ax

        self.fig2 = fig2
        self.ax2 = ax2

        self.canvas = FigureCanvas(self.fig)
        self.verticalLayout.addWidget(self.canvas)
        self.canvas.draw()

        self.canvas2 = FigureCanvas(self.fig2)
        self.verticalLayout_2.addWidget(self.canvas2)
        self.canvas2.draw()
        
        # Toolbar creation
        # self.toolbar = NavigationToolbar(self.canvas, self.plotWindow,
        #                                  coordinates=True)
        # self.verticalLayout.addWidget(self.toolbar)
        self.rs = RectangleSelector(self.ax, self.line_select_callback,
                                                    useblit=True,
                                                    button=[1, 3],  # don't use middle button
                                                    minspanx=5, minspany=5,
                                                    spancoords='pixels',
                                                    interactive=True)


            # set Qlayout properties and show window
            # self.gridLayout = QtW.QGridLayout(self._main)
            # self.setLayout(self.verticalLayout)
            # self.show()

            # connect mouse events to canvas
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
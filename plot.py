import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas,  NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import RectangleSelector
from osgeo import gdal
from matplotlib.widgets import RectangleSelector
import numpy as np
from matplotlib import colors
from .feature_space_dialog import FeatureSpaceDialog
from uuid import uuid4
from qgis.core import QgsRasterLayer, QgsVectorLayer,  QgsProject, QgsProcessingParameterRasterDestination
import processing
from matplotlib.colors import LogNorm

cmap = colors.ListedColormap(['red'])

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

    def create_scatter(self, ax, x, y):
        bins = [1000, 1000] #TODO calculate dynamically
        hh, locx, locy = np.histogram2d(x, y, bins=bins)
        z = np.array([hh[np.argmax(a<=locx[1:]),np.argmax(b<=locy[1:])] for a,b in zip(x,y)])
        idx = z.argsort()
        x2, y2, z2 = x[idx], y[idx], z[idx]
        s = ax.scatter(x2, y2, c=z2, cmap='jet', marker='.', s=0.05, norm = LogNorm()) 

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
        self.ax2.imshow(self.rgb)
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

        input_name = self.layer_name_input.toPlainText()
        if input_name == '':
            layer_name = "feature_space_selected_raster"
        else:
            layer_name = input_name

        layer = QgsRasterLayer(filename, layer_name)
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

        input_name = self.layer_name_input.toPlainText()
        if input_name == '':
            layer_name = "feature_space_selected_vector"
        else:
            layer_name = input_name

        poly_opts = { 'BAND' : 1, 'EXTRA' : f'-mask {filename}', 'INPUT' : filename, 'OUTPUT' : 'TEMPORARY_OUTPUT' }
        vlayer = processing.run("gdal:polygonize", poly_opts)
        vlayer = QgsVectorLayer(vlayer["OUTPUT"], layer_name)
        QgsProject.instance().addMapLayer(vlayer)

    def get_band_as_array(self, filepath, band_number, flat=False):
        image = gdal.Open(filepath)
        band = image.GetRasterBand(band_number)
        nodata = band.GetNoDataValue()
        band = band.ReadAsArray()

        if flat:
            return image, band, nodata, band.flatten()
        else:
            return image, band, nodata
    
    def create_rgb(self, red, green, blue):
        rgb = np.zeros((red.shape[0],red.shape[1], 3))
        rgb[:,:,0] = red
        rgb[:,:,1] = green
        rgb[:,:,2] = blue
        return rgb

    def change_plot(self):
        self.ax.clear()
        self.ax2.clear()

        try:
            xfile = self.wcb.currentLayer().source()
            yfile = self.wcb2.currentLayer().source()
            xband = int(self.sb.currentText())
            yband = int(self.sb2.currentText())

            self.image1, self.band1, self.nodatax, self.x  = self.get_band_as_array(xfile, xband, True)
            self.image2, self.band2, self.nodatay, self.y = self.get_band_as_array(yfile, yband, True)
            self.create_scatter(self.ax, self.x, self.y)

            self.x = self.x[self.x!=self.nodatax]
            self.y = self.y[self.y!=self.nodatay]

            amountx = max(self.x)*0.1
            amounty = max(self.y)*0.1
            self.ax.set_xlim(min(self.x) - amountx, max(self.x) + amountx)
            self.ax.set_ylim(min(self.y) - amounty, max(self.y) + amounty)

            self.ax.set_xlabel(xfile.split('/')[-1] + '\nBand: ' + str(xband))
            self.ax.set_ylabel(yfile.split('/')[-1] + '\nBand: ' + str(yband))
            # Make sure everything fits inside the canvas
            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print(e)
            pass

        try:
            self.image_red, self.band_red, _ = self.get_band_as_array(self.wcb_red.currentLayer().source(), int(self.sb_red.currentText()))
            self.image_green, self.band_green, _ = self.get_band_as_array(self.wcb_green.currentLayer().source(), int(self.sb_green.currentText()))
            self.image_blue, self.band_blue, _ = self.get_band_as_array(self.wcb_blue.currentLayer().source(), int(self.sb_blue.currentText()))

            self.rgb = self.create_rgb(self.band_red, self.band_green, self.band_blue)
            self.rgb = self.rgb/self.rgb.max()
            self.ax2.imshow(self.rgb)
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
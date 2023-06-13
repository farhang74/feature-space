# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FeatureSpace
                                 A QGIS plugin
 test
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-06-05
        git sha              : $Format:%H$
        copyright            : (C) 2023 by fz
        email                : fz
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox
from PyQt5.QtWidgets import QComboBox, QLabel

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .feature_space_dialog import FeatureSpaceDialog
import os.path
from .plot import GuiProgram


class FeatureSpace:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'FeatureSpace_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&feature space')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('FeatureSpace', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/feature_space/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'feature space'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&feature space'),
                action)
            self.iface.removeToolBarIcon(action)



    def load_fields(self, wcb, sb):
        lyr_nm=wcb.currentLayer()
        print(lyr_nm)

        try:
            sb.clear()
            num_of_bands = lyr_nm.bandCount()
            sb.addItems([' '] + [ str(i+1) for i in range(num_of_bands)])
        except:
            pass
        
    def create_map_layer_drpdwn(self, dlg, width, loc, type, sb, label):
        wcb = QgsMapLayerComboBox(dlg)
        wcb.setFixedWidth(width)
        wcb.move(*loc)
        wcb.setFilters( type )
        wcb.setAllowEmptyLayer(True)
        wcb.setCurrentIndex(0)
        wcb.layerChanged.connect(lambda: self.load_fields(wcb, sb))
        Label = QLabel(dlg)
        Label.setText(label)
        Label.move(loc[0]-50, loc[1])
        return wcb
    
    def create_select_band_drpdwn(self, dlg, width, loc):
        sb = QComboBox(dlg)
        sb.setFixedWidth(width)
        sb.move(*loc)
        return sb

    def run(self):

        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = FeatureSpaceDialog()
        
        
        self.sb = self.create_select_band_drpdwn(self.dlg, 50, [450,27])
        self.sb2 = self.create_select_band_drpdwn(self.dlg, 50, [450,127])

        self.sb_red = self.create_select_band_drpdwn(self.dlg, 50, [950,27])
        self.sb_green = self.create_select_band_drpdwn(self.dlg, 50, [950,127])
        self.sb_blue = self.create_select_band_drpdwn(self.dlg, 50, [950,227])

        self.wcb = self.create_map_layer_drpdwn(self.dlg, 150, [220,40], QgsMapLayerProxyModel.RasterLayer, self.sb, 'X Axis')
        self.wcb2 = self.create_map_layer_drpdwn(self.dlg, 150, [220,80], QgsMapLayerProxyModel.RasterLayer, self.sb2, 'Y Axis')

        self.wcb_red = self.create_map_layer_drpdwn(self.dlg, 150, [720,27], QgsMapLayerProxyModel.RasterLayer, self.sb_red, 'Red')
        self.wcb_green = self.create_map_layer_drpdwn(self.dlg, 150, [720,127], QgsMapLayerProxyModel.RasterLayer, self.sb_green, "Green")
        self.wcb_blue = self.create_map_layer_drpdwn(self.dlg, 150, [720,227], QgsMapLayerProxyModel.RasterLayer, self.sb_blue, 'Blue')


        program = GuiProgram(self.dlg,
                            self.wcb, self.wcb2, self.wcb_red, self.wcb_green, self.wcb_blue,
                            self.sb, self.sb2, self.sb_red, self.sb_green, self.sb_blue)
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

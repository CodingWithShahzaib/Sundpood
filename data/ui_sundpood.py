# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'sundpood.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets

from data.path_utils import resource_path


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 800)
        MainWindow.setMinimumSize(QtCore.QSize(1000, 700))
        # Removed maximum size constraint to allow resizing/fullscreen
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(resource_path("icon.ico")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)
        # Stylesheet will be applied via theme system
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        
        # Title bar - responsive layout
        self.background = QtWidgets.QWidget(self.centralwidget)
        self.background.setGeometry(QtCore.QRect(0, 0, 1200, 45))
        self.background.setObjectName("background")
        
        self.title_label = QtWidgets.QLabel(self.background)
        self.title_label.setGeometry(QtCore.QRect(20, 0, 300, 45))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(16)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setObjectName("title_label")
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        
        # Window controls - will be repositioned dynamically to top right
        self.exit_button = QtWidgets.QPushButton(self.background)
        self.exit_button.setGeometry(QtCore.QRect(1155, 7, 35, 30))
        self.exit_button.setObjectName("exit_button")
        self.exit_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.min_button = QtWidgets.QPushButton(self.background)
        self.min_button.setGeometry(QtCore.QRect(1115, 7, 35, 30))
        self.min_button.setObjectName("min_button")
        self.min_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        self.pref_button = QtWidgets.QPushButton(self.background)
        self.pref_button.setGeometry(QtCore.QRect(1020, 7, 90, 30))
        self.pref_button.setObjectName("pref_button")
        self.pref_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        # Status label
        self.select_label = QtWidgets.QLabel(self.centralwidget)
        self.select_label.setGeometry(QtCore.QRect(20, 55, 1160, 40))
        self.select_label.setText("")
        self.select_label.setAlignment(QtCore.Qt.AlignCenter)
        self.select_label.setObjectName("select_label")
        
        # Left panel - Controls
        self.control_panel = QtWidgets.QWidget(self.centralwidget)
        self.control_panel.setGeometry(QtCore.QRect(20, 105, 320, 680))
        self.control_panel.setObjectName("control_panel")
        
        # Play button
        self.play_button = QtWidgets.QPushButton(self.control_panel)
        self.play_button.setGeometry(QtCore.QRect(0, 0, 320, 55))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.play_button.setFont(font)
        self.play_button.setObjectName("play_button")
        self.play_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        # Stop button
        self.stop_button = QtWidgets.QPushButton(self.control_panel)
        self.stop_button.setGeometry(QtCore.QRect(0, 65, 320, 55))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.stop_button.setFont(font)
        self.stop_button.setObjectName("stop_button")
        self.stop_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        # Stop on same hotkey checkbox
        self.stop_same_hotkey_checkbox = QtWidgets.QCheckBox(self.control_panel)
        self.stop_same_hotkey_checkbox.setGeometry(QtCore.QRect(5, 125, 310, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.stop_same_hotkey_checkbox.setFont(font)
        self.stop_same_hotkey_checkbox.setObjectName("stop_same_hotkey_checkbox")
        self.stop_same_hotkey_checkbox.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        # Set hotkey button
        self.hkset = QtWidgets.QPushButton(self.control_panel)
        self.hkset.setGeometry(QtCore.QRect(0, 160, 320, 55))
        font = QtGui.QFont()
        font.setPointSize(13)
        self.hkset.setFont(font)
        self.hkset.setObjectName("hkset")
        self.hkset.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        # Volume label
        self.volume_label = QtWidgets.QLabel(self.control_panel)
        self.volume_label.setGeometry(QtCore.QRect(0, 230, 320, 28))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.volume_label.setFont(font)
        self.volume_label.setAlignment(QtCore.Qt.AlignCenter)
        self.volume_label.setObjectName("volume_label")
        
        # Volume slider
        self.volume_slider = QtWidgets.QSlider(self.control_panel)
        self.volume_slider.setGeometry(QtCore.QRect(15, 265, 290, 22))
        self.volume_slider.setMaximum(100)
        self.volume_slider.setProperty("value", 70)
        self.volume_slider.setOrientation(QtCore.Qt.Horizontal)
        self.volume_slider.setObjectName("volume_slider")
        
        # Volume percentage label
        self.volume_percent_label = QtWidgets.QLabel(self.control_panel)
        self.volume_percent_label.setGeometry(QtCore.QRect(0, 292, 320, 22))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.volume_percent_label.setFont(font)
        self.volume_percent_label.setAlignment(QtCore.Qt.AlignCenter)
        self.volume_percent_label.setObjectName("volume_percent_label")
        
        # Categories label
        self.cat_label = QtWidgets.QLabel(self.control_panel)
        self.cat_label.setGeometry(QtCore.QRect(0, 325, 320, 32))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.cat_label.setFont(font)
        self.cat_label.setAlignment(QtCore.Qt.AlignCenter)
        self.cat_label.setObjectName("cat_label")
        
        # Categories list
        self.catList = QtWidgets.QListWidget(self.control_panel)
        self.catList.setGeometry(QtCore.QRect(0, 360, 320, 320))
        self.catList.setObjectName("catList")
        
        # Right panel - Sound list
        self.sound_panel = QtWidgets.QWidget(self.centralwidget)
        self.sound_panel.setGeometry(QtCore.QRect(355, 105, 825, 680))
        self.sound_panel.setObjectName("sound_panel")
        
        # Sound list label
        self.sound_list_label = QtWidgets.QLabel(self.sound_panel)
        self.sound_list_label.setGeometry(QtCore.QRect(0, 0, 825, 35))
        font = QtGui.QFont()
        font.setPointSize(13)
        font.setBold(True)
        self.sound_list_label.setFont(font)
        self.sound_list_label.setAlignment(QtCore.Qt.AlignCenter)
        self.sound_list_label.setObjectName("sound_list_label")
        
        # Sound list
        self.soundList = QtWidgets.QListWidget(self.sound_panel)
        self.soundList.setGeometry(QtCore.QRect(0, 40, 825, 640))
        self.soundList.setObjectName("soundList")
        # Set grid view mode with better spacing
        self.soundList.setViewMode(QtWidgets.QListWidget.IconMode)
        self.soundList.setIconSize(QtCore.QSize(200, 160))
        self.soundList.setGridSize(QtCore.QSize(220, 180))
        self.soundList.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.soundList.setMovement(QtWidgets.QListWidget.Static)
        self.soundList.setSpacing(15)
        self.soundList.setWordWrap(True)
        self.soundList.setUniformItemSizes(True)
        
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "SundPood - Modern Soundpad"))
        self.title_label.setText(_translate("MainWindow", "SundPood"))
        self.min_button.setText(_translate("MainWindow", "−"))
        self.exit_button.setText(_translate("MainWindow", "✕"))
        self.pref_button.setText(_translate("MainWindow", "⚙"))
        self.stop_button.setText(_translate("MainWindow", "■ STOP"))
        self.stop_same_hotkey_checkbox.setText(_translate("MainWindow", "⏹ Stop on same hotkey"))
        self.hkset.setText(_translate("MainWindow", "⌨ SET HOTKEY"))
        self.cat_label.setText(_translate("MainWindow", "CATEGORIES"))
        self.play_button.setText(_translate("MainWindow", "▶ PLAY"))
        self.volume_label.setText(_translate("MainWindow", "VOLUME"))
        self.volume_percent_label.setText(_translate("MainWindow", "70%"))
        self.sound_list_label.setText(_translate("MainWindow", "SOUNDS"))

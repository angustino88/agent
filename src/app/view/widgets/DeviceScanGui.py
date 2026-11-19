# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'DeviceScanGui.ui'
##
## Created by: Qt User Interface Compiler version 6.11.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QGroupBox,
    QHeaderView, QPlainTextEdit, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QWidget)
from qt_embedded import resources

class Ui_DeviceScanDialog(object):
    def setupUi(self, DeviceScanDialog):
        if not DeviceScanDialog.objectName():
            DeviceScanDialog.setObjectName(u"DeviceScanDialog")
        DeviceScanDialog.resize(789, 564)
        DeviceScanDialog.setMinimumSize(QSize(789, 564))
        DeviceScanDialog.setMaximumSize(QSize(789, 564))
        icon = QIcon()
        icon.addFile(u":/icons/search.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        DeviceScanDialog.setWindowIcon(icon)
        self.groupBox = QGroupBox(DeviceScanDialog)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(0, 10, 441, 541))
        self.device_table = QTableWidget(self.groupBox)
        if (self.device_table.columnCount() < 3):
            self.device_table.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.device_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.device_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.device_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        if (self.device_table.rowCount() < 16):
            self.device_table.setRowCount(16)
        self.device_table.setObjectName(u"device_table")
        self.device_table.setGeometry(QRect(10, 60, 421, 471))
        self.device_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.device_table.setShowGrid(False)
        self.device_table.setRowCount(16)
        self.refresh_btn = QPushButton(self.groupBox)
        self.refresh_btn.setObjectName(u"refresh_btn")
        self.refresh_btn.setGeometry(QRect(10, 20, 205, 31))
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.refresh_btn.setFont(font)
        self.refresh_btn.setCheckable(True)
        self.push_btn = QPushButton(self.groupBox)
        self.push_btn.setObjectName(u"push_btn")
        self.push_btn.setEnabled(False)
        self.push_btn.setGeometry(QRect(225, 20, 205, 31))
        self.push_btn.setFont(font)
        self.push_btn.setCheckable(True)
        self.groupBox_2 = QGroupBox(DeviceScanDialog)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setGeometry(QRect(449, 9, 331, 541))
        self.console_output = QPlainTextEdit(self.groupBox_2)
        self.console_output.setObjectName(u"console_output")
        self.console_output.setGeometry(QRect(10, 60, 311, 471))
        self.console_output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)
        self.console_output.setBackgroundVisible(False)
        self.scan_btn = QPushButton(self.groupBox_2)
        self.scan_btn.setObjectName(u"scan_btn")
        self.scan_btn.setGeometry(QRect(10, 20, 311, 31))
        self.scan_btn.setFont(font)
        self.scan_btn.setCheckable(True)

        self.retranslateUi(DeviceScanDialog)

        QMetaObject.connectSlotsByName(DeviceScanDialog)
    # setupUi

    def retranslateUi(self, DeviceScanDialog):
        DeviceScanDialog.setWindowTitle(QCoreApplication.translate("DeviceScanDialog", u"Device Scan", None))
        self.groupBox.setTitle(QCoreApplication.translate("DeviceScanDialog", u"Expected devices", None))
        ___qtablewidgetitem = self.device_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("DeviceScanDialog", u"Status", None))
        ___qtablewidgetitem1 = self.device_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("DeviceScanDialog", u"Name", None))
        ___qtablewidgetitem2 = self.device_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("DeviceScanDialog", u"PnP ID", None))
        self.refresh_btn.setText(QCoreApplication.translate("DeviceScanDialog", u"Refresh", None))
        self.push_btn.setText(QCoreApplication.translate("DeviceScanDialog", u"Push", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("DeviceScanDialog", u"Device Scan", None))
        self.scan_btn.setText(QCoreApplication.translate("DeviceScanDialog", u"Scan", None))
    # retranslateUi


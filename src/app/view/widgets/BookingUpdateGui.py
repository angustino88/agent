# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'BookingUpdateGui.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDateTimeEdit, QDialog,
    QGroupBox, QLabel, QPushButton, QSizePolicy,
    QWidget)
from qt_embedded import resources

class Ui_BookingUpdateDialog(object):
    def setupUi(self, BookingUpdateDialog):
        if not BookingUpdateDialog.objectName():
            BookingUpdateDialog.setObjectName(u"BookingUpdateDialog")
        BookingUpdateDialog.resize(327, 213)
        icon = QIcon()
        icon.addFile(u":/icons/schedule.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        BookingUpdateDialog.setWindowIcon(icon)
        self.groupBox = QGroupBox(BookingUpdateDialog)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(10, 10, 311, 151))
        self.to_datetime_edit = QDateTimeEdit(self.groupBox)
        self.to_datetime_edit.setObjectName(u"to_datetime_edit")
        self.to_datetime_edit.setGeometry(QRect(110, 70, 194, 24))
        self.to_datetime_edit.setFrame(True)
        self.to_datetime_edit.setCalendarPopup(True)
        self.label_6 = QLabel(self.groupBox)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(10, 35, 101, 16))
        self.label_7 = QLabel(self.groupBox)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setGeometry(QRect(10, 75, 101, 16))
        self.from_datetime_edit = QDateTimeEdit(self.groupBox)
        self.from_datetime_edit.setObjectName(u"from_datetime_edit")
        self.from_datetime_edit.setEnabled(False)
        self.from_datetime_edit.setGeometry(QRect(110, 30, 194, 24))
        self.from_datetime_edit.setCalendarPopup(True)
        self.booking_status_combo = QComboBox(self.groupBox)
        self.booking_status_combo.setObjectName(u"booking_status_combo")
        self.booking_status_combo.setGeometry(QRect(110, 110, 111, 24))
        self.label_8 = QLabel(self.groupBox)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setGeometry(QRect(10, 112, 101, 16))
        self.update_btn = QPushButton(BookingUpdateDialog)
        self.update_btn.setObjectName(u"update_btn")
        self.update_btn.setGeometry(QRect(170, 170, 71, 31))
        font = QFont()
        font.setBold(True)
        self.update_btn.setFont(font)
        self.update_btn.setStyleSheet(u"")
        self.cancel_btn = QPushButton(BookingUpdateDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        self.cancel_btn.setGeometry(QRect(250, 170, 71, 31))
        self.cancel_btn.setFont(font)
        self.cancel_btn.setStyleSheet(u"")

        self.retranslateUi(BookingUpdateDialog)

        self.update_btn.setDefault(True)


        QMetaObject.connectSlotsByName(BookingUpdateDialog)
    # setupUi

    def retranslateUi(self, BookingUpdateDialog):
        BookingUpdateDialog.setWindowTitle(QCoreApplication.translate("BookingUpdateDialog", u"Booking Update", None))
        self.groupBox.setTitle(QCoreApplication.translate("BookingUpdateDialog", u"Booking Info", None))
        self.to_datetime_edit.setDisplayFormat(QCoreApplication.translate("BookingUpdateDialog", u"M/d/yyyy HH:mm", None))
        self.label_6.setText(QCoreApplication.translate("BookingUpdateDialog", u"From datetime:", None))
        self.label_7.setText(QCoreApplication.translate("BookingUpdateDialog", u"To datetime:", None))
        self.from_datetime_edit.setDisplayFormat(QCoreApplication.translate("BookingUpdateDialog", u"M/d/yyyy HH:mm", None))
        self.label_8.setText(QCoreApplication.translate("BookingUpdateDialog", u"Status", None))
        self.update_btn.setText(QCoreApplication.translate("BookingUpdateDialog", u"Update", None))
        self.cancel_btn.setText(QCoreApplication.translate("BookingUpdateDialog", u"Cancel", None))
    # retranslateUi


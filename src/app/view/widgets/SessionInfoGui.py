# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SessionInfoGui.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGroupBox,
    QLCDNumber, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QWidget)
from qt_embedded import resources

class Ui_SessionInfoDialog(object):
    def setupUi(self, SessionInfoDialog):
        if not SessionInfoDialog.objectName():
            SessionInfoDialog.setObjectName(u"SessionInfoDialog")
        SessionInfoDialog.resize(363, 350)
        SessionInfoDialog.setMinimumSize(QSize(363, 350))
        SessionInfoDialog.setMaximumSize(QSize(363, 350))
        icon = QIcon()
        icon.addFile(u":/icons/schedule.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        SessionInfoDialog.setWindowIcon(icon)
        self.groupBox = QGroupBox(SessionInfoDialog)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(10, 10, 342, 271))
        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 30, 101, 16))
        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(10, 60, 101, 16))
        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(10, 90, 101, 16))
        self.label_4 = QLabel(self.groupBox)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(10, 120, 101, 16))
        self.label_5 = QLabel(self.groupBox)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(10, 150, 101, 16))
        self.label_6 = QLabel(self.groupBox)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(10, 180, 101, 16))
        self.hour_lcdNumber = QLCDNumber(self.groupBox)
        self.hour_lcdNumber.setObjectName(u"hour_lcdNumber")
        self.hour_lcdNumber.setGeometry(QRect(120, 210, 100, 50))
        self.hour_lcdNumber.setFrameShape(QFrame.Shape.Box)
        self.hour_lcdNumber.setSmallDecimalPoint(False)
        self.hour_lcdNumber.setDigitCount(3)
        self.hour_lcdNumber.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.minute_lcdNumber = QLCDNumber(self.groupBox)
        self.minute_lcdNumber.setObjectName(u"minute_lcdNumber")
        self.minute_lcdNumber.setGeometry(QRect(230, 210, 100, 50))
        self.minute_lcdNumber.setFrameShape(QFrame.Shape.Box)
        self.minute_lcdNumber.setSmallDecimalPoint(False)
        self.minute_lcdNumber.setDigitCount(2)
        self.minute_lcdNumber.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.label_7 = QLabel(self.groupBox)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setGeometry(QRect(10, 210, 101, 16))
        self.booking_number_edit = QLineEdit(self.groupBox)
        self.booking_number_edit.setObjectName(u"booking_number_edit")
        self.booking_number_edit.setGeometry(QRect(120, 28, 211, 22))
        self.booking_number_edit.setReadOnly(True)
        self.remote_user_edit = QLineEdit(self.groupBox)
        self.remote_user_edit.setObjectName(u"remote_user_edit")
        self.remote_user_edit.setGeometry(QRect(120, 58, 211, 22))
        self.remote_user_edit.setReadOnly(True)
        self.remote_ip_edit = QLineEdit(self.groupBox)
        self.remote_ip_edit.setObjectName(u"remote_ip_edit")
        self.remote_ip_edit.setGeometry(QRect(120, 88, 211, 22))
        self.remote_ip_edit.setReadOnly(True)
        self.remote_computer_edit = QLineEdit(self.groupBox)
        self.remote_computer_edit.setObjectName(u"remote_computer_edit")
        self.remote_computer_edit.setGeometry(QRect(120, 118, 211, 22))
        self.remote_computer_edit.setReadOnly(True)
        self.from_datetime_edit = QLineEdit(self.groupBox)
        self.from_datetime_edit.setObjectName(u"from_datetime_edit")
        self.from_datetime_edit.setGeometry(QRect(120, 148, 211, 22))
        self.from_datetime_edit.setReadOnly(True)
        self.to_datetime_edit = QLineEdit(self.groupBox)
        self.to_datetime_edit.setObjectName(u"to_datetime_edit")
        self.to_datetime_edit.setGeometry(QRect(120, 178, 211, 22))
        self.to_datetime_edit.setReadOnly(True)
        self.update_booking_btn = QPushButton(SessionInfoDialog)
        self.update_booking_btn.setObjectName(u"update_booking_btn")
        self.update_booking_btn.setGeometry(QRect(240, 290, 112, 41))
        font = QFont()
        font.setBold(True)
        self.update_booking_btn.setFont(font)
        self.update_booking_btn.setStyleSheet(u"")
        self.update_booking_btn.setAutoDefault(True)
        self.update_booking_btn.setFlat(False)
        self.end_booking_btn = QPushButton(SessionInfoDialog)
        self.end_booking_btn.setObjectName(u"end_booking_btn")
        self.end_booking_btn.setGeometry(QRect(10, 290, 112, 41))
        self.end_booking_btn.setFont(font)
        self.end_booking_btn.setStyleSheet(u"")
        self.end_booking_btn.setIconSize(QSize(18, 18))
        self.end_booking_btn.setAutoDefault(False)
        self.refresh_booking_btn = QPushButton(SessionInfoDialog)
        self.refresh_booking_btn.setObjectName(u"refresh_booking_btn")
        self.refresh_booking_btn.setGeometry(QRect(126, 290, 112, 41))
        self.refresh_booking_btn.setFont(font)
        self.refresh_booking_btn.setStyleSheet(u"")
        self.refresh_booking_btn.setAutoDefault(True)
        self.refresh_booking_btn.setFlat(False)

        self.retranslateUi(SessionInfoDialog)

        self.update_booking_btn.setDefault(False)
        self.end_booking_btn.setDefault(True)
        self.refresh_booking_btn.setDefault(False)


        QMetaObject.connectSlotsByName(SessionInfoDialog)
    # setupUi

    def retranslateUi(self, SessionInfoDialog):
        SessionInfoDialog.setWindowTitle(QCoreApplication.translate("SessionInfoDialog", u"Session Info", None))
        self.groupBox.setTitle(QCoreApplication.translate("SessionInfoDialog", u"Session Info", None))
        self.label.setText(QCoreApplication.translate("SessionInfoDialog", u"Booking number:", None))
        self.label_2.setText(QCoreApplication.translate("SessionInfoDialog", u"Remote user:", None))
        self.label_3.setText(QCoreApplication.translate("SessionInfoDialog", u"Remote IP:", None))
        self.label_4.setText(QCoreApplication.translate("SessionInfoDialog", u"Remote computer:", None))
        self.label_5.setText(QCoreApplication.translate("SessionInfoDialog", u"From datetime:", None))
        self.label_6.setText(QCoreApplication.translate("SessionInfoDialog", u"To datetime:", None))
        self.label_7.setText(QCoreApplication.translate("SessionInfoDialog", u"Time left:", None))
        self.booking_number_edit.setText("")
        self.remote_user_edit.setText("")
        self.remote_ip_edit.setText("")
        self.remote_computer_edit.setText("")
        self.from_datetime_edit.setText("")
        self.to_datetime_edit.setText("")
        self.update_booking_btn.setText(QCoreApplication.translate("SessionInfoDialog", u"Update Booking", None))
        self.end_booking_btn.setText(QCoreApplication.translate("SessionInfoDialog", u"End Booking", None))
        self.refresh_booking_btn.setText(QCoreApplication.translate("SessionInfoDialog", u"Refresh Booking", None))
    # retranslateUi


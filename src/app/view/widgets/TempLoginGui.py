# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'TempLoginGui.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget)
from qt_embedded import resources

class Ui_TempLoginDialog(object):
    def setupUi(self, TempLoginDialog):
        if not TempLoginDialog.objectName():
            TempLoginDialog.setObjectName(u"TempLoginDialog")
        TempLoginDialog.resize(449, 216)
        icon = QIcon()
        icon.addFile(u":/icons/mango.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        TempLoginDialog.setWindowIcon(icon)
        self.otp_code_edit = QLineEdit(TempLoginDialog)
        self.otp_code_edit.setObjectName(u"otp_code_edit")
        self.otp_code_edit.setGeometry(QRect(120, 100, 201, 31))
        font = QFont()
        font.setFamilies([u"MS Shell Dlg 2"])
        font.setPointSize(10)
        font.setBold(True)
        font.setItalic(False)
        self.otp_code_edit.setFont(font)
        self.otp_code_edit.setStyleSheet(u"")
        self.otp_code_edit.setInputMethodHints(Qt.InputMethodHint.ImhNone)
        self.otp_code_edit.setMaxLength(6)
        self.otp_code_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_1 = QLabel(TempLoginDialog)
        self.label_1.setObjectName(u"label_1")
        self.label_1.setGeometry(QRect(40, 10, 361, 41))
        font1 = QFont()
        font1.setFamilies([u"MS Shell Dlg 2"])
        font1.setPointSize(18)
        self.label_1.setFont(font1)
        self.label_1.setStyleSheet(u"")
        self.label_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_2 = QLabel(TempLoginDialog)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(10, 50, 421, 41))
        self.label_2.setStyleSheet(u"")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verify_btn = QPushButton(TempLoginDialog)
        self.verify_btn.setObjectName(u"verify_btn")
        self.verify_btn.setGeometry(QRect(120, 140, 201, 31))
        font2 = QFont()
        font2.setBold(True)
        self.verify_btn.setFont(font2)
        self.verify_btn.setStyleSheet(u"")
        self.label_3 = QLabel(TempLoginDialog)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(140, 180, 121, 20))
        self.label_3.setStyleSheet(u"")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resend_label = QLabel(TempLoginDialog)
        self.resend_label.setObjectName(u"resend_label")
        self.resend_label.setGeometry(QRect(250, 180, 51, 20))
        self.resend_label.setStyleSheet(u"")
        self.resend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.retranslateUi(TempLoginDialog)

        self.verify_btn.setDefault(True)


        QMetaObject.connectSlotsByName(TempLoginDialog)
    # setupUi

    def retranslateUi(self, TempLoginDialog):
        TempLoginDialog.setWindowTitle(QCoreApplication.translate("TempLoginDialog", u"Temp Login", None))
        self.otp_code_edit.setText("")
        self.otp_code_edit.setPlaceholderText(QCoreApplication.translate("TempLoginDialog", u"OTP code", None))
        self.label_1.setText(QCoreApplication.translate("TempLoginDialog", u"Temporary Login Verificaiton", None))
        self.label_2.setText(QCoreApplication.translate("TempLoginDialog", u"Enter the 6-digit verification that was sent to \n"
" your email and MS Teams", None))
        self.verify_btn.setText(QCoreApplication.translate("TempLoginDialog", u"Verify", None))
        self.label_3.setText(QCoreApplication.translate("TempLoginDialog", u"Didn't receive code?", None))
        self.resend_label.setText(QCoreApplication.translate("TempLoginDialog", u"Resend", None))
    # retranslateUi


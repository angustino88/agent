# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ServerConfigGui.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QGroupBox, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QWidget)
from qt_embedded import resources

class Ui_ServerConfigDialog(object):
    def setupUi(self, ServerConfigDialog):
        if not ServerConfigDialog.objectName():
            ServerConfigDialog.setObjectName(u"ServerConfigDialog")
        ServerConfigDialog.resize(370, 400)
        ServerConfigDialog.setMinimumSize(QSize(370, 400))
        ServerConfigDialog.setMaximumSize(QSize(370, 400))
        icon = QIcon()
        icon.addFile(u":/icons/server-security.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        ServerConfigDialog.setWindowIcon(icon)
        self.prod_server_group = QGroupBox(ServerConfigDialog)
        self.prod_server_group.setObjectName(u"prod_server_group")
        self.prod_server_group.setEnabled(True)
        self.prod_server_group.setGeometry(QRect(10, 10, 351, 131))
        self.prod_frontend_edit = QLineEdit(self.prod_server_group)
        self.prod_frontend_edit.setObjectName(u"prod_frontend_edit")
        self.prod_frontend_edit.setGeometry(QRect(80, 28, 261, 22))
        self.prod_frontend_edit.setStyleSheet(u"font: 8pt \"MS Shell Dlg 2\";")
        self.prod_frontend_edit.setReadOnly(True)
        self.label_8 = QLabel(self.prod_server_group)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setGeometry(QRect(10, 30, 61, 16))
        self.label_9 = QLabel(self.prod_server_group)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setGeometry(QRect(10, 62, 61, 16))
        self.prod_backend_edit = QLineEdit(self.prod_server_group)
        self.prod_backend_edit.setObjectName(u"prod_backend_edit")
        self.prod_backend_edit.setGeometry(QRect(80, 60, 261, 22))
        self.prod_backend_edit.setStyleSheet(u"font: 8pt \"MS Shell Dlg 2\";")
        self.prod_backend_edit.setReadOnly(True)
        self.prod_apikey_edit = QLineEdit(self.prod_server_group)
        self.prod_apikey_edit.setObjectName(u"prod_apikey_edit")
        self.prod_apikey_edit.setGeometry(QRect(80, 92, 261, 22))
        self.prod_apikey_edit.setStyleSheet(u"font: 8pt \"MS Shell Dlg 2\";")
        self.prod_apikey_edit.setReadOnly(True)
        self.label_12 = QLabel(self.prod_server_group)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setGeometry(QRect(10, 96, 55, 16))
        self.service_gateway_group = QGroupBox(ServerConfigDialog)
        self.service_gateway_group.setObjectName(u"service_gateway_group")
        self.service_gateway_group.setGeometry(QRect(10, 157, 351, 95))
        self.service_gateway_backend_edit = QLineEdit(self.service_gateway_group)
        self.service_gateway_backend_edit.setObjectName(u"service_gateway_backend_edit")
        self.service_gateway_backend_edit.setGeometry(QRect(80, 28, 261, 22))
        self.service_gateway_backend_edit.setStyleSheet(u"font: 8pt \"MS Shell Dlg 2\";")
        self.service_gateway_backend_edit.setReadOnly(True)
        self.label_10 = QLabel(self.service_gateway_group)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setGeometry(QRect(10, 30, 61, 16))
        self.label_11 = QLabel(self.service_gateway_group)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setGeometry(QRect(10, 60, 61, 16))
        self.service_gateway_token_edit = QLineEdit(self.service_gateway_group)
        self.service_gateway_token_edit.setObjectName(u"service_gateway_token_edit")
        self.service_gateway_token_edit.setGeometry(QRect(80, 58, 261, 22))
        self.service_gateway_token_edit.setStyleSheet(u"font: 8pt \"MS Shell Dlg 2\";")
        self.service_gateway_token_edit.setReadOnly(True)
        self.sync_btn = QPushButton(ServerConfigDialog)
        self.sync_btn.setObjectName(u"sync_btn")
        self.sync_btn.setGeometry(QRect(170, 350, 90, 31))
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.sync_btn.setFont(font)
        self.sync_btn.setCheckable(True)
        self.otp_master_code_group = QGroupBox(ServerConfigDialog)
        self.otp_master_code_group.setObjectName(u"otp_master_code_group")
        self.otp_master_code_group.setGeometry(QRect(10, 270, 171, 71))
        self.otp_master_code_edit = QLineEdit(self.otp_master_code_group)
        self.otp_master_code_edit.setObjectName(u"otp_master_code_edit")
        self.otp_master_code_edit.setGeometry(QRect(10, 30, 151, 22))
        self.otp_master_code_edit.setStyleSheet(u"font: 8pt \"MS Shell Dlg 2\";")
        self.otp_master_code_edit.setReadOnly(True)
        self.cancel_btn = QPushButton(ServerConfigDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        self.cancel_btn.setGeometry(QRect(270, 350, 90, 31))
        self.cancel_btn.setFont(font)
        self.cancel_btn.setCheckable(True)
        self.safe_mode_group = QGroupBox(ServerConfigDialog)
        self.safe_mode_group.setObjectName(u"safe_mode_group")
        self.safe_mode_group.setGeometry(QRect(190, 270, 171, 71))
        self.safe_mode_edit = QLineEdit(self.safe_mode_group)
        self.safe_mode_edit.setObjectName(u"safe_mode_edit")
        self.safe_mode_edit.setGeometry(QRect(10, 30, 151, 22))
        self.safe_mode_edit.setStyleSheet(u"font: 8pt \"MS Shell Dlg 2\";")
        self.safe_mode_edit.setReadOnly(True)

        self.retranslateUi(ServerConfigDialog)

        QMetaObject.connectSlotsByName(ServerConfigDialog)
    # setupUi

    def retranslateUi(self, ServerConfigDialog):
        ServerConfigDialog.setWindowTitle(QCoreApplication.translate("ServerConfigDialog", u"Server Configuration", None))
        self.prod_server_group.setTitle(QCoreApplication.translate("ServerConfigDialog", u"Production Server", None))
        self.prod_frontend_edit.setText("")
        self.prod_frontend_edit.setPlaceholderText("")
        self.label_8.setText(QCoreApplication.translate("ServerConfigDialog", u"Front-End:", None))
        self.label_9.setText(QCoreApplication.translate("ServerConfigDialog", u"Back-End:", None))
        self.prod_backend_edit.setText("")
        self.prod_backend_edit.setPlaceholderText("")
        self.prod_apikey_edit.setText("")
        self.prod_apikey_edit.setPlaceholderText("")
        self.label_12.setText(QCoreApplication.translate("ServerConfigDialog", u"API Key:", None))
        self.service_gateway_group.setTitle(QCoreApplication.translate("ServerConfigDialog", u"Service Gateway", None))
        self.service_gateway_backend_edit.setText("")
        self.service_gateway_backend_edit.setPlaceholderText("")
        self.label_10.setText(QCoreApplication.translate("ServerConfigDialog", u"Back-End:", None))
        self.label_11.setText(QCoreApplication.translate("ServerConfigDialog", u"Token:", None))
        self.service_gateway_token_edit.setText("")
        self.service_gateway_token_edit.setPlaceholderText("")
        self.sync_btn.setText(QCoreApplication.translate("ServerConfigDialog", u"Sync", None))
        self.otp_master_code_group.setTitle(QCoreApplication.translate("ServerConfigDialog", u"OTP Master Code", None))
        self.otp_master_code_edit.setText("")
        self.otp_master_code_edit.setPlaceholderText("")
        self.cancel_btn.setText(QCoreApplication.translate("ServerConfigDialog", u"Cancel", None))
        self.safe_mode_group.setTitle(QCoreApplication.translate("ServerConfigDialog", u"Safe Mode", None))
        self.safe_mode_edit.setText("")
        self.safe_mode_edit.setPlaceholderText("")
    # retranslateUi


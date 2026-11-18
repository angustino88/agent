# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'LoginGui.ui'
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

class Ui_LoginDialog(object):
    def setupUi(self, LoginDialog):
        if not LoginDialog.objectName():
            LoginDialog.setObjectName(u"LoginDialog")
        LoginDialog.resize(593, 399)
        LoginDialog.setMinimumSize(QSize(593, 399))
        LoginDialog.setMaximumSize(QSize(65535, 65535))
        self.widget = QWidget(LoginDialog)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(20, 20, 561, 331))
        self.cancel_btn = QPushButton(self.widget)
        self.cancel_btn.setObjectName(u"cancel_btn")
        self.cancel_btn.setGeometry(QRect(300, 240, 71, 31))
        font = QFont()
        font.setBold(True)
        self.cancel_btn.setFont(font)
        self.cancel_btn.setStyleSheet(u"")
        self.login_btn = QPushButton(self.widget)
        self.login_btn.setObjectName(u"login_btn")
        self.login_btn.setGeometry(QRect(220, 240, 71, 31))
        self.login_btn.setFont(font)
        self.login_btn.setStyleSheet(u"")
        self.login_groupBox = QGroupBox(self.widget)
        self.login_groupBox.setObjectName(u"login_groupBox")
        self.login_groupBox.setGeometry(QRect(120, 120, 341, 91))
        self.login_groupBox.setMinimumSize(QSize(0, 0))
        self.login_groupBox.setMaximumSize(QSize(16777215, 16777215))
        self.login_groupBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.login_groupBox.setCheckable(False)
        self.login_input_edit = QLineEdit(self.login_groupBox)
        self.login_input_edit.setObjectName(u"login_input_edit")
        self.login_input_edit.setGeometry(QRect(20, 30, 301, 41))
        font1 = QFont()
        font1.setFamilies([u"MS Shell Dlg 2"])
        font1.setPointSize(10)
        font1.setBold(True)
        font1.setItalic(False)
        self.login_input_edit.setFont(font1)
        self.login_input_edit.setStyleSheet(u"")
        self.border_left_btn = QPushButton(self.login_groupBox)
        self.border_left_btn.setObjectName(u"border_left_btn")
        self.border_left_btn.setGeometry(QRect(0, 6, 6, 122))
        self.border_left_btn.setStyleSheet(u"background-color: rgb(255, 85, 127);\n"
"QPushButton { border: none; }")
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(100, 10, 465, 121))
        font2 = QFont()
        font2.setPointSize(30)
        self.label.setFont(font2)
        self.icon_btn = QPushButton(self.widget)
        self.icon_btn.setObjectName(u"icon_btn")
        self.icon_btn.setGeometry(QRect(20, 45, 60, 60))
        self.icon_btn.setStyleSheet(u"QPushButton {\n"
"    border: none;\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: transparent;\n"
"}\n"
"")
        icon = QIcon()
        icon.addFile(u":/icons/mango.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.icon_btn.setIcon(icon)
        self.icon_btn.setIconSize(QSize(60, 60))

        self.retranslateUi(LoginDialog)

        self.login_btn.setDefault(True)


        QMetaObject.connectSlotsByName(LoginDialog)
    # setupUi

    def retranslateUi(self, LoginDialog):
        LoginDialog.setWindowTitle(QCoreApplication.translate("LoginDialog", u"Login", None))
        self.cancel_btn.setText(QCoreApplication.translate("LoginDialog", u"Cancel", None))
        self.login_btn.setText(QCoreApplication.translate("LoginDialog", u"Login", None))
        self.login_groupBox.setTitle("")
        self.login_input_edit.setText("")
        self.login_input_edit.setPlaceholderText(QCoreApplication.translate("LoginDialog", u"Booking code or username", None))
        self.border_left_btn.setText("")
        self.label.setText(QCoreApplication.translate("LoginDialog", u"Lab Management System", None))
        self.icon_btn.setText("")
    # retranslateUi


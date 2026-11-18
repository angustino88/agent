# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SettingsGui.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QGroupBox,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QWidget)
from qt_embedded import resources

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        if not SettingsDialog.objectName():
            SettingsDialog.setObjectName(u"SettingsDialog")
        SettingsDialog.resize(370, 220)
        SettingsDialog.setMinimumSize(QSize(370, 220))
        SettingsDialog.setMaximumSize(QSize(370, 220))
        icon = QIcon()
        icon.addFile(u":/icons/gear.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        SettingsDialog.setWindowIcon(icon)
        self.settings_group = QGroupBox(SettingsDialog)
        self.settings_group.setObjectName(u"settings_group")
        self.settings_group.setEnabled(True)
        self.settings_group.setGeometry(QRect(10, 10, 351, 141))
        self.label_1 = QLabel(self.settings_group)
        self.label_1.setObjectName(u"label_1")
        self.label_1.setGeometry(QRect(10, 30, 91, 18))
        self.label_2 = QLabel(self.settings_group)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(10, 68, 101, 18))
        self.sharing_dir_edit = QLineEdit(self.settings_group)
        self.sharing_dir_edit.setObjectName(u"sharing_dir_edit")
        self.sharing_dir_edit.setGeometry(QRect(120, 68, 231, 22))
        self.sharing_dir_edit.setStyleSheet(u"font: 8pt \"MS Shell Dlg 2\";")
        self.sharing_dir_edit.setReadOnly(False)
        self.debug_enabled_combo = QComboBox(self.settings_group)
        self.debug_enabled_combo.setObjectName(u"debug_enabled_combo")
        self.debug_enabled_combo.setGeometry(QRect(120, 30, 101, 24))
        self.label_3 = QLabel(self.settings_group)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(10, 104, 101, 18))
        self.user_quota_btn = QPushButton(self.settings_group)
        self.user_quota_btn.setObjectName(u"user_quota_btn")
        self.user_quota_btn.setGeometry(QRect(120, 102, 51, 22))
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.user_quota_btn.setFont(font)
        self.user_quota_btn.setCheckable(True)
        self.save_btn = QPushButton(SettingsDialog)
        self.save_btn.setObjectName(u"save_btn")
        self.save_btn.setGeometry(QRect(170, 170, 90, 31))
        font1 = QFont()
        font1.setPointSize(9)
        font1.setBold(True)
        self.save_btn.setFont(font1)
        self.save_btn.setCheckable(True)
        self.cancel_btn = QPushButton(SettingsDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        self.cancel_btn.setGeometry(QRect(270, 170, 90, 31))
        self.cancel_btn.setFont(font1)
        self.cancel_btn.setCheckable(True)

        self.retranslateUi(SettingsDialog)

        QMetaObject.connectSlotsByName(SettingsDialog)
    # setupUi

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(QCoreApplication.translate("SettingsDialog", u"Settings", None))
        self.settings_group.setTitle(QCoreApplication.translate("SettingsDialog", u"Settings", None))
        self.label_1.setText(QCoreApplication.translate("SettingsDialog", u"Debug enabled:", None))
        self.label_2.setText(QCoreApplication.translate("SettingsDialog", u"Sharing directory:", None))
        self.sharing_dir_edit.setText("")
        self.sharing_dir_edit.setPlaceholderText("")
        self.label_3.setText(QCoreApplication.translate("SettingsDialog", u"User quota config:", None))
        self.user_quota_btn.setText(QCoreApplication.translate("SettingsDialog", u"open", None))
        self.save_btn.setText(QCoreApplication.translate("SettingsDialog", u"Save", None))
        self.cancel_btn.setText(QCoreApplication.translate("SettingsDialog", u"Cancel", None))
    # retranslateUi


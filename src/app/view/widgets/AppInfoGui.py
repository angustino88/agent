# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AppInfoGui.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)
from qt_embedded import resources

class Ui_AppInfoDialog(object):
    def setupUi(self, AppInfoDialog):
        if not AppInfoDialog.objectName():
            AppInfoDialog.setObjectName(u"AppInfoDialog")
        AppInfoDialog.resize(480, 300)
        AppInfoDialog.setMinimumSize(QSize(480, 300))
        AppInfoDialog.setMaximumSize(QSize(480, 300))
        icon = QIcon()
        icon.addFile(u":/icons/mango.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        AppInfoDialog.setWindowIcon(icon)
        self.main_layout = QVBoxLayout(AppInfoDialog)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.header_hbox = QHBoxLayout()
        self.header_hbox.setSpacing(20)
        self.header_hbox.setObjectName(u"header_hbox")
        self.header_hbox.setContentsMargins(28, 20, 28, 20)
        self.icon_label = QLabel(AppInfoDialog)
        self.icon_label.setObjectName(u"icon_label")
        self.icon_label.setMinimumSize(QSize(68, 68))
        self.icon_label.setMaximumSize(QSize(68, 68))
        self.icon_label.setPixmap(QPixmap(u":/icons/mango.svg"))
        self.icon_label.setScaledContents(True)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.header_hbox.addWidget(self.icon_label)

        self.title_vbox = QVBoxLayout()
        self.title_vbox.setSpacing(6)
        self.title_vbox.setObjectName(u"title_vbox")
        self.name_label = QLabel(AppInfoDialog)
        self.name_label.setObjectName(u"name_label")

        self.title_vbox.addWidget(self.name_label)

        self.version_label = QLabel(AppInfoDialog)
        self.version_label.setObjectName(u"version_label")

        self.title_vbox.addWidget(self.version_label)


        self.header_hbox.addLayout(self.title_vbox)


        self.main_layout.addLayout(self.header_hbox)

        self.separator = QFrame(AppInfoDialog)
        self.separator.setObjectName(u"separator")
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.separator)

        self.body_vbox = QVBoxLayout()
        self.body_vbox.setSpacing(0)
        self.body_vbox.setObjectName(u"body_vbox")
        self.body_vbox.setContentsMargins(28, 20, 28, 12)
        self.app_section_title = QLabel(AppInfoDialog)
        self.app_section_title.setObjectName(u"app_section_title")

        self.body_vbox.addWidget(self.app_section_title)

        self.app_title_gap = QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.body_vbox.addItem(self.app_title_gap)

        self.body_info_label = QLabel(AppInfoDialog)
        self.body_info_label.setObjectName(u"body_info_label")
        self.body_info_label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.body_vbox.addWidget(self.body_info_label)


        self.main_layout.addLayout(self.body_vbox)

        self.body_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.body_spacer)

        self.bottom_separator = QFrame(AppInfoDialog)
        self.bottom_separator.setObjectName(u"bottom_separator")
        self.bottom_separator.setFrameShape(QFrame.Shape.HLine)
        self.bottom_separator.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.bottom_separator)

        self.btn_hbox = QHBoxLayout()
        self.btn_hbox.setSpacing(8)
        self.btn_hbox.setObjectName(u"btn_hbox")
        self.btn_hbox.setContentsMargins(16, 8, 16, 12)
        self.btn_spacer = QSpacerItem(30, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.btn_hbox.addItem(self.btn_spacer)

        self.close_btn = QPushButton(AppInfoDialog)
        self.close_btn.setObjectName(u"close_btn")

        self.btn_hbox.addWidget(self.close_btn)


        self.main_layout.addLayout(self.btn_hbox)


        self.retranslateUi(AppInfoDialog)

        self.close_btn.setDefault(True)


        QMetaObject.connectSlotsByName(AppInfoDialog)
    # setupUi

    def retranslateUi(self, AppInfoDialog):
        AppInfoDialog.setWindowTitle(QCoreApplication.translate("AppInfoDialog", u"About", None))
        self.name_label.setText(QCoreApplication.translate("AppInfoDialog", u"xxx", None))
        self.name_label.setProperty(u"role", QCoreApplication.translate("AppInfoDialog", u"dialog-title", None))
        self.version_label.setText(QCoreApplication.translate("AppInfoDialog", u"Version xxx", None))
        self.version_label.setProperty(u"role", QCoreApplication.translate("AppInfoDialog", u"hint", None))
        self.app_section_title.setText(QCoreApplication.translate("AppInfoDialog", u"APPLICATION", None))
        self.app_section_title.setProperty(u"role", QCoreApplication.translate("AppInfoDialog", u"section-title", None))
        self.body_info_label.setText("")
        self.close_btn.setText(QCoreApplication.translate("AppInfoDialog", u"Close", None))
    # retranslateUi


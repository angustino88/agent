# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AppUpdateGui.ui'
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
    QLabel, QPlainTextEdit, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)
from qt_embedded import resources

class Ui_AppUpdateDialog(object):
    def setupUi(self, AppUpdateDialog):
        if not AppUpdateDialog.objectName():
            AppUpdateDialog.setObjectName(u"AppUpdateDialog")
        AppUpdateDialog.resize(560, 440)
        AppUpdateDialog.setMinimumSize(QSize(560, 440))
        icon = QIcon()
        icon.addFile(u":/icons/update.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        AppUpdateDialog.setWindowIcon(icon)
        self.main_vbox = QVBoxLayout(AppUpdateDialog)
        self.main_vbox.setSpacing(10)
        self.main_vbox.setObjectName(u"main_vbox")
        self.main_vbox.setContentsMargins(16, 14, 16, 14)
        self.header_hbox = QHBoxLayout()
        self.header_hbox.setSpacing(12)
        self.header_hbox.setObjectName(u"header_hbox")
        self.icon_label = QLabel(AppUpdateDialog)
        self.icon_label.setObjectName(u"icon_label")
        self.icon_label.setMinimumSize(QSize(48, 48))
        self.icon_label.setMaximumSize(QSize(48, 48))
        self.icon_label.setPixmap(QPixmap(u":/icons/mango.svg"))
        self.icon_label.setScaledContents(True)

        self.header_hbox.addWidget(self.icon_label)

        self.title_vbox = QVBoxLayout()
        self.title_vbox.setSpacing(1)
        self.title_vbox.setObjectName(u"title_vbox")
        self.name_label = QLabel(AppUpdateDialog)
        self.name_label.setObjectName(u"name_label")

        self.title_vbox.addWidget(self.name_label)

        self.version_label = QLabel(AppUpdateDialog)
        self.version_label.setObjectName(u"version_label")

        self.title_vbox.addWidget(self.version_label)


        self.header_hbox.addLayout(self.title_vbox)

        self.header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.header_hbox.addItem(self.header_spacer)


        self.main_vbox.addLayout(self.header_hbox)

        self.console_output = QPlainTextEdit(AppUpdateDialog)
        self.console_output.setObjectName(u"console_output")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.console_output.sizePolicy().hasHeightForWidth())
        self.console_output.setSizePolicy(sizePolicy)
        self.console_output.setMinimumSize(QSize(0, 220))
        self.console_output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)
        self.console_output.setBackgroundVisible(False)

        self.main_vbox.addWidget(self.console_output)

        self.separator_bottom = QFrame(AppUpdateDialog)
        self.separator_bottom.setObjectName(u"separator_bottom")
        self.separator_bottom.setFrameShape(QFrame.Shape.HLine)
        self.separator_bottom.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_vbox.addWidget(self.separator_bottom)

        self.footer_hbox = QHBoxLayout()
        self.footer_hbox.setSpacing(8)
        self.footer_hbox.setObjectName(u"footer_hbox")
        self.footer_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.footer_hbox.addItem(self.footer_spacer)

        self.update_btn = QPushButton(AppUpdateDialog)
        self.update_btn.setObjectName(u"update_btn")
        self.update_btn.setMinimumSize(QSize(110, 34))

        self.footer_hbox.addWidget(self.update_btn)

        self.cancel_btn = QPushButton(AppUpdateDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")
        self.cancel_btn.setMinimumSize(QSize(110, 34))

        self.footer_hbox.addWidget(self.cancel_btn)


        self.main_vbox.addLayout(self.footer_hbox)


        self.retranslateUi(AppUpdateDialog)

        QMetaObject.connectSlotsByName(AppUpdateDialog)
    # setupUi

    def retranslateUi(self, AppUpdateDialog):
        AppUpdateDialog.setWindowTitle(QCoreApplication.translate("AppUpdateDialog", u"Software Update", None))
        self.icon_label.setText("")
        self.name_label.setText(QCoreApplication.translate("AppUpdateDialog", u"xxx", None))
        self.name_label.setProperty(u"role", QCoreApplication.translate("AppUpdateDialog", u"dialog-title", None))
        self.version_label.setText(QCoreApplication.translate("AppUpdateDialog", u"Version x.x.x", None))
        self.version_label.setProperty(u"role", QCoreApplication.translate("AppUpdateDialog", u"hint", None))
        self.console_output.setProperty(u"role", QCoreApplication.translate("AppUpdateDialog", u"console-update", None))
        self.update_btn.setText(QCoreApplication.translate("AppUpdateDialog", u"Update", None))
        self.update_btn.setProperty(u"variant", QCoreApplication.translate("AppUpdateDialog", u"primary", None))
        self.cancel_btn.setText(QCoreApplication.translate("AppUpdateDialog", u"Cancel", None))
        self.cancel_btn.setProperty(u"variant", QCoreApplication.translate("AppUpdateDialog", u"secondary", None))
    # retranslateUi


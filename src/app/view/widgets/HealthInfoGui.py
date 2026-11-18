# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'HealthInfoGui.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QPlainTextEdit, QSizePolicy,
    QWidget)
from qt_embedded import resources

class Ui_HealthInfoDialog(object):
    def setupUi(self, HealthInfoDialog):
        if not HealthInfoDialog.objectName():
            HealthInfoDialog.setObjectName(u"HealthInfoDialog")
        HealthInfoDialog.resize(850, 400)
        HealthInfoDialog.setMinimumSize(QSize(850, 400))
        HealthInfoDialog.setMaximumSize(QSize(850, 400))
        icon = QIcon()
        icon.addFile(u":/icons/heart.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        HealthInfoDialog.setWindowIcon(icon)
        self.console_output = QPlainTextEdit(HealthInfoDialog)
        self.console_output.setObjectName(u"console_output")
        self.console_output.setGeometry(QRect(10, 10, 831, 371))
        self.console_output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)
        self.console_output.setBackgroundVisible(False)

        self.retranslateUi(HealthInfoDialog)

        QMetaObject.connectSlotsByName(HealthInfoDialog)
    # setupUi

    def retranslateUi(self, HealthInfoDialog):
        HealthInfoDialog.setWindowTitle(QCoreApplication.translate("HealthInfoDialog", u"Health Info", None))
    # retranslateUi


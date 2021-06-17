import sys
import json
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QPushButton, QMainWindow, QFileDialog, QLineEdit, QLabel, QGraphicsView, QWidget
from PySide6.QtCore import QFile, QIODevice
from automapy import DFA, NFA
from PySide6 import QtCore, QtGui, QtWidgets


class PhotoViewer(QtWidgets.QGraphicsView):

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtGui.QPixmap())
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0

    def toggleDragMode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        super(PhotoViewer, self).mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, ui_file_name, parent=None):
        super(MainWindow, self).__init__(parent)
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
            sys.exit(-1)
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        if not self.window:
            print(loader.errorString())
            sys.exit(-1)


        self.browseButton = self.window.findChild(QPushButton, "browseButton")
        self.browseButton.clicked.connect(self.browseButtonHandler)

        self.browseLineEdit = self.window.findChild(QLineEdit, "browseLineEdit")
        self.browseLineEdit.setReadOnly(True)

        self.inputFileName = None

        self.nfa = None  # type: NFA
        self.dfa = None  # type: DFA
        self.minDfa = None  # type: DFA

        self.browseButton = self.window.findChild(QPushButton, "browseButton")
        self.browseButton.clicked.connect(self.browseButtonHandler)

        self.processButton = self.window.findChild(QPushButton, "processButton")
        self.processButton.clicked.connect(self.processButtonHandler)

        self.checkButton = self.window.findChild(QPushButton, "checkButton")
        self.checkButton.clicked.connect(self.checkButtonHandler)

        self.statusLabel = self.window.findChild(QLabel, "statusLabel")  # type: QLabel
        self.inputLineEdit = self.window.findChild(QLineEdit, "inputLineEdit")  # type: QLineEdit

        self.nfaViewer = PhotoViewer(self)
        self.nfaTab = self.window.findChild(QWidget, "nfaTab")  # type: QWidget
        self.nfaTab.layout().addWidget(self.nfaViewer)

        self.dfaViewer = PhotoViewer(self)
        self.dfaTab = self.window.findChild(QWidget, "dfaTab")  # type: QWidget
        self.dfaTab.layout().addWidget(self.dfaViewer)

        self.minDfaViewer = PhotoViewer(self)
        self.minDfaTab = self.window.findChild(QWidget, "minDfaTab")  # type: QWidget
        self.minDfaTab.layout().addWidget(self.minDfaViewer)

        self.window.show()

    def browseButtonHandler(self, parentWidget):
        filename, filter = QFileDialog.getOpenFileName(parent=self, caption='Open file', dir='.', filter='*.json')
        self.browseLineEdit.setText(filename)
        self.inputFileName = filename

    def processButtonHandler(self, parentWidget):
        if self.inputFileName is None:
            return

        data = json.load(open(self.inputFileName))

        transitions = {}
        for currentState, inputLetter, nextStates in data["transitions"]:
            transitions.setdefault(currentState, {})[inputLetter] = nextStates

        self.nfa = NFA(
                data["states"],
                data["alphabet"],
                transitions,
                data["initial"],
                data["final"]
            )
        self.dfa = self.nfa.toDFA()
        self.minDfa = self.dfa.minimize()

        self.dfa.visualize().render("automapy_dfa")
        self.dfaViewer.setPhoto(QtGui.QPixmap("automapy_dfa.png"))

        self.minDfa.visualize().render("automapy_minDfa")
        self.minDfaViewer.setPhoto(QtGui.QPixmap("automapy_minDfa.png"))

        self.nfa.visualize().render("automapy_nfa")
        self.nfaViewer.setPhoto(QtGui.QPixmap("automapy_nfa.png"))

    def checkButtonHandler(self, parentWidget):
        if self.dfa is None:
            self.statusLabel.setText("No automato")
        elif self.dfa.accepts(self.inputLineEdit.text()):
            self.statusLabel.setText("Accepts")
        else:
            self.statusLabel.setText("Rejects")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ui_file_name = "automapy.ui"
    mainWindow = MainWindow(ui_file_name=ui_file_name)

    sys.exit(app.exec())

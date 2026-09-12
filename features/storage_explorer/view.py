"""Virtualized tree: Qt creates indexes only for visible rows."""
from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, QThreadPool, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QFileDialog, QTreeView, QPlainTextEdit, QProgressBar)
from core.workers import FunctionWorker
from .models import format_size
from .analyzer import advice, largest_path
from .scanner import validate_root
from pathlib import Path


class StorageTreeModel(QAbstractItemModel):
    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.root = root

    def columnCount(self, parent=QModelIndex()):
        return 3

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid() and parent.column() != 0:
            return 0
        return len(parent.internalPointer().children) if parent.isValid() else 1

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        node = parent.internalPointer().children[row] if parent.isValid() else self.root
        return self.createIndex(row, column, node)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer().parent
        return self.createIndex(node.row, 0, node) if node else QModelIndex()

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == Qt.ItemDataRole.ToolTipRole:
            return node.path
        if role == Qt.ItemDataRole.DisplayRole:
            return (node.path if node.parent is None else Path(node.path).name,
                    format_size(node.size), node.status)[index.column()]

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return ("File / folder", "Logical size", "Coverage")[section]


class StorageView(QWidget):
    def __init__(self, service, app_state):
        super().__init__()
        self.service, self.app_state = service, app_state
        self.worker = None
        self.result = None
        self.model = None
        self.route = iter(())
        self.timer = QTimer(self)
        self.timer.setInterval(1200)
        self.timer.timeout.connect(self._guide_next)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Storage Explorer")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        note = QLabel("Read-only • No deletion • Local metadata only\nLogical sizes are not reclaimable disk space. Links/cloud placeholders are excluded; hard links may be counted more than once.")
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        self.drives = QComboBox()
        row.addWidget(self.drives, 1)
        self.refresh = QPushButton("List drives")
        self.start = QPushButton("Scan selected drive")
        self.choose = QPushButton("Choose folder…")
        self.cancel = QPushButton("Cancel")
        self.cancel.setEnabled(False)
        for button in (self.refresh, self.start, self.choose, self.cancel):
            row.addWidget(button)
        layout.addLayout(row)
        self.refresh.clicked.connect(self._drives)
        self.start.clicked.connect(lambda: self.start_scan(self.drives.currentData()))
        self.choose.clicked.connect(self._choose)
        self.cancel.clicked.connect(self._cancel)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel("No scan yet. List drives or choose a folder to begin.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.tree = QTreeView()
        self.tree.setUniformRowHeights(True)
        layout.addWidget(self.tree, 1)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(115)
        layout.addWidget(self.details)
        actions = QHBoxLayout()
        self.rescan = QPushButton("Re-scan selected item")
        self.open_location = QPushButton("Open containing folder")
        self.top = QPushButton("Show 100 largest files")
        for button in (self.rescan, self.open_location, self.top):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.rescan.clicked.connect(self._rescan)
        self.open_location.clicked.connect(self._open)
        self.top.clicked.connect(self._largest)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(150)
        self.log.setMaximumHeight(125)
        layout.addWidget(self.log)
        self._busy(False)

    def _busy(self, busy):
        for button in (self.refresh, self.choose):
            button.setEnabled(not busy)
        self.start.setEnabled(not busy and self.drives.count() > 0)
        self.drives.setEnabled(not busy)
        for button in (self.rescan, self.open_location, self.top):
            button.setEnabled(not busy and self.result is not None)
        self.cancel.setEnabled(busy)
        self.progress.setRange(0, 0 if busy else 1)
        self.progress.setValue(0 if busy else 1)
        self.progress.setFormat("Working…" if busy else "Idle / see coverage below")

    def _run(self, function, callback, *args):
        if self.worker:
            return
        self.timer.stop()
        self._busy(True)
        self.worker = FunctionWorker(function, *args)
        self.worker.signals.progress.connect(self.status.setText)
        self.worker.signals.finished.connect(callback)
        self.worker.signals.error.connect(self._error)
        QThreadPool.globalInstance().start(self.worker)

    def _drives(self):
        self.status.setText("Checking fixed local drives…")
        self._run(self.service.list_drives, self._got_drives)

    def _got_drives(self, payload):
        drives, unavailable = payload
        self.worker = None
        self.drives.clear()
        for drive in drives:
            self.drives.addItem(f"{drive.path} | {format_size(drive.used)} / {format_size(drive.total)} used ({drive.percent:.1f}%) | {format_size(drive.free)} free", drive.path)
        message = "No available fixed local drives."
        if drives:
            fullest = max(drives, key=lambda drive: drive.percent)
            message = f"Most used by bytes: {drives[0].path}. Highest percentage: {fullest.path} ({fullest.percent:.1f}%). Selected the first; press Scan to continue."
        if unavailable:
            message += " Unavailable: " + ", ".join(unavailable)
        self.status.setText(message)
        self.log.appendPlainText(message)
        self._busy(False)

    def _choose(self):
        path = QFileDialog.getExistingDirectory(self, "Choose a local folder")
        if path:
            self.start_scan(path)

    def start_scan(self, path):
        if not path or self.worker:
            return
        self.log.clear()
        self.log.appendPlainText(f"Starting metadata scan: {path}")
        self._run(self.service.scan, self._finished, path)

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
            self.status.setText("Cancellation requested; waiting for the current filesystem call…")

    def _error(self, error):
        self.worker = None
        self.status.setText(f"Operation failed: {error}. Previous results, if shown, are unchanged.")
        self._busy(False)

    def _finished(self, result):
        self.worker = None
        self.result = result
        old_model = self.model
        self.model = StorageTreeModel(result.root, self)
        self.tree.setModel(self.model)
        if old_model:
            old_model.deleteLater()
        self.tree.setColumnWidth(0, 410)
        self.tree.setColumnWidth(1, 130)
        self.tree.selectionModel().currentChanged.connect(self._selected)
        self.tree.expand(self.model.index(0, 0))
        self.tree.setCurrentIndex(self.model.index(0, 0))
        flags = " CANCELLED." if result.cancelled else ""
        if result.limited:
            flags += " Node limit reached; scan a smaller folder."
        summary = (f"{result.finished_at:%Y-%m-%d %H:%M:%S} | {result.root.status} | "
                   f"{format_size(result.root.size)} logical | {result.files:,} files | "
                   f"{result.skipped:,} excluded/unavailable | {result.hardlink_entries:,} hard-link entries." + flags)
        self.status.setText(summary)
        self.log.appendPlainText(summary)
        self.app_state.storage_summary = summary
        self.app_state.changed.emit()
        self._busy(False)
        self.route = iter(largest_path(result.root))
        self.timer.start()

    def _guide_next(self):
        try:
            node, message = next(self.route)
        except StopIteration:
            self.timer.stop()
            return
        self.log.appendPlainText(message)
        self.log.appendPlainText(advice(node))

    def _node(self):
        index = self.tree.currentIndex()
        return index.internalPointer() if index.isValid() else None

    def _selected(self, current, previous):
        node = self._node()
        if node:
            percent = node.size * 100 / node.parent.size if node.parent and node.parent.size else 0
            share = f" | {percent:.1f}% of observed parent" if node.parent else ""
            self.details.setPlainText(f"{node.path}\n{node.size:,} logical bytes | {node.status}{share}\n{advice(node)}")

    def _rescan(self):
        node = self._node()
        if node:
            self.start_scan(node.path)

    def _open(self):
        node = self._node()
        if node:
            try:
                folder = validate_root(Path(node.path).parent)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            except (OSError, ValueError) as error:
                self.status.setText(str(error))

    def _largest(self):
        self.timer.stop()
        self.log.clear()
        for node in self.result.largest_files:
            self.log.appendPlainText(f"{format_size(node.size)} | {node.path}")

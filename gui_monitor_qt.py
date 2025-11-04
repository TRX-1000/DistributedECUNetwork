# gui_monitor_qt.py
import sys
import queue
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMainWindow, QFrame
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QFont


class ECUTable(QTableWidget):
    """Table to display ECU data dynamically"""
    def __init__(self):
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["Parameter", "Value", "Status"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().hide()
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setStyleSheet("QTableWidget { background-color: #1e1e1e; color: white; }")


class ECUPanel(QWidget):
    """Individual ECU display"""
    def __init__(self, ecu_name):
        super().__init__()
        layout = QVBoxLayout()
        self.title = QLabel(ecu_name)
        self.title.setFont(QFont("Arial", 14, QFont.Bold))
        self.title.setStyleSheet("color: #00ffff;")
        layout.addWidget(self.title)

        self.table = ECUTable()
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.table_data = {}

    def update_data(self, data, faults):
        self.table.setRowCount(len(data))
        for i, (key, value) in enumerate(data.items()):
            val_item = QTableWidgetItem(str(round(value, 2) if isinstance(value, (float, int)) else value))
            val_item.setTextAlignment(Qt.AlignCenter)
            status_item = QTableWidgetItem("OK")

            # Color code faults
            if any(key.lower() in f.lower() for f in faults):
                status_item.setText("FAULT")
                status_item.setBackground(QColor(255, 70, 70))
            else:
                status_item.setBackground(QColor(70, 255, 70))

            self.table.setItem(i, 0, QTableWidgetItem(key))
            self.table.setItem(i, 1, val_item)
            self.table.setItem(i, 2, status_item)


class ECUNetworkMonitor(QMainWindow):
    """Main window for ECU network GUI"""
    def __init__(self, network, update_queue):
        super().__init__()
        self.network = network
        self.update_queue = update_queue

        self.setWindowTitle("ECU Network Monitor")
        self.setGeometry(200, 200, 1100, 700)

        central = QWidget()
        self.setCentralWidget(central)

        # Layouts
        main_layout = QVBoxLayout()
        ecu_layout = QHBoxLayout()
        button_layout = QHBoxLayout()

        # ECU panels
        self.ecu_panels = {}
        for ecu_name in self.network.ecus:
            panel = ECUPanel(ecu_name)
            ecu_layout.addWidget(panel)
            self.ecu_panels[ecu_name] = panel

        # Buttons
        self.btn_start = QPushButton("Start Monitoring")
        self.btn_pause = QPushButton("Pause")
        self.btn_stop = QPushButton("Stop & Generate Summary")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_pause.setStyleSheet("background-color: #FFC107; color: black; font-weight: bold;")
        self.btn_stop.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")

        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_pause)
        button_layout.addWidget(self.btn_stop)

        # Log window
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #111; color: #ddd;")
        self.log_box.setFont(QFont("Consolas", 10))

        # Assemble main layout
        main_layout.addLayout(ecu_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(QLabel("Event Log:"))
        main_layout.addWidget(self.log_box)
        central.setLayout(main_layout)

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gui)
        self.timer.start(500)

        # Button actions
        self.btn_start.clicked.connect(self.start_monitoring)
        self.btn_pause.clicked.connect(self.pause_monitoring)
        self.btn_stop.clicked.connect(self.stop_and_summary)

        self.running = True
        self.logs = []

    def update_gui(self):
        while not self.update_queue.empty():
            msg_type, ecu_name, payload = self.update_queue.get()
            if msg_type == "update":
                data, faults = payload
                if ecu_name in self.ecu_panels:
                    self.ecu_panels[ecu_name].update_data(data, faults)
            elif msg_type == "log":
                self.logs.append(payload)
                self.log_box.append(payload)

    def start_monitoring(self):
        self.running = True
        self.log_box.append("[INFO] Monitoring resumed.")

    def pause_monitoring(self):
        self.running = False
        self.log_box.append("[INFO] Monitoring paused.")

    def stop_and_summary(self):
        """Generate a simple summary report."""
        self.running = False
        summary = "\n--- ECU SUMMARY REPORT ---\n"
        summary += f"Total messages processed: {len(self.logs)}\n"
        fault_count = sum("FAULT" in log for log in self.logs)
        summary += f"Total faults detected: {fault_count}\n\n"
        summary += "Recent 5 log entries:\n" + "\n".join(self.logs[-5:])
        self.log_box.append(summary)
        print(summary)


def run_gui(network, update_queue):
    app = QApplication(sys.argv)
    window = ECUNetworkMonitor(network, update_queue)
    window.show()
    sys.exit(app.exec_())

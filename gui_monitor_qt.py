import sys
import queue
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMainWindow, QFrame
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QFont


class ECUTable(QTableWidget):
    def __init__(self):
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["Parameter", "Value", "Status"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.setColumnWidth(0, 130)
        self.setColumnWidth(2, 60)
        self.verticalHeader().hide()
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: white;
                gridline-color: #3a3a3a;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #2c2c2c;
                color: #ffffff;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-bottom: 2px solid #555555;
                border-right: 1px solid #555555;
            }
        """)


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
        self.active_faults = set()

        

    
    def update_data(self, data, faults):
        self.table.setRowCount(len(data))
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Accumulate faults — never clear automatically
        for fault in faults:
            self.active_faults.add(fault)
        
        for i, (key, value) in enumerate(data.items()):
            # Parameter name
            param_item = QTableWidgetItem(key)
            param_item.setForeground(QColor(200, 200, 200))
            
            # Value
            if isinstance(value, float):
                display_val = f"{value:.2f}"
            elif isinstance(value, bool):
                display_val = "YES" if value else "NO"
            else:
                display_val = str(value)
                
            val_item = QTableWidgetItem(display_val)
            val_item.setTextAlignment(Qt.AlignCenter)
    
            # Status
            status_item = QTableWidgetItem("OK")
            status_item.setTextAlignment(Qt.AlignCenter)

            # Check against accumulated faults, not just current ones
            is_faulted = any(
                key.lower().replace("_", "") in f.lower().replace("_", "")
                or f.lower().replace("_", "") in key.lower().replace("_", "")
                for f in self.active_faults
            )

            if is_faulted:
                status_item.setText("FAULT")
                status_item.setBackground(QColor(200, 50, 50))
                status_item.setForeground(QColor(255, 255, 255))
                val_item.setBackground(QColor(80, 20, 20))
                val_item.setForeground(QColor(255, 150, 150))
            else:
                status_item.setBackground(QColor(30, 120, 30))
                status_item.setForeground(QColor(150, 255, 150))
                val_item.setBackground(QColor(30, 30, 30))
                val_item.setForeground(QColor(200, 200, 200))

            self.table.setItem(i, 0, param_item)
            self.table.setItem(i, 1, val_item)
            self.table.setItem(i, 2, status_item)


class ECUNetworkMonitor(QMainWindow):
    """Main window for ECU network GUI"""
    def __init__(self, network, update_queue, ecus):
        super().__init__()
        self.network = network
        self.update_queue = update_queue
        self.ecus = ecus

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
        self.btn_stop = QPushButton("Stop and Generate Summary")
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

        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(True)

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
        for ecu in self.ecus.values():
            ecu.generate_event.set()
        self.log_box.append("[INFO] Monitoring started.")
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)

    def pause_monitoring(self):
        for ecu in self.ecus.values():
            ecu.generate_event.clear()
        self.log_box.append("[INFO] Monitoring paused.")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)

    def stop_and_summary(self):
        for ecu in self.ecus.values():
            ecu.stop()
        summary = "\n--- ECU SUMMARY REPORT ---\n"
        summary += f"Total log entries: {len(self.logs)}\n"
        fault_count = sum("FAULT" in log for log in self.logs)
        summary += f"Total faults detected: {fault_count}\n"
        summary += f"Network messages sent: {self.network.stats.messages_sent}\n"
        summary += f"Bytes transferred: {self.network.stats.bytes_transferred}\n\n"
        summary += "Recent 5 log entries:\n" + "\n".join(self.logs[-5:])
        self.log_box.append(summary)
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)


def run_gui(network, update_queue):
    app = QApplication(sys.argv)
    window = ECUNetworkMonitor(network, update_queue)
    window.show()
    sys.exit(app.exec_())

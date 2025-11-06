################################################################################
#                                                                              #
#                            📁 GUI.py                                         #
#                     Graphical User Interface Module                          #
#                                                                              #
################################################################################

import sys
from queue import Queue
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QColor, QPalette, QBrush, QLinearGradient


class ECUTable(QTableWidget):
    def __init__(self):
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["Parameter", "Value", "Status"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().hide()
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setStyleSheet("""
            QTableWidget {
                background-color: #0e1316;
                color: #e6f2f1;
                gridline-color: #172424;
                selection-background-color: #054a52;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #122426;
                color: #cfeeea;
                padding: 6px;
                border: none;
            }
        """)


class ECUPanel(QWidget):
    def __init__(self, ecu_name, thresholds):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(8,8,8,8)
        layout.setSpacing(6)
        
        icon_map = {
            "EngineECU": "🔧",
            "FuelECU": "⛽",
            "TransmissionECU": "⚙️",
            "BrakeECU": "🛑"
        }
        icon = icon_map.get(ecu_name, "🚗")
        
        self.title = QLabel(f"  {icon}  {ecu_name}")
        self.title.setFont(QFont("Arial", 14, QFont.Bold))
        self.title.setStyleSheet("color: #8ffaf0; padding-left:6px;")
        layout.addWidget(self.title)

        status_row = QHBoxLayout()
        self.status_label = QLabel("● Offline")
        self.status_label.setStyleSheet("color: #8a9998; font-weight: 600;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.table_widget = QWidget()
        self.table_layout = QVBoxLayout()
        self.table_layout.setContentsMargins(0,0,0,0)
        self.table = ECUTable()
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table_layout.addWidget(self.table)
        self.table_widget.setLayout(self.table_layout)
        self.scroll.setWidget(self.table_widget)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #072025, stop:1 #0b2f2f);
                border-radius: 10px;
                padding: 6px;
            }
        """)
        self.thresholds = thresholds or {}

    def update_data(self, data, faults):
        keys = list(data.keys())
        self.table.setRowCount(len(keys))
        for i, key in enumerate(keys):
            value = data[key]
            
            if isinstance(value, bool):
                display_val = "YES" if value else "NO"
            elif isinstance(value, float):
                display_val = str(round(value, 3))
            else:
                display_val = str(value)
                
            key_item = QTableWidgetItem(key)
            val_item = QTableWidgetItem(display_val)
            val_item.setTextAlignment(Qt.AlignCenter)
            val_item.setForeground(QColor("#e8f8f6"))

            status_item = QTableWidgetItem("OK")
            status_item.setTextAlignment(Qt.AlignCenter)

            matched_fault = any(key.lower() in f.lower() for f in faults)
            if matched_fault:
                status_item.setText("FAULT")
                status_item.setBackground(QColor(255, 70, 70))
            else:
                thr = self._find_threshold(key)
                
                if thr is not None and isinstance(value, (int, float)):
                    try:
                        v = float(value)
                        
                        if any(x in key.lower() for x in ["level", "thickness"]):
                            if v < float(thr):
                                status_item.setText("WARNING")
                                status_item.setBackground(QColor(255, 200, 60))
                            else:
                                status_item.setText("OK")
                                status_item.setBackground(QColor(70, 255, 120))
                        elif "o2" in key.lower() or "afratio" in key.lower():
                            if v > 15.5 or v < 13.5:
                                status_item.setText("WARNING")
                                status_item.setBackground(QColor(255, 200, 60))
                            else:
                                status_item.setText("OK")
                                status_item.setBackground(QColor(70, 255, 120))
                        elif "battery" in key.lower():
                            if v < 11.5 or v > 14.8:
                                status_item.setText("WARNING")
                                status_item.setBackground(QColor(255, 200, 60))
                            else:
                                status_item.setText("OK")
                                status_item.setBackground(QColor(70, 255, 120))
                        else:
                            if v > float(thr):
                                status_item.setText("WARNING")
                                status_item.setBackground(QColor(255, 200, 60))
                            else:
                                status_item.setText("OK")
                                status_item.setBackground(QColor(70, 255, 120))
                    except:
                        status_item.setText("OK")
                        status_item.setBackground(QColor(70, 255, 120))
                else:
                    status_item.setText("OK")
                    status_item.setBackground(QColor(70, 255, 120))

            self.table.setItem(i, 0, key_item)
            self.table.setItem(i, 1, val_item)
            self.table.setItem(i, 2, status_item)

    def _find_threshold(self, key):
        if key in self.thresholds:
            return self.thresholds[key]
        for tkey in self.thresholds.keys():
            if key.startswith(tkey):
                return self.thresholds[tkey]
        return None


class StatsDashboard(QWidget):
    def __init__(self, network):
        super().__init__()
        self.network = network
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        title = QLabel("📊 Network Statistics")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #8ffaf0;")
        layout.addWidget(title)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        
        self.msg_sent_label = QLabel("Messages Sent:")
        self.msg_sent_value = QLabel("0")
        self.msg_sent_value.setStyleSheet("color: #7ef6d8; font-size: 18px; font-weight: bold;")
        grid.addWidget(self.msg_sent_label, 0, 0)
        grid.addWidget(self.msg_sent_value, 0, 1)
        
        self.data_label = QLabel("Data Transferred:")
        self.data_value = QLabel("0 bytes")
        self.data_value.setStyleSheet("color: #7ef6d8; font-size: 18px; font-weight: bold;")
        grid.addWidget(self.data_label, 1, 0)
        grid.addWidget(self.data_value, 1, 1)
        
        self.latency_label = QLabel("Network Latency:")
        self.latency_value = QLabel(f"{self.network.latency_ms} ms")
        self.latency_value.setStyleSheet("color: #7ef6d8; font-size: 18px; font-weight: bold;")
        grid.addWidget(self.latency_label, 2, 0)
        grid.addWidget(self.latency_value, 2, 1)
        
        layout.addLayout(grid)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #072025, stop:1 #0b2f2f);
                border-radius: 10px;
            }
            QLabel {
                color: #e6f2f1;
                font-size: 14px;
            }
        """)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(500)
    
    def update_stats(self):
        with self.network.stats.lock:
            self.msg_sent_value.setText(str(self.network.stats.messages_sent))
            
            bytes_val = self.network.stats.bytes_transferred
            if bytes_val < 1024:
                data_str = f"{bytes_val} bytes"
            elif bytes_val < 1024 * 1024:
                data_str = f"{bytes_val / 1024:.2f} KB"
            else:
                data_str = f"{bytes_val / (1024 * 1024):.2f} MB"
            self.data_value.setText(data_str)


class ECUNetworkMonitor(QMainWindow):
    def __init__(self, network, update_queue, ecus):
        super().__init__()
        self.network = network
        self.update_queue = update_queue
        self.ecus = ecus

        self.setWindowTitle("🚘 Enhanced Distributed ECU Network Monitor")
        self.setGeometry(50, 30, 1600, 900)

        palette = QPalette()
        gradient = QLinearGradient(0, 0, 1, 1)
        gradient.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
        gradient.setColorAt(0.0, QColor("#051218"))
        gradient.setColorAt(0.5, QColor("#0b3332"))
        gradient.setColorAt(1.0, QColor("#14343b"))
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #1a4d4d;
                border-radius: 8px;
                background: transparent;
            }
            QTabBar::tab {
                background: #0a2528;
                color: #9fd8d3;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #0f3d3d;
                color: #7ef6d8;
                font-weight: bold;
            }
        """)

        self.ecu_panels = {}
        for name, ecu in self.ecus.items():
            thresholds = getattr(ecu, "THRESHOLDS", {})
            panel = ECUPanel(name, thresholds)
            panel.setMinimumWidth(500)
            self.ecu_panels[name] = panel
            self.tab_widget.addTab(panel, name.replace("ECU", ""))

        self.stats_dashboard = StatsDashboard(self.network)
        self.tab_widget.addTab(self.stats_dashboard, "📊 Stats")

        main_layout.addWidget(self.tab_widget)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(12)

        self.btn_toggle = QPushButton("▶ Start Monitoring")
        self.btn_toggle.setFixedWidth(220)
        self.btn_toggle.setStyleSheet("background-color: #2ecc71; color: white; font-weight:bold; padding:12px; border-radius:10px;")
        self.btn_toggle.clicked.connect(self.on_toggle)

        self.btn_stop = QPushButton("🛑 Stop and Generate Summary")
        self.btn_stop.setFixedWidth(250)
        self.btn_stop.setStyleSheet("background-color: #e74c3c; color: white; font-weight:bold; padding:12px; border-radius:10px;")
        self.btn_stop.clicked.connect(self.on_stop)

        self.btn_log = QPushButton("📜 Show Log")
        self.btn_log.setFixedWidth(140)
        self.btn_log.setStyleSheet("background-color: #3498db; color: white; font-weight:bold; padding:12px; border-radius:10px;")
        self.btn_log.clicked.connect(self.toggle_log)

        ctrl_layout.addWidget(self.btn_toggle)
        ctrl_layout.addWidget(self.btn_stop)
        ctrl_layout.addWidget(self.btn_log)
        ctrl_layout.addStretch()

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setVisible(False)
        self.log_box.setStyleSheet("background-color:#071216;color:#dff3f0;border-radius:8px;padding:8px;")
        self.log_box.setFont(QFont("Consolas", 9))
        self.log_box.setMinimumHeight(180)
        self.log_box.setMaximumHeight(250)

        main_layout.addLayout(ctrl_layout)
        main_layout.addWidget(self.log_box)
        central.setLayout(main_layout)

        self.status_bar = QStatusBar()
        self.status_bar.showMessage("🔴 Idle — press Start")
        self.setStatusBar(self.status_bar)

        self.state = "stopped"
        self.logs = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gui)
        self.timer.start(50)

    def on_toggle(self):
        if self.state == "stopped":
            self.start_all_ecus()
            self.state = "running"
            self.btn_toggle.setText("⏸ Pause")
            self.btn_toggle.setStyleSheet("background-color: #f1c40f; color: black; font-weight:bold; padding:12px; border-radius:10px;")
            self.status_bar.showMessage("🟢 Running")
            self._append_log("[INFO] Monitoring started.")
        elif self.state == "running":
            for ecu in self.ecus.values():
                ecu.generate_event.clear()
            self.state = "paused"
            self.btn_toggle.setText("▶ Resume")
            self.btn_toggle.setStyleSheet("background-color: #2ecc71; color: white; font-weight:bold; padding:12px; border-radius:10px;")
            self.status_bar.showMessage("⏸ Paused")
            self._append_log("[WARN] Monitoring paused.")
        elif self.state == "paused":
            for ecu in self.ecus.values():
                ecu.generate_event.set()
            self.state = "running"
            self.btn_toggle.setText("⏸ Pause")
            self.btn_toggle.setStyleSheet("background-color: #f1c40f; color: black; font-weight:bold; padding:12px; border-radius:10px;")
            self.status_bar.showMessage("🟢 Running")
            self._append_log("[INFO] Monitoring resumed.")

    def on_stop(self):
        if self.state != "stopped":
            for ecu in self.ecus.values():
                ecu.generate_event.clear()
                ecu.stop()
            self.state = "stopped"
            self.btn_toggle.setText("▶ Start Monitoring")
            self.btn_toggle.setStyleSheet("background-color: #2ecc71; color: white; font-weight:bold; padding:12px; border-radius:10px;")
            self.status_bar.showMessage("🛑 Stopped")
            
            self._generate_summary()
            
            for panel in self.ecu_panels.values():
                panel.status_label.setText("● Offline")
                panel.status_label.setStyleSheet("color: #8a9998; font-weight: 600;")

    def _generate_summary(self):
        from ecu_base import DTC_CODES
        
        self._append_log("\n" + "="*80)
        self._append_log("📊 SESSION SUMMARY")
        self._append_log("="*80)
        
        with self.network.stats.lock:
            self._append_log(f"\n🌐 Network Statistics:")
            self._append_log(f"   • Total Messages: {self.network.stats.messages_sent}")
            
            bytes_val = self.network.stats.bytes_transferred
            if bytes_val < 1024:
                data_str = f"{bytes_val} bytes"
            elif bytes_val < 1024 * 1024:
                data_str = f"{bytes_val / 1024:.2f} KB"
            else:
                data_str = f"{bytes_val / (1024 * 1024):.2f} MB"
            self._append_log(f"   • Data Transferred: {data_str}")
            self._append_log(f"   • Average Latency: {self.network.latency_ms} ms")
        
        for ecu_name, ecu in self.ecus.items():
            self._append_log(f"\n🔧 {ecu_name}:")
            
            metrics = ecu.performance_metrics
            self._append_log(f"   • Avg Loop Time: {metrics['loop_time_avg']*1000:.2f} ms")
            self._append_log(f"   • Max Loop Time: {metrics['loop_time_max']*1000:.2f} ms")
            self._append_log(f"   • Messages Processed: {metrics['messages_processed']}")
            
            with ecu.lock:
                if ecu.data:
                    self._append_log(f"   • Final State:")
                    for key, value in list(ecu.data.items())[:5]:
                        if isinstance(value, float):
                            self._append_log(f"      - {key}: {value:.2f}")
                        else:
                            self._append_log(f"      - {key}: {value}")
            
            if ecu.dtc_codes:
                self._append_log(f"   ⚠️  Active DTCs: {', '.join(ecu.dtc_codes)}")
                for code in ecu.dtc_codes:
                    if code in DTC_CODES:
                        self._append_log(f"      - {code}: {DTC_CODES[code]}")
            else:
                self._append_log(f"   ✅ No Active DTCs")
        
        self._append_log(f"\n🏥 Overall System Health:")
        total_dtcs = sum(len(ecu.dtc_codes) for ecu in self.ecus.values())
        if total_dtcs == 0:
            self._append_log(f"   ✅ All systems nominal - no faults detected")
        elif total_dtcs <= 2:
            self._append_log(f"   ⚠️  Minor issues detected ({total_dtcs} DTC(s)) - monitoring recommended")
        else:
            self._append_log(f"   ❌ Multiple faults detected ({total_dtcs} DTC(s)) - service required")
        
        self._append_log("\n" + "="*80)
        self._append_log("[INFO] Monitoring session ended.\n")
        
        if not self.log_box.isVisible():
            self.toggle_log()

    def toggle_log(self):
        visible = not self.log_box.isVisible()
        self.log_box.setVisible(visible)
        self.btn_log.setText("📜 Hide Log" if visible else "📜 Show Log")

    def update_gui(self):
        while not self.update_queue.empty():
            msg_type, ecu_name, payload = self.update_queue.get()
            if msg_type == "update":
                data, faults = payload
                if ecu_name in self.ecu_panels:
                    self.ecu_panels[ecu_name].update_data(data, faults)
                    self.ecu_panels[ecu_name].status_label.setText("● Online")
                    self.ecu_panels[ecu_name].status_label.setStyleSheet("color: #7ef6d8; font-weight: 700;")
            elif msg_type == "log":
                self.logs.append(payload)
                self._append_log(payload)

    def _append_log(self, text):
        color = "#ffffff"
        if "FAULT" in text:
            color = "#ff5555"
        elif "[WARN]" in text or "WARN" in text:
            color = "#ffcc00"
        elif "[INFO]" in text:
            color = "#7ef6d8"
        formatted = f"<span style='color:{color}'>{text}</span>"
        self.log_box.append(formatted)
        
        scrollbar = self.log_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_all_ecus(self):
        import time
        for ecu in self.ecus.values():
            if not ecu.is_alive():
                ecu.running = True
                try:
                    ecu.start()
                except RuntimeError:
                    pass
            ecu.generate_event.set()

    def closeEvent(self, event):
        import time
        for ecu in self.ecus.values():
            ecu.stop()
        time.sleep(0.2)
        event.accept()

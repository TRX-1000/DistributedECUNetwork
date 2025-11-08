################################################################################
#                                                                              #
#                          📁 ecu_base.py                                      #
#                         Base ECU Implementation                              #
#                                                                              #
################################################################################

import threading
import time
from queue import Queue
from collections import deque
from datetime import datetime

# Configuration
MAIN_TICK = 0.1
FAST = 0.1
MEDIUM = 0.5
SLOW = 2.0

# DTC definitions
DTC_CODES = {
    "P0100": "Mass Air Flow Circuit Malfunction",
    "P0171": "System Too Lean (Bank 1)",
    "P0300": "Random/Multiple Cylinder Misfire",
    "P0420": "Catalyst System Efficiency Below Threshold",
    "P0700": "Transmission Control System Malfunction",
    "P1450": "Barometric Pressure Sensor Circuit",
    "C1201": "ABS Control Module Communication Error",
    "B1342": "ECM Internal Temperature Sensor Circuit",
}


def now_s():
    return time.time()


def timestamp():
    return datetime.now().strftime("[%H:%M:%S.%f]")[:-3]


def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))


class BaseECU(threading.Thread):
    def __init__(self, name, update_queue, main_tick=MAIN_TICK):
        super().__init__(daemon=True)
        self.name = name
        self.network = None
        self.main_tick = main_tick
        self.running = True
        self.generate_event = threading.Event()
        self.generate_event.clear()
        self.update_queue = update_queue
        self.received_messages = Queue()
        self.data = {}
        self.lock = threading.Lock()
        self._last_tick = now_s()
        self.dtc_codes = []
        self.performance_metrics = {
            'loop_time_avg': 0.0,
            'loop_time_max': 0.0,
            'messages_processed': 0
        }

    def log(self, msg):
        full = f"{timestamp()} {self.name}: {msg}"
        self.update_queue.put(("log", self.name, full))

    def send_message(self, target, data):
        if self.network:
            self.network.send(self.name, target, data)

    def receive_message(self, src, data):
        self.received_messages.put((src, data))

    def add_dtc(self, code):
        if code not in self.dtc_codes and code in DTC_CODES:
            self.dtc_codes.append(code)
            self.log(f"[FAULT] DTC {code}: {DTC_CODES[code]}")

    def clear_dtc(self, code):
        if code in self.dtc_codes:
            self.dtc_codes.remove(code)
            self.log(f"[INFO] DTC {code} cleared")

    def stop(self):
        self.running = False
        self.generate_event.set()

    def run(self):
        loop_times = deque(maxlen=50)
        
        while self.running:
            self.generate_event.wait()
            if not self.running:
                break
            
            t0 = now_s()
            self.process_incoming()
            
            try:
                self.generate_data()
            except Exception as e:
                self.log(f"[FAULT] Exception in generate_data: {e}")
            
            elapsed = now_s() - t0
            loop_times.append(elapsed)
            
            if len(loop_times) > 0:
                self.performance_metrics['loop_time_avg'] = sum(loop_times) / len(loop_times)
                self.performance_metrics['loop_time_max'] = max(loop_times)
            
            time.sleep(max(0.0, self.main_tick - elapsed))

    def process_incoming(self):
        count = 0
        while not self.received_messages.empty():
            src, data = self.received_messages.get()
            count += 1
            try:
                self.handle_message(src, data)
            except Exception as e:
                self.log(f"[WARN] Error handling message from {src}: {e}")
        self.performance_metrics['messages_processed'] += count

    def generate_data(self):
        pass

    def handle_message(self, src, data):
        pass

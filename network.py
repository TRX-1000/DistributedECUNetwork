################################################################################
#                                                                              #
#                           📁 network.py                                      #
#                        Network Infrastructure                                #
#                                                                              #
################################################################################

import threading
import time
from collections import deque


class NetworkStats:
    def __init__(self):
        self.messages_sent = 0
        self.messages_received = 0
        self.bytes_transferred = 0
        self.lock = threading.Lock()
        self.message_history = deque(maxlen=100)
        
    def record_message(self, sender, receiver, size):
        with self.lock:
            self.messages_sent += 1
            self.messages_received += 1
            self.bytes_transferred += size
            self.message_history.append({
                'time': time.time(),
                'sender': sender,
                'receiver': receiver,
                'size': size
            })


class ECUNetwork:
    def __init__(self):
        self.ecus = {}
        self.lock = threading.Lock()
        self.stats = NetworkStats()
        self.latency_ms = 2  # Simulated network latency

    def register(self, ecu):
        with self.lock:
            self.ecus[ecu.name] = ecu
            ecu.network = self

    def send(self, sender, receiver, data):
        with self.lock:
            if receiver in self.ecus:
                msg_size = len(str(data))
                self.stats.record_message(sender, receiver, msg_size)
                
                def delayed_send():
                    time.sleep(self.latency_ms / 1000.0)
                    self.ecus[receiver].receive_message(sender, data)
                
                threading.Thread(target=delayed_send, daemon=True).start()
            else:
                if sender in self.ecus and hasattr(self.ecus[sender], "update_queue"):
                    self.ecus[sender].update_queue.put(("log", sender,
                                                       f"[WARN] Network: target '{receiver}' not found"))

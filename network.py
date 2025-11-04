# network.py
import threading

class ECUNetwork:
    def __init__(self):
        self.ecus = {}
        self.lock = threading.Lock()

    def register(self, ecu):
        """Register ECU with the network"""
        with self.lock:
            self.ecus[ecu.name] = ecu

    def send(self, sender, receiver, data):
        """Deliver message from sender to receiver"""
        with self.lock:
            if receiver in self.ecus:
                self.ecus[receiver].receive_message(sender, data)
            else:
                print(f"[Network] ECU '{receiver}' not found!")

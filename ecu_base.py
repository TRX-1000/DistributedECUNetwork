# ecu_base.py
import threading
import time
import random
from queue import Queue
from datetime import datetime


class BaseECU(threading.Thread):
    def __init__(self, name, network, update_interval=1.0):
        super().__init__()
        self.name = name
        self.network = network  # reference to network controller
        self.update_interval = update_interval
        self.running = True
        self.data = {}
        self.received_messages = Queue()

    def log(self, msg):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        print(f"{timestamp} {self.name}: {msg}")

    def send_message(self, target, data):
        """Send message to another ECU via the network"""
        self.network.send(self.name, target, data)

    def receive_message(self, src, data):
        """Handle incoming data (to be overridden by subclasses)"""
        self.received_messages.put((src, data))

    def stop(self):
        self.running = False

    def run(self):
        """Main loop for the ECU thread"""
        while self.running:
            self.process_incoming()
            self.generate_data()
            time.sleep(self.update_interval)

    def process_incoming(self):
        """Called each cycle to check new messages"""
        while not self.received_messages.empty():
            src, data = self.received_messages.get()
            self.handle_message(src, data)

    def generate_data(self):
        """Placeholder — subclasses override this"""
        pass

    def handle_message(self, src, data):
        """Placeholder — subclasses override this"""
        pass

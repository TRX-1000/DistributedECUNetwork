# ecus/engine_ecu.py
from ecu_base import BaseECU
import random

class EngineECU(BaseECU):
    def __init__(self, network):
        super().__init__("EngineECU", network, update_interval=1.0)
        self.rpm = 0
        self.temp = 90
        self.power_output = 0

    def generate_data(self):
        # Randomize some engine parameters
        self.rpm = random.randint(700, 7500)
        self.temp = random.uniform(80, 120)
        self.power_output = round(self.rpm * 0.1, 1)

        # Broadcast to others
        self.send_message("FuelECU", {"rpm": self.rpm, "temp": self.temp})
        self.log(f"Sent RPM={self.rpm}, Temp={self.temp}")

    def handle_message(self, src, data):
        # Handle incoming data from other ECUs
        if src == "FuelECU":
            fuel_ratio = data.get("fuel_ratio", None)
            if fuel_ratio:
                self.log(f"Received fuel ratio = {fuel_ratio}")

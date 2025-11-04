# ecus/fuel_ecu.py
from ecu_base import BaseECU
import random

class FuelECU(BaseECU):
    def __init__(self, network):
        super().__init__("FuelECU", network, update_interval=1.2)
        self.fuel_ratio = 14.7  # default stoichiometric
        self.last_rpm = 0

    def generate_data(self):
        # adjust fuel ratio based on last known engine RPM
        if self.last_rpm > 5000:
            self.fuel_ratio = 12.5
        elif self.last_rpm < 2000:
            self.fuel_ratio = 15.2
        else:
            self.fuel_ratio = 14.7 + random.uniform(-0.3, 0.3)

        # send data back to engine
        self.send_message("EngineECU", {"fuel_ratio": self.fuel_ratio})
        self.log(f"Sent fuel ratio = {self.fuel_ratio:.2f}")

    def handle_message(self, src, data):
        if src == "EngineECU":
            rpm = data.get("rpm", 0)
            self.last_rpm = rpm
            self.log(f"Received RPM = {rpm}")

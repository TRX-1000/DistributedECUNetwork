################################################################################
#                                                                              #
#                         📁 engine_ecu.py                                     #
#                       Engine Control Unit Module                             #
#                                                                              #
################################################################################

import random
import math
from ecu_base import BaseECU, FAST, MEDIUM, SLOW, now_s, clamp


class EngineECU(BaseECU):
    THRESHOLDS = {
        "RPM": 8000,
        "Temperature": 105.0,
        "IntakePressure": 1.6,
        "BoostPressure": 1.4,
        "O2": 1.2,
        "BatteryVoltage": 14.8,
        "OilLevel": 15.0,
        "OilPressure": 80.0,
        "ThrottlePosition": 100.0,
        "MAFRate": 250.0
    }

    def __init__(self, name, update_queue, main_tick=0.1):
        super().__init__(name, update_queue, main_tick)
        self.random = random.Random()
        
        # Core parameters
        self.rpm = 900
        self.throttle = 0.0
        self.temp = 80.0
        self.oil_level = 100.0
        self.oil_pressure = 30.0
        self.intake_pressure = 1.0
        self.boost = 0.0
        self.o2 = 1.0
        self.batt = 12.6
        self.crank = 0.0
        self.cam = 0.0
        self.maf_rate = 15.0
        self.load = 0.0
        
        self.current_gear = 1
        self.target_gear = 1
        self.gear_request_rpm = 0
        
        self.throttle_target = 0.0
        self.rpm_target = self.rpm
        
        self.last_update = {}
        t = now_s()
        keys = ["RPM", "ThrottlePosition", "Temperature", "OilLevel", "OilPressure",
                "IntakePressure", "BoostPressure", "O2", "BatteryVoltage", 
                "CrankshaftPos", "CamshaftPos", "MAFRate", "Load"]
        for k in keys:
            self.last_update[k] = t - 10.0

    def generate_data(self):
        t = now_s()
        
        # Update throttle target periodically
        if t - self.last_update.get("ThrottleTarget", 0) > 1.5:
            if self.random.random() < 0.25:
                self.throttle_target = float(self.random.choice([0, 5, 10, 25, 40, 60, 80, 100]))
            else:
                self.throttle_target = clamp(
                    self.throttle_target + self.random.uniform(-5, 5), 0.0, 100.0
                )
            self.last_update["ThrottleTarget"] = t

        # FAST updates
        if t - self.last_update["ThrottlePosition"] >= FAST:
            self.throttle += (self.throttle_target - self.throttle) * 0.20 + self.random.uniform(-0.4, 0.4)
            self.throttle = clamp(self.throttle, 0.0, 100.0)
            
            self.load = (self.throttle / 100.0) * (self.rpm / 9000.0) * 100.0
            
            base_idle = 900
            gear_ratio = 1.0 + (self.current_gear - 1) * 0.7
            self.rpm_target = int(base_idle + self.throttle * (80.0 / gear_ratio))
            
            self.rpm += (self.rpm_target - self.rpm) * 0.15 + self.random.uniform(-100, 100)
            self.rpm = int(clamp(self.rpm, 600, 9500))
            
            deg_per_sec = (self.rpm / 60.0) * 360.0
            self.crank = (self.crank + deg_per_sec * FAST) % 360.0
            self.cam = (self.cam + (deg_per_sec * FAST) / 2.0 + self.random.uniform(-3.0, 3.0)) % 360.0
            
            self.last_update["ThrottlePosition"] = t
            self.last_update["RPM"] = t
            self.last_update["CrankshaftPos"] = t
            self.last_update["CamshaftPos"] = t
            self.last_update["Load"] = t

        # MEDIUM updates
        if t - self.last_update["IntakePressure"] >= MEDIUM:
            self.intake_pressure += (1.0 + (self.throttle / 100.0) * 0.9 - self.intake_pressure) * 0.30
            self.intake_pressure += self.random.uniform(-0.04, 0.04)
            self.intake_pressure = round(clamp(self.intake_pressure, 0.5, 2.8), 3)
            
            self.boost = max(0.0, round((self.intake_pressure - 1.0) * (0.8 + self.throttle / 250.0), 3))
            self.boost += self.random.uniform(-0.02, 0.02)
            self.boost = round(clamp(self.boost, 0.0, 2.0), 3)
            
            self.maf_rate = 15.0 + (self.throttle / 100.0) * (self.rpm / 9000.0) * 230.0
            self.maf_rate += self.random.uniform(-5.0, 5.0)
            self.maf_rate = round(clamp(self.maf_rate, 5.0, 300.0), 1)
            
            self.last_update["IntakePressure"] = t
            self.last_update["BoostPressure"] = t
            self.last_update["MAFRate"] = t

        if t - self.last_update["O2"] >= MEDIUM:
            target_o2 = 1.0 + (self.throttle / 500.0)
            self.o2 += (target_o2 - self.o2) * 0.12 + self.random.uniform(-0.04, 0.04)
            self.o2 = round(clamp(self.o2, 0.5, 1.5), 3)
            self.last_update["O2"] = t
            
            if self.o2 > 1.15:
                if self.random.random() < 0.05:
                    self.add_dtc("P0171")

        # SLOW updates
        if t - self.last_update["Temperature"] >= 1.0:
            load_factor = (self.load / 100.0)
            temp_change = (load_factor * 8.0) - ((self.temp - 75.0) * 0.03)
            self.temp += temp_change + self.random.uniform(-0.3, 0.3)
            self.temp = round(clamp(self.temp, 60.0, 135.0), 1)
            self.last_update["Temperature"] = t
            
            if self.temp > 115.0:
                self.add_dtc("B1342")

        if t - self.last_update["OilPressure"] >= SLOW:
            target_pressure = 20.0 + (self.rpm / 9000.0) * 60.0
            self.oil_pressure += (target_pressure - self.oil_pressure) * 0.20
            self.oil_pressure += self.random.uniform(-2.0, 2.0)
            self.oil_pressure = round(clamp(self.oil_pressure, 5.0, 100.0), 1)
            self.last_update["OilPressure"] = t

        if t - self.last_update["BatteryVoltage"] >= SLOW:
            self.batt = round(12.8 + math.sin(t / 80.0) * 0.3 + self.random.uniform(-0.15, 0.15), 2)
            self.last_update["BatteryVoltage"] = t

        if t - self.last_update["OilLevel"] >= 3.0:
            consumption = 0.002 + (self.load / 100.0) * 0.018
            self.oil_level -= consumption
            self.oil_level = round(clamp(self.oil_level, 0.0, 100.0), 3)
            self.last_update["OilLevel"] = t

        with self.lock:
            data = {
                "RPM": int(self.rpm),
                "Gear": int(self.current_gear),
                "ThrottlePosition": round(self.throttle, 1),
                "Load": round(self.load, 1),
                "Temperature": round(self.temp, 1),
                "OilLevel": round(self.oil_level, 2),
                "OilPressure": round(self.oil_pressure, 1),
                "IntakePressure": self.intake_pressure,
                "BoostPressure": self.boost,
                "O2": self.o2,
                "MAFRate": self.maf_rate,
                "BatteryVoltage": self.batt,
                "CrankshaftPos": round(self.crank, 1),
                "CamshaftPos": round(self.cam, 1),
            }
            self.data = data

        self.update_queue.put(("update", self.name, (data.copy(), [])))
        
        self.send_message("FuelECU", {"ThrottlePosition": round(self.throttle, 1), "RPM": int(self.rpm)})
        self.send_message("TransmissionECU", {"RPM": int(self.rpm), "ThrottlePosition": round(self.throttle, 1), "Load": round(self.load, 1)})
        self.send_message("BrakeECU", {"RPM": int(self.rpm)})

        if self.rpm > 8500:
            self.log(f"[WARN] RPM critical: {self.rpm}")
        if self.temp > 110.0:
            self.log(f"[WARN] Engine overheating: {self.temp}°C")
        if self.oil_level < 10.0:
            self.log(f"[FAULT] Oil critically low: {self.oil_level}%")

    def handle_message(self, src, data):
        if src == "TransmissionECU" and "CurrentGear" in data:
            self.current_gear = int(data["CurrentGear"])
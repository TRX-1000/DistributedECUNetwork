<<<<<<< HEAD
################################################################################
#                                                                              #
#                          📁 fuel_ecu.py                                      #
#                        Fuel Control Unit Module                              #
#                                                                              #
################################################################################

import random
from ecu_base import BaseECU, MEDIUM, SLOW, now_s, clamp


class FuelECU(BaseECU):
    THRESHOLDS = {
        "FuelPressure": 4.0,
        "FuelTemperature": 65.0,
        "FuelLevel": 10.0,
        "InjectorPulseWidth": 5.0,
        "InjectorFlow": 50.0,
        "ThrottlePosition": 100.0,
        "AFRatio": 16.0
    }

    def __init__(self, name, update_queue, cylinders=8, main_tick=0.1):
        super().__init__(name, update_queue, main_tick)
        self.cylinders = cylinders
        self.random = random.Random()
        self.fuel_level = 100.0
        self.current_throttle = 0.0
        self.current_rpm = 900
        self.pressure = 3.5
        self.ftemp = 25.0
        self.af_ratio = 14.7
        self.last_update = {}
        
        t = now_s()
        keys = ["FuelPressure", "FuelTemperature", "FuelLevel", "InjectorFlows", 
                "InjectorPulseWidth", "ThrottlePosition", "AFRatio"]
        for k in keys:
            self.last_update[k] = t - 10.0

    def generate_data(self):
        t = now_s()

        if t - self.last_update["FuelPressure"] >= MEDIUM:
            load_factor = self.current_throttle / 100.0
            target_pressure = 2.8 + load_factor * 2.2 + (self.current_rpm / 9000.0) * 0.5
            self.pressure += (target_pressure - self.pressure) * 0.30 + self.random.uniform(-0.08, 0.08)
            self.pressure = round(clamp(self.pressure, 1.0, 7.0), 2)
            
            self.ftemp += (load_factor * 0.8 - (self.ftemp - 30.0) * 0.03) + self.random.uniform(-0.2, 0.3)
            self.ftemp = round(clamp(self.ftemp, 15.0, 95.0), 1)
            
            self.last_update["FuelPressure"] = t
            self.last_update["FuelTemperature"] = t

        if t - self.last_update["AFRatio"] >= MEDIUM:
            target_af = 14.7 - (self.current_throttle / 100.0) * 0.5
            self.af_ratio += (target_af - self.af_ratio) * 0.15 + self.random.uniform(-0.2, 0.2)
            self.af_ratio = round(clamp(self.af_ratio, 12.0, 16.0), 2)
            self.last_update["AFRatio"] = t
            
            if self.af_ratio > 15.5:
                self.add_dtc("P0171")

        if t - self.last_update["InjectorFlows"] >= MEDIUM:
            base_flow = 8.0 + (self.current_throttle / 100.0) * (self.current_rpm / 9000.0) * 50.0
            flows = []
            for i in range(self.cylinders):
                variation = self.random.uniform(-2.0, 4.0)
                flow = round(clamp(base_flow + variation, 1.0, 80.0), 2)
                flows.append(flow)
            self.last_update["InjectorFlows"] = t
        else:
            flows = [self.random.uniform(8.0, 15.0) for _ in range(self.cylinders)]

        if t - self.last_update["InjectorPulseWidth"] >= MEDIUM:
            avg_flow = sum(flows) / len(flows) if flows else 10.0
            inj_pw = round(clamp(1.2 + (avg_flow / 25.0) + self.random.uniform(-0.3, 0.3), 0.8, 8.0), 2)
            self.last_update["InjectorPulseWidth"] = t
        else:
            inj_pw = round(1.5 + self.random.uniform(0.0, 1.5), 2)

        if t - self.last_update["FuelLevel"] >= 2.5:
            consumption = 0.015 + (self.current_throttle / 100.0) * (self.current_rpm / 9000.0) * 0.04
            self.fuel_level -= consumption
            self.fuel_level = round(clamp(self.fuel_level, 0.0, 100.0), 3)
            self.last_update["FuelLevel"] = t

        data = {
            "FuelPressure": round(self.pressure, 2),
            "FuelTemperature": round(self.ftemp, 1),
            "FuelLevel": round(self.fuel_level, 2),
            "InjectorPulseWidth": inj_pw,
            "AFRatio": self.af_ratio,
            "ThrottlePosition": round(self.current_throttle, 1),
        }
        
        for idx, f in enumerate(flows, start=1):
            data[f"InjectorFlow_Cyl{idx}"] = f

        with self.lock:
            self.data = data

        faults = []
        if self.pressure < 2.5:
            faults.append("FuelPressureLow")
        if self.fuel_level < 5.0:
            faults.append("FuelCriticallyLow")

        self.update_queue.put(("update", self.name, (data.copy(), faults)))

        if self.pressure < 2.6:
            self.log(f"[WARN] Low fuel pressure: {self.pressure} bar")
        if self.fuel_level < 15.0 and self.fuel_level > 14.5:
            self.log(f"[WARN] Fuel level low: {self.fuel_level}%")

    def handle_message(self, src, data):
        if "ThrottlePosition" in data:
            t = float(data.get("ThrottlePosition", self.current_throttle))
            self.current_throttle = (self.current_throttle * 0.6) + (t * 0.4)
        if "RPM" in data:
            self.current_rpm = int(data.get("RPM", self.current_rpm))
=======
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
>>>>>>> 529f573ddde8dfe23913a5af0207dc8513e3241a

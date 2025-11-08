###############################################################################
#                                                                              #
#                      📁 transmission_ecu.py                                  #
#                    Transmission Control Unit Module                          #
#                                                                              #
################################################################################

import random
from ecu_base import BaseECU, FAST, MEDIUM, SLOW, now_s, clamp


class TransmissionECU(BaseECU):
    THRESHOLDS = {
        "TransmissionTemp": 95.0,
        "TorqueConverterSlip": 15.0,
        "TransmissionPressure": 180.0,
        "FluidLevel": 15.0
    }

    def __init__(self, name, update_queue, gear_count=6, main_tick=0.1):
        super().__init__(name, update_queue, main_tick)
        self.random = random.Random()
        self.gear_count = gear_count
        self.current_gear = 1
        self.target_gear = 1
        self.shifting = False
        self.shift_progress = 0.0
        self.shift_cooldown = 0.0
        
        self.trans_temp = 70.0
        self.fluid_level = 100.0
        self.trans_pressure = 120.0
        self.torque_converter_slip = 5.0
        self.line_pressure = 100.0
        
        self.current_rpm = 900
        self.current_throttle = 0.0
        self.current_load = 0.0
        
        self.last_update = {}
        t = now_s()
        keys = ["Gear", "TransmissionTemp", "FluidLevel", "TransmissionPressure", 
                "TorqueConverterSlip", "LinePressure"]
        for k in keys:
            self.last_update[k] = t - 10.0

    def generate_data(self):
        t = now_s()

        # FAST: Gear shifting logic
        if t - self.last_update["Gear"] >= FAST:
            if not self.shifting:
                self._evaluate_shift(t)
            else:
                self._process_shift(t)
            self.last_update["Gear"] = t

        # MEDIUM: Transmission temperature
        if t - self.last_update["TransmissionTemp"] >= 1.0:
            heat_gen = (self.current_load / 100.0) * 3.0
            if self.shifting:
                heat_gen += 2.0
            cooling = (self.trans_temp - 65.0) * 0.04
            self.trans_temp += heat_gen - cooling + self.random.uniform(-0.3, 0.3)
            self.trans_temp = round(clamp(self.trans_temp, 60.0, 120.0), 1)
            self.last_update["TransmissionTemp"] = t
            
            if self.trans_temp > 105.0:
                self.add_dtc("P0700")

        # MEDIUM: Pressures
        if t - self.last_update["TransmissionPressure"] >= MEDIUM:
            # Line pressure increases with throttle and gear
            target_pressure = 80.0 + (self.current_throttle / 100.0) * 60.0 + self.current_gear * 8.0
            self.line_pressure += (target_pressure - self.line_pressure) * 0.25
            self.line_pressure += self.random.uniform(-3.0, 3.0)
            self.line_pressure = round(clamp(self.line_pressure, 60.0, 200.0), 1)
            
            self.trans_pressure = self.line_pressure + self.random.uniform(-5.0, 5.0)
            self.trans_pressure = round(clamp(self.trans_pressure, 70.0, 220.0), 1)
            
            self.last_update["TransmissionPressure"] = t
            self.last_update["LinePressure"] = t

        # MEDIUM: Torque converter slip
        if t - self.last_update["TorqueConverterSlip"] >= MEDIUM:
            # Slip is higher at low speeds and under acceleration
            base_slip = 8.0 / (1.0 + self.current_rpm / 2000.0)
            load_slip = (self.current_throttle / 100.0) * 5.0
            self.torque_converter_slip = base_slip + load_slip + self.random.uniform(-1.0, 1.0)
            self.torque_converter_slip = round(clamp(self.torque_converter_slip, 0.0, 25.0), 1)
            self.last_update["TorqueConverterSlip"] = t

        # SLOW: Fluid level
        if t - self.last_update["FluidLevel"] >= 3.0:
            consumption = 0.001 + (self.trans_temp / 120.0) * 0.005
            self.fluid_level -= consumption
            self.fluid_level = round(clamp(self.fluid_level, 0.0, 100.0), 3)
            self.last_update["FluidLevel"] = t

        # Build data
        data = {
            "CurrentGear": int(self.current_gear),
            "TargetGear": int(self.target_gear),
            "Shifting": self.shifting,
            "ShiftProgress": round(self.shift_progress * 100, 1),
            "TransmissionTemp": self.trans_temp,
            "FluidLevel": round(self.fluid_level, 2),
            "TransmissionPressure": self.trans_pressure,
            "LinePressure": self.line_pressure,
            "TorqueConverterSlip": self.torque_converter_slip,
        }

        with self.lock:
            self.data = data

        self.update_queue.put(("update", self.name, (data.copy(), [])))
        
        # Send current gear to EngineECU
        self.send_message("EngineECU", {"CurrentGear": int(self.current_gear)})

        if self.trans_temp > 100.0:
            self.log(f"[WARN] Transmission overheating: {self.trans_temp}°C")

    def _evaluate_shift(self, t):
        if t < self.shift_cooldown:
            return
            
        shift_up_rpms = {1: 3800, 2: 4200, 3: 4800, 4: 5200, 5: 5600}
        shift_down_rpms = {2: 1800, 3: 2000, 4: 2200, 5: 2400, 6: 2600}
        
        # Upshift
        if self.current_gear < self.gear_count and self.current_throttle > 15:
            threshold = shift_up_rpms.get(self.current_gear, 5500)
            if self.current_rpm > threshold:
                self.target_gear = self.current_gear + 1
                self.shifting = True
                self.shift_progress = 0.0
                self.shift_cooldown = t + 0.8
                self.log(f"[INFO] Initiating upshift {self.current_gear} → {self.target_gear}")
                
        # Downshift
        elif self.current_gear > 1:
            threshold = shift_down_rpms.get(self.current_gear, 2000)
            if self.current_rpm < threshold:
                self.target_gear = self.current_gear - 1
                self.shifting = True
                self.shift_progress = 0.0
                self.shift_cooldown = t + 0.7
                self.log(f"[INFO] Initiating downshift {self.current_gear} → {self.target_gear}")

    def _process_shift(self, t):
        self.shift_progress += 0.12
        if self.shift_progress >= 1.0:
            self.current_gear = self.target_gear
            self.shifting = False
            self.shift_progress = 0.0
            self.log(f"[INFO] Shift complete - now in gear {self.current_gear}")

    def handle_message(self, src, data):
        if "RPM" in data:
            self.current_rpm = int(data.get("RPM", self.current_rpm))
        if "ThrottlePosition" in data:
            self.current_throttle = float(data.get("ThrottlePosition", self.current_throttle))
        if "Load" in data:
            self.current_load = float(data.get("Load", self.current_load))
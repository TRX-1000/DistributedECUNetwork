import random
from ecu_base import BaseECU, FAST, MEDIUM, SLOW, now_s, clamp


class BrakeECU(BaseECU):
    THRESHOLDS = {
        "BrakePressure": 150.0,
        "BrakeTemp_Front": 400.0,
        "BrakeTemp_Rear": 350.0,
        "BrakePadThickness": 25.0,
        "BrakeFluidLevel": 20.0,
    }

    def __init__(self, name, update_queue, main_tick=0.1):
        super().__init__(name, update_queue, main_tick)
        self.random = random.Random()
        
        self.brake_pressure = 0.0
        self.brake_applied = False
        self.brake_force = 0.0
        
        self.brake_temp_fl = 80.0  # Front left
        self.brake_temp_fr = 80.0  # Front right
        self.brake_temp_rl = 70.0  # Rear left
        self.brake_temp_rr = 70.0  # Rear right
        
        self.pad_thickness_front = 100.0
        self.pad_thickness_rear = 100.0
        self.fluid_level = 100.0
        
        self.abs_active = False
        self.abs_cycle_count = 0
        
        self.current_rpm = 900
        
        self.last_update = {}
        self.last_brake_apply = 0.0
        t = now_s()
        keys = ["BrakePressure", "BrakeTemps", "PadThickness", "FluidLevel", "ABS"]
        for k in keys:
            self.last_update[k] = t - 10.0

    def generate_data(self):
        t = now_s()

        # FAST: Brake application simulation
        if t - self.last_update["BrakePressure"] >= FAST:
            # Randomly apply brakes
            if not self.brake_applied and self.random.random() < 0.02:
                self.brake_applied = True
                self.last_brake_apply = t
                self.brake_force = self.random.uniform(20.0, 90.0)
                self.log(f"[INFO] Brakes applied ({self.brake_force:.1f}%)")
            elif self.brake_applied and t - self.last_brake_apply > self.random.uniform(1.5, 4.0):
                self.brake_applied = False
                self.brake_force = 0.0
                self.log(f"[INFO] Brakes released")
            
            # Brake pressure follows brake force
            target_pressure = self.brake_force * 2.0  # 0-180 bar
            self.brake_pressure += (target_pressure - self.brake_pressure) * 0.35
            self.brake_pressure = round(clamp(self.brake_pressure, 0.0, 200.0), 1)
            
            self.last_update["BrakePressure"] = t

        # FAST: ABS simulation
        if t - self.last_update["ABS"] >= FAST:
            # ABS activates during hard braking
            if self.brake_applied and self.brake_force > 70.0 and self.current_rpm > 2000:
                if self.random.random() < 0.3:
                    self.abs_active = True
                    self.abs_cycle_count += 1
                else:
                    self.abs_active = False
            else:
                self.abs_active = False
            
            self.last_update["ABS"] = t

        # MEDIUM: Brake temperatures
        if t - self.last_update["BrakeTemps"] >= MEDIUM:
            # Heat generation from braking (front biased 60/40)
            heat_gen = (self.brake_force / 100.0) * 8.0            
            # Front brakes
            self.brake_temp_fl += heat_gen * 0.6 - (self.brake_temp_fl - 70.0) * 0.15
            self.brake_temp_fl += self.random.uniform(-1.0, 1.0)
            self.brake_temp_fl = round(clamp(self.brake_temp_fl, 60.0, 600.0), 1)

            self.brake_temp_fr += heat_gen * 0.6 - (self.brake_temp_fr - 70.0) * 0.15
            self.brake_temp_fr += self.random.uniform(-1.0, 1.0)
            self.brake_temp_fr = round(clamp(self.brake_temp_fr, 60.0, 600.0), 1)

            # Rear brakes
            self.brake_temp_rl += heat_gen * 0.4 - (self.brake_temp_rl - 70.0) * 0.15
            self.brake_temp_rl += self.random.uniform(-0.5, 0.5)
            self.brake_temp_rl = round(clamp(self.brake_temp_rl, 60.0, 500.0), 1)

            self.brake_temp_rr += heat_gen * 0.4 - (self.brake_temp_rr - 70.0) * 0.15
            self.brake_temp_rr += self.random.uniform(-0.5, 0.5)
            self.brake_temp_rr = round(clamp(self.brake_temp_rr, 60.0, 500.0), 1)
            
            self.last_update["BrakeTemps"] = t
            
            # Check for overheating
            if max(self.brake_temp_fl, self.brake_temp_fr) > 450.0:
                self.add_dtc("C1201")

        # SLOW: Pad wear
        if t - self.last_update["PadThickness"] >= 2.0:
            if self.brake_applied:
                wear_front = (self.brake_force / 100.0) * 0.008
                wear_rear = (self.brake_force / 100.0) * 0.005
                self.pad_thickness_front -= wear_front
                self.pad_thickness_rear -= wear_rear
            
            self.pad_thickness_front = round(clamp(self.pad_thickness_front, 0.0, 100.0), 2)
            self.pad_thickness_rear = round(clamp(self.pad_thickness_rear, 0.0, 100.0), 2)
            self.last_update["PadThickness"] = t

        # SLOW: Fluid level
        if t - self.last_update["FluidLevel"] >= 3.0:
            consumption = 0.001
            self.fluid_level -= consumption
            self.fluid_level = round(clamp(self.fluid_level, 0.0, 100.0), 3)
            self.last_update["FluidLevel"] = t

        # Build data
        data = {
            "BrakePressure": self.brake_pressure,
            "BrakeForce": round(self.brake_force, 1),
            "BrakeTemp_FL": self.brake_temp_fl,
            "BrakeTemp_FR": self.brake_temp_fr,
            "BrakeTemp_RL": self.brake_temp_rl,
            "BrakeTemp_RR": self.brake_temp_rr,
            "PadThickness_Front": self.pad_thickness_front,
            "PadThickness_Rear": self.pad_thickness_rear,
            "FluidLevel": round(self.fluid_level, 2),
            "ABS_Active": self.abs_active,
            "ABS_Cycles": self.abs_cycle_count,
        }

        with self.lock:
            self.data = data

        self.update_queue.put(("update", self.name, (data.copy(), self.dtc_codes.copy())))

        # Warnings
        if max(self.brake_temp_fl, self.brake_temp_fr) > 420.0:
            self.log(f"[WARN] Front brake overheating: {max(self.brake_temp_fl, self.brake_temp_fr):.1f}°C")
        if self.pad_thickness_front < 30.0:
            self.log(f"[WARN] Front brake pads worn: {self.pad_thickness_front:.1f}%")

    def handle_message(self, src, data):
        if "RPM" in data:
            self.current_rpm = int(data.get("RPM", self.current_rpm))
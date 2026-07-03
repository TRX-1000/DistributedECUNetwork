import sys
from queue import Queue
from PyQt5.QtWidgets import QApplication
from network import ECUNetwork
from gui_monitor_qt import ECUNetworkMonitor
from ecus.engine_ecu import EngineECU
from ecus.fuel_ecu import FuelECU
from ecus.brake_ecu import BrakeECU
from ecus.transmission_ecu import TransmissionECU

def main():
    update_queue = Queue()
    network = ECUNetwork()

    # Instantiate ECUs
    engine = EngineECU("EngineECU", update_queue, main_tick=0.1)
    fuel = FuelECU("FuelECU", update_queue, cylinders=6, main_tick=0.1)
    transmission = TransmissionECU("TransmissionECU", update_queue, gear_count=6, main_tick=0.1)
    brake = BrakeECU("BrakeECU", update_queue, main_tick=0.1)

    # Register on network
    network.register(engine)
    network.register(fuel)
    network.register(transmission)
    network.register(brake)

    # Start ECU threads
    engine.start()
    fuel.start()
    transmission.start()
    brake.start()

    ecus = {
        "EngineECU": engine,
        "FuelECU": fuel,
        "TransmissionECU": transmission,
        "BrakeECU": brake
    }

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ECUNetworkMonitor(network, update_queue, ecus)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
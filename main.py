################################################################################
#                                                                              #
#                           📁 main.py                                         #
#                         Application Entry Point                              #
#                                                                              #
################################################################################

import sys
from queue import Queue
from PyQt5.QtWidgets import QApplication
from network import ECUNetwork
from ecus.engine_ecu import EngineECU
from ecus.fuel_ecu import FuelECU
from GUI import ECUNetworkMonitor


# Import additional ECUs if you create transmission_ecu.py and brake_ecu.py
# from transmission_ecu import TransmissionECU
# from brake_ecu import BrakeECU


def main():
    update_queue = Queue()
    network = ECUNetwork()

    # Instantiate ECUs
    engine = EngineECU("EngineECU", update_queue, main_tick=0.1)
    fuel = FuelECU("FuelECU", update_queue, cylinders=8, main_tick=0.1)
    
    # Uncomment when you create these files:
    # transmission = TransmissionECU("TransmissionECU", update_queue, gear_count=6, main_tick=0.1)
    # brake = BrakeECU("BrakeECU", update_queue, main_tick=0.1)

    # Register on network
    network.register(engine)
    network.register(fuel)
    # network.register(transmission)
    # network.register(brake)

    ecus = {
        "EngineECU": engine, 
        "FuelECU": fuel,
        # "TransmissionECU": transmission,
        # "BrakeECU": brake
    }

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ECUNetworkMonitor(network, update_queue, ecus)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
# main.py
import time
from network import ECUNetwork
from ecus.engine_ecu import EngineECU
from ecus.fuel_ecu import FuelECU

def main():
    network = ECUNetwork()

    engine = EngineECU(network)
    fuel = FuelECU(network)

    # Register ECUs with the network
    network.register(engine)
    network.register(fuel)

    # Start threads
    engine.start()
    fuel.start()

    try:
        time.sleep(15)
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        fuel.stop()
        engine.join()
        fuel.join()
        print("\n[System] Simulation ended.")

if __name__ == "__main__":
    main()

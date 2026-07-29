import can
import cantools
import time
import random

CHANNEL = "vcan0"
BUSTYPE = "socketcan"
DBC_FILE = "vehicle.dbc"

def main():
    db = cantools.database.load_file(DBC_FILE)
    message_def = db.get_message_by_name("VEHICLE_STATUS")

    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[dbc publisher] sending VEHICLE_STATUS (id=0x{message_def.frame_id:X}) on {CHANNEL}")

    try:
        while True:
            # Simulate realistic values
            speed = round(random.uniform(0, 120), 2)       # km/h
            rpm = round(random.uniform(800, 6000), 2)      # engine rpm
            battery_temp = round(random.uniform(15, 45), 0)  # degC

            data = message_def.encode({
                "Speed": speed,
                "RPM": rpm,
                "BatteryTemp": battery_temp,
            })

            msg = can.Message(arbitration_id=message_def.frame_id, data=data, is_extended_id=False)
            bus.send(msg)
            print(f"[dbc publisher] sent Speed={speed} km/h RPM={rpm} BatteryTemp={battery_temp}C")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[dbc publisher] stopped")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()

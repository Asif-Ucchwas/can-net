import logging
import os
import sys
import time

import can

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("can_publisher")

CHANNEL = os.environ.get("CAN_CHANNEL", "vcan0")
BUSTYPE = os.environ.get("CAN_BUSTYPE", "socketcan")
SEND_INTERVAL_S = float(os.environ.get("CAN_SEND_INTERVAL_S", "0.5"))


def main():
    try:
        bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    except OSError as e:
        logger.error(
            "Failed to open CAN interface '%s' (bustype=%s): %s. "
            "Is the interface up? Try: sudo ip link set %s up type vcan",
            CHANNEL, BUSTYPE, e, CHANNEL,
        )
        sys.exit(1)

    logger.info("Sending fixed-rate frames on %s", CHANNEL)

    ids = [0x100, 0x200]
    counter = 0

    try:
        while True:
            for arb_id in ids:
                data = [counter % 256, (counter * 2) % 256, 0, 0, 0, 0, 0, 0]
                msg = can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)
                try:
                    bus.send(msg)
                except can.CanError as e:
                    logger.warning("Failed to send frame id=0x%X: %s", arb_id, e)
                    continue
                logger.debug("Sent id=0x%X data=%s", arb_id, data)
            counter += 1
            time.sleep(SEND_INTERVAL_S)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()

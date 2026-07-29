#!/bin/bash
# Recreates the virtual CAN interface after a WSL2/system restart.
# Virtual interfaces don't persist across reboots - run this once per session.
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan 2>/dev/null || echo "vcan0 already exists"
sudo ip link set up vcan0
echo "vcan0 status:"
ip link show vcan0

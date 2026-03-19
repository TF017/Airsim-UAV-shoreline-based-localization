import sys
import pygame
import time
import math

# ====== Add AirSim repo PythonClient path here ======
sys.path.append(r"D:\PC\AirSim\PythonClient")

import airsim

# =========================
# Configuration
# =========================
DEADZONE_ROLL_PITCH = 0.10
DEADZONE_YAW = 0.10
DEADZONE_THROTTLE = 0.10
SMOOTHING = 0.2          # 0 = no smoothing, 1 = very slow response
CONTROL_DT = 0.05       # control loop rate

# =========================
# Deadzone Function (Scaled)
# =========================
def apply_deadzone(value, deadzone):
    if abs(value) < deadzone:
        return 0.0
    return (value - deadzone * math.copysign(1, value)) / (1 - deadzone)

# =========================
# Simple Low-Pass Filter
# =========================
def smooth(current, previous, alpha):
    return previous + alpha * (current - previous)

# =========================
# Initialize AirSim
# =========================
client = airsim.MultirotorClient()
client.confirmConnection()
client.enableApiControl(True)
client.armDisarm(True)
client.takeoffAsync().join()

# =========================
# Initialize Joystick
# =========================
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise RuntimeError("No joystick detected")

joystick = pygame.joystick.Joystick(0)
joystick.init()

print("Controller:", joystick.get_name())
print("Ready for control")

# Previous filtered values (for smoothing)
prev_roll = 0
prev_pitch = 0
prev_yaw = 0
prev_throttle = 0

try:
    while True:
        pygame.event.pump()

        # Raw input (F310 typical mapping in X mode)
        raw_roll = joystick.get_axis(0)
        raw_pitch = -joystick.get_axis(1)
        raw_yaw = joystick.get_axis(3)
        raw_throttle = -joystick.get_axis(4)

        # Apply deadzones
        roll = apply_deadzone(raw_roll, DEADZONE_ROLL_PITCH)
        pitch = apply_deadzone(raw_pitch, DEADZONE_ROLL_PITCH)
        yaw = apply_deadzone(raw_yaw, DEADZONE_YAW)
        throttle = apply_deadzone(raw_throttle, DEADZONE_THROTTLE)

        # Normalize throttle from [-1,1] to [0,1]
        throttle = (throttle + 1) / 2

        # Apply smoothing
        roll = smooth(roll, prev_roll, SMOOTHING)
        pitch = smooth(pitch, prev_pitch, SMOOTHING)
        yaw = smooth(yaw, prev_yaw, SMOOTHING)
        throttle = smooth(throttle, prev_throttle, SMOOTHING)

        prev_roll = roll
        prev_pitch = pitch
        prev_yaw = yaw
        prev_throttle = throttle

        # Send command to AirSim
        client.moveByRollPitchYawThrottleAsync(
            roll,
            pitch,
            yaw,
            throttle,
            CONTROL_DT
        )

        time.sleep(CONTROL_DT)

except KeyboardInterrupt:
    print("Landing...")
    client.landAsync().join()
    client.armDisarm(False)
    client.enableApiControl(False)
    pygame.quit()

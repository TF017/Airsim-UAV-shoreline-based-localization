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
CONTROL_DT = 0.02          # 50 Hz (smooth + stable)
EXPO = 0.4
DEADZONE = 0.10

#IF FPV mode:
MAX_SPEED = 8.0
MAX_CLIMB_RATE = 3.0
MAX_YAW_RATE = 150.0
#IF Cinematic mode
""" MAX_SPEED = 5.0            # m/s horizontal speed
MAX_CLIMB_RATE = 2.0       # m/s vertical speed
MAX_YAW_RATE = 90.0        # deg/sec """

SMOOTHING = 0.1

# =========================
# Utility Functions
# =========================
def apply_deadzone(value, deadzone):
    if abs(value) < deadzone:
        return 0.0
    return (value - deadzone * math.copysign(1, value)) / (1 - deadzone)

def expo(value, expo_amount):
    return (1 - expo_amount) * value + expo_amount * value**3

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

# Get initial hover altitude
state = client.getMultirotorState()
target_altitude = state.kinematics_estimated.position.z_val

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
print("Auto-Hover Mode Ready")

# Previous smoothed values
prev_vx = 0
prev_vy = 0
prev_vz = 0
prev_yaw = 0

try:
    while True:
        pygame.event.pump()

        # Raw input
        raw_yaw = joystick.get_axis(0)
        raw_throttle = -joystick.get_axis(1)
        raw_roll = joystick.get_axis(2)
        raw_pitch = -joystick.get_axis(3)
        

        # Deadzone
        roll = apply_deadzone(raw_roll, DEADZONE)
        pitch = apply_deadzone(raw_pitch, DEADZONE)
        yaw = apply_deadzone(raw_yaw, DEADZONE)
        throttle = apply_deadzone(raw_throttle, DEADZONE)

        # Expo for smooth center control
        roll = expo(roll, EXPO)
        pitch = expo(pitch, EXPO)
        yaw = expo(yaw, EXPO)
        throttle = expo(throttle, EXPO)

        # Convert to horizontal velocities
        vx = pitch * MAX_SPEED
        vy = roll * MAX_SPEED

        # Vertical velocity (altitude hold logic)
        if abs(throttle) < 0.05:
            vz = 0
        else:
            vz = -throttle * MAX_CLIMB_RATE

        # Yaw rate (degrees/sec for AirSim)
        yaw_rate = yaw * MAX_YAW_RATE

        # Apply smoothing
        vx = smooth(vx, prev_vx, SMOOTHING)
        vy = smooth(vy, prev_vy, SMOOTHING)
        vz = smooth(vz, prev_vz, SMOOTHING)
        yaw_rate = smooth(yaw_rate, prev_yaw, SMOOTHING)

        prev_vx = vx
        prev_vy = vy
        prev_vz = vz
        prev_yaw = yaw_rate

        client.moveByVelocityBodyFrameAsync(
            vx, vy, vz, CONTROL_DT, yaw_mode=airsim.YawMode(is_rate=True, yaw_or_rate=yaw_rate))
        print(round(vx, 3), round(vy, 3), round(vz, 3), round(yaw_rate,3))
        time.sleep(CONTROL_DT)


except KeyboardInterrupt:
    print("Landing...")
    client.landAsync().join()
    client.armDisarm(False)
    client.enableApiControl(False)
    pygame.quit()

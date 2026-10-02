import sys
import pygame
import time
import math
import os
#os.startfile("D:\\Downloads\\Universidade\\ANO2526\\PIC\\Coastline\\Coastline\\WindowsNoEditor\\Coastline.exe")
if sys.platform=='win32':
# ====== Add AirSim repo PythonClient path here ======
    sys.path.append(r"A:\AirSim\PythonClient")
else:
    sys.path.append(r"/mnt/a/AirSim/PythonClient")

import airsim


# =========================
# Configuration
# =========================
CLOCK_SPEED= 1.0
CONTROL_DT = 0.02          # 50 Hz (smooth + stable)
LOG_FREQUENCY = 2 #Frequency to print status in unreal
LOG_TIMER = int(1/(LOG_FREQUENCY*CONTROL_DT))
SIM_DT = CONTROL_DT / CLOCK_SPEED
CAMERA_NAME=''#'front_center' or '0' or ''

WAITING_TIME_BUTTONS = 1.0
N_WAITING_TIME= int(WAITING_TIME_BUTTONS/CONTROL_DT) # Number of CONTROL_DT to allow that button to be pressed again
#This was made because the controller buttons were given multiple signals after pressing 

EXPO = 0.4
DEADZONE = 0.10
DESCENT_RATE = 0.3       # m/s down
TOUCHDOWN_TIME = 0.5     # seconds of stable contact
COUNTER_LIMIT = int(TOUCHDOWN_TIME / CONTROL_DT)

#IF FPV mode:
MAX_SPEED = 20.0
MAX_CLIMB_RATE = 5.0
MAX_YAW_RATE = 25.0
MAX_ACCEL = 25 # m/s² acceleration
BRAKE_DECEL = 20 # m/s² braking force

'''
#IF Sports mode
MAX_SPEED = 8.0
MAX_CLIMB_RATE = 3.0
MAX_YAW_RATE = 75.0
MAX_ACCEL = 15
BRAKE_DECEL = 12
'''

#IF Cinematic mode
""" MAX_SPEED = 5.0            # m/s horizontal speed
MAX_CLIMB_RATE = 2.0       # m/s vertical speed
MAX_YAW_RATE = 45.0        # deg/sec 
MAX_ACCEL = 6
BRAKE_DECEL = 4
"""

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

def quaternion_to_euler(w, x, y, z):
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x**2 + y**2)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    pitch = math.asin(sinp)

    # Yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y**2 + z**2)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll*180/math.pi, pitch*180/math.pi, yaw*180/math.pi


# =========================
# Initialize AirSim
# =========================
#time.sleep(1)
ip="127.0.0.1"
if sys.platform!='win32':
    ip='172.23.0.1'
client = airsim.MultirotorClient(ip)
client.confirmConnection()
client.enableApiControl(True)

'''If you define the pose inside the setting.json you cannot change them afterwards.
 Even with no pose definition coastline.exe fails for some reason. So i define type and dimensions in default settings.
 For now it works.'''
print(client.simGetCameraInfo(CAMERA_NAME, "Drone1", False).pose.orientation)
global Camera_pitch
Camera_pitch=-math.pi/2
pose=airsim.Pose(
    airsim.Vector3r(0, 0, 0),
    airsim.to_quaternion(Camera_pitch, 0, 0)  # yaw rotation
)
print(client.simSetCameraPose(CAMERA_NAME, pose, "Drone1"))
print(client.simGetCameraInfo(CAMERA_NAME, "Drone1", False).pose.orientation)

'''
client.simEnableWeather(True)
client.simSetWeatherParameter(8, 1.0)
client.simSetWeatherParameter(3, 1.0)
client.simSetWeatherParameter(6, .5)
client.simSetTimeOfDay(True, "2018-02-12 22:20:00")
'''

is_flying = False   # because you already take off at start
takeoff_requested = False
landing_requested = False
is_recording = False
last_z = None
touchdown_counter = 0


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

client.simPrintLogMessage("Python Controller: ", "Ready", 2)

# Previous smoothed values
vx=0
vy=0
vz=0
prev_vx = 0
prev_vy = 0
prev_vz = 0
prev_yaw = 0
log_time=0

class Buttons:
    def __init__(self, n=4):
        #waiting list for buttons; if 0 can be read now, otherwise not valid
        #A button; B button; RB button; Dpad button;
        self.values=[0 for i in range(n)]
        self.n=n
    
    def drop_all(self):
        for i, j in enumerate(self.values):
            if j!=0: 
                self.values[i]=j-1

    def setmax(self, i):
        self.values[i]=N_WAITING_TIME
    
    def validate(self, values):
        valid_values=[]
        for i,(j,k) in enumerate(zip(values, self.values)):
            result=int(j!=0 and k==0)*j
            valid_values.append(result)
            if result!=0: self.setmax(i)
        return valid_values

waiting_list_buttons=Buttons(4)

try:
    while True:
        pygame.event.pump()
        start=time.time()
        # Read buttons
        #A button; B button; RB button; Dpad button;
        buttons_pressed= [joystick.get_button(0), joystick.get_button(1), joystick.get_button(5), joystick.get_hat(0)[1]]
        button_takeoff, button_land, button_record_start, hat_camera_pitch = waiting_list_buttons.validate(buttons_pressed)
        
        if hat_camera_pitch !=0: 
            new_pitch=hat_camera_pitch*math.pi/12+Camera_pitch
            if -math.pi/2>new_pitch:
                new_pitch=-math.pi/2
            elif new_pitch>math.pi/2:
                new_pitch=math.pi/2
            if new_pitch!=Camera_pitch:
                CameraPose=airsim.Pose(
                    airsim.Vector3r(0, 0, 0),
                    airsim.to_quaternion(new_pitch, 0, 0)  # yaw rotation
                )
                client.simSetCameraPose(CAMERA_NAME, CameraPose, "Drone1", False)
                Camera_pitch=new_pitch
                client.simPrintLogMessage("Python Controller Camera Pitch: ", str(round(Camera_pitch*180/math.pi, 2)), 1)
                print("New Camera Pitch:", round(Camera_pitch*180/math.pi, 2))

        # =========================
        # RECORD
        # =========================
        if button_record_start and not is_recording:
            client.startRecording()
            #print('Recording...', time.time())
            client.simPrintLogMessage("Python Controller Recording: ", "Started", 1)
            is_recording=True
        elif button_record_start and is_recording:
            client.stopRecording()
            #print('Stop Recording', time.time())
            client.simPrintLogMessage("Python Controller Recording: ", "Stoped", 1)   
            is_recording=False
            

        # =========================
        # TAKEOFF
        # =========================
        if button_takeoff and not takeoff_requested and not is_flying:
            takeoff_requested = True
            print("Takeoff initiated...")
            client.simPrintLogMessage("Python Controller: ", "Takeoff initiated...", 2)
            client.armDisarm(True)
            client.takeoffAsync().join()
            is_flying = True
            client.simPrintLogMessage("Python Controller: ", "Airborne", 2)
            print("Airborne")

        if not button_takeoff:
            takeoff_requested = False

        # =========================
        # LAND
        # =========================
        if button_land and not landing_requested and is_flying:
            landing_requested = True
            print("Landing initiated...", time.time())
            client.simPrintLogMessage("Python Controller: ", "Landing initiated...", 2)
            client.landAsync()   # DO NOT join
            #print(time.time())
            # keep loop running

        
        if landing_requested:
            # Command gentle descent
            client.moveByVelocityBodyFrameAsync(
                0, 0, DESCENT_RATE, CONTROL_DT,
                yaw_mode=airsim.YawMode(is_rate=True, yaw_or_rate=0)
            )

            state = client.getMultirotorState()
            z = state.kinematics_estimated.position.z_val
            vz_real = state.kinematics_estimated.linear_velocity.z_val

            if last_z is not None:
                dz = abs(z - last_z)

                # If altitude barely changes AND vertical velocity small → likely on ground
                if dz < 0.005 and abs(vz_real) < 0.05:
                    touchdown_counter += 1
                else:
                    touchdown_counter = 0

                if touchdown_counter > COUNTER_LIMIT:
                    print("Touchdown detected — disarming")
                    client.simPrintLogMessage("Python Controller: ", "Touchdown detected — disarming", 2)
                    client.landAsync().join()
                    client.armDisarm(False)
                    print(state)
                    landing_requested = False
                    is_flying=False

            last_z = z

        if is_flying and not landing_requested:
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
            # Target velocities from stick
            target_vx = pitch * MAX_SPEED
            target_vy = roll * MAX_SPEED

            # --- Acceleration model ---
            def update_velocity(current, target):
                if abs(target) > 0.01:
                    # accelerate toward target
                    delta = target - current
                    step = MAX_ACCEL * SIM_DT
                    delta = max(-step, min(step, delta))
                    return current + delta
                else:
                    # brake toward zero
                    if abs(current) < 0.05:
                        return 0
                    brake = BRAKE_DECEL * SIM_DT
                    return current - math.copysign(min(abs(current), brake), current)

            vx = update_velocity(prev_vx, target_vx)
            vy = update_velocity(prev_vy, target_vy)


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
            #print(round(vx, 3), round(vy, 3), round(vz, 3), round(yaw_rate,3))

        if log_time==LOG_TIMER:
            log_time=0
            state = client.simGetGroundTruthKinematics()
            roll, pitch, yaw=quaternion_to_euler(state.orientation.w_val, state.orientation.x_val,
                                                 state.orientation.y_val, state.orientation.z_val)
            if is_flying and not landing_requested:
                client.simPrintLogMessage("Command Vx: ", str(round(prev_vx, 2)))
                client.simPrintLogMessage("Command Vy: ", str(round(prev_vy, 2)))
                client.simPrintLogMessage("Command Vz: ", str(round(prev_vz, 2)))
                client.simPrintLogMessage("Command Yaw: ",str(round(prev_yaw, 2)))
            else:
                client.simPrintLogMessage("Command Vx: ", "0.00")
                client.simPrintLogMessage("Command Vy: ", "0.00")
                client.simPrintLogMessage("Command Vz: ", "0.30")
                client.simPrintLogMessage("Command Yaw: ", "0.00")
            client.simPrintLogMessage("X: ", str(round(state.position.x_val, 2)))
            client.simPrintLogMessage("Y: ", str(round(state.position.y_val, 2)))
            client.simPrintLogMessage("Z: ", str(round(-state.position.z_val, 2)))
            client.simPrintLogMessage("Vx: ", str(round(state.linear_velocity.x_val, 2)))
            client.simPrintLogMessage("Vy: ", str(round(state.linear_velocity.y_val, 2)))
            client.simPrintLogMessage("Vz: ", str(round(state.linear_velocity.z_val, 2)))
            client.simPrintLogMessage("Roll: ",str(round(roll, 2)))
            client.simPrintLogMessage("Pitch: ",str(round(pitch, 2)))
            client.simPrintLogMessage("Yaw: ",str(round(yaw, 2)))
            gps=client.getMultirotorState().gps_location
            client.simPrintLogMessage("Lat: ",str(round(gps.latitude, 5)))
            client.simPrintLogMessage("Lon: ",str(round(gps.longitude, 5)))
            client.simPrintLogMessage("Alt: ",str(round(gps.altitude, 5)))
        log_time+=1    
        waiting_list_buttons.drop_all()
        #print('End:', time.time()-start)
        time.sleep(CONTROL_DT)


except KeyboardInterrupt:
    print("Landing...")
    client.landAsync().join()
    client.armDisarm(False)
    client.enableApiControl(False)
    pygame.quit()

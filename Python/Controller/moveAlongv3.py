from fastkml import KML, Placemark, Point
from fastkml.utils import find, find_all
import winsound
import sys
import math
import time
import subprocess
import coordinate_system as cs
import json
if sys.platform=='win32':
# ====== Add AirSim repo PythonClient path here ======
    sys.path.append(r"A:\AirSim\PythonClient")
else:
    sys.path.append(r"/mnt/a/AirSim/PythonClient")

import airsim

KML_FILE="zambujeira_north.kml"
VELOCITY=20
ALTITUDE=300.0 #REFERENCE HEIGHT IS ADDED AFTERWARDS
CAMERA_NAME=''#'front_center' or '0' or ''
CAMERA_PITCH_ANGLE=-10.0 #-50.0; -90.0; -78.0 is actual nadir
TIMEOUT=100000
NED=False

print(F'Pitch Angle: {CAMERA_PITCH_ANGLE:.2f}')

#prog = subprocess.Popen([EXECUTABLE])
#time.sleep(15)#Give time for the executable to build the environment properly

k = KML.parse(KML_FILE)

points=[]
placemarks = list(find_all(k, of_type=Point))
for p in placemarks:
    points.append([p.geometry.y, p.geometry.x]) #[lat, long]

def equal(x, y):
    r=abs(x-y)
    if r>0.01: return r
    return True


# =========================
# Initialize AirSim
# =========================
ip="127.0.0.1"
if sys.platform!='win32':
    ip='172.23.0.1'
client = airsim.MultirotorClient(ip)
client.confirmConnection()
client.enableApiControl(True)

client.simPause(True)
settings=json.loads(client.getSettingsString())
LAT=settings['OriginGeopoint']['Latitude']
LON=settings['OriginGeopoint']['Longitude']
HEIGHT=settings['OriginGeopoint']['Altitude']
ALTITUDE+=HEIGHT

airsim2ecef=None
if NED:
    airsim2ecef=cs.AIRSIM2ECEF([LON, LAT, HEIGHT])
else:
    airsim2ecef=cs.AIRSIM2ECEF_ESD([LON, LAT, HEIGHT])

points_in_esd=[]
for lat, lon in points:
    e,s,d=airsim2ecef.invertfromgeo([lon, lat, ALTITUDE])
    print(lat, lon, ALTITUDE, e,s,d)
    points_in_esd.append(airsim.Vector3r(e,s,d))

drone1_pose=client.simGetVehiclePose(vehicle_name='Drone1')
#print("Drone1 Pose:",drone1_pose)
#camera_inicial_pose=client.simGetCameraInfo(CAMERA_NAME, "Drone1", False).pose
camera_pitch=CAMERA_PITCH_ANGLE*math.pi/180 # 10º below horizont
pose=airsim.Pose(
    airsim.Vector3r(0, 0, 0), #For some unknowned reason it adds past pose to this new one, so i leave it empty
    airsim.to_quaternion(camera_pitch, 0, 0)  # pitch rotation
)
client.simSetCameraPose(CAMERA_NAME, pose, "Drone1")
camera_final_pose=client.simGetCameraInfo(CAMERA_NAME, "Drone1", False).pose
print('Goal Pose achieve:')
print("\tZ:", equal(drone1_pose.position.z_val,camera_final_pose.position.z_val)) 
print("\tY:", equal(drone1_pose.position.y_val,camera_final_pose.position.y_val))
print("\tX:", equal(drone1_pose.position.x_val+0.46,camera_final_pose.position.x_val), equal(drone1_pose.position.x_val-0.46,camera_final_pose.position.x_val))
pitch, roll, yaw=airsim.to_eularian_angles(camera_final_pose.orientation)#In radians
print("Goal Camera Pitch Angle:")
print("\tPitch:", equal(camera_pitch, pitch)) 
print("\tRoll:", equal(roll, 0.0))
print("\tYaw:", equal(yaw,0.0), equal(yaw,math.pi))
client.simPause(False)
print("GOING TO ORIGIN POINT")
client.moveToPositionAsync(0, 0, -10, VELOCITY, TIMEOUT, airsim.DrivetrainType.ForwardOnly, airsim.YawMode(False,0), 20, 2).join()
print("GOING TO THE STARTING POSITION")
client.moveToPositionAsync(points_in_esd[0].x_val, points_in_esd[0].y_val, points_in_esd[0].z_val, VELOCITY, TIMEOUT, airsim.DrivetrainType.ForwardOnly, airsim.YawMode(False,0), 20, 2).join()
print('STARTING NOW')
action=client.moveOnPathAsync(points_in_esd[1:],
                        VELOCITY, TIMEOUT,
                        airsim.DrivetrainType.ForwardOnly, airsim.YawMode(False,0), 40, 2)
client.startRecording()
while not action._set_flag:
    state = client.simGetGroundTruthKinematics()
    pitch, roll, yaw=airsim.utils.to_eularian_angles(state.orientation)
    client.simPrintLogMessage("X: ", str(round(state.position.x_val, 2)))
    client.simPrintLogMessage("Y: ", str(round(state.position.y_val, 2)))
    client.simPrintLogMessage("Z: ", str(round(-state.position.z_val, 2)))
    client.simPrintLogMessage("Vx: ", str(round(state.linear_velocity.x_val, 2)))
    client.simPrintLogMessage("Vy: ", str(round(state.linear_velocity.y_val, 2)))
    client.simPrintLogMessage("Vz: ", str(round(state.linear_velocity.z_val, 2)))
    client.simPrintLogMessage("Roll: ",str(round(roll*180/math.pi, 1)))
    client.simPrintLogMessage("Pitch: ",str(round(pitch*180/math.pi, 1)))
    client.simPrintLogMessage("Yaw: ",str(round(yaw*180/math.pi, 1)))
    #gps=client.getMultirotorState().gps_location AIRSIM GPS NOW IS COMPLETE TRASH
    lon, lat, alt=airsim2ecef.convert2geo([state.position.x_val, state.position.y_val, state.position.z_val])
    client.simPrintLogMessage("Lon: ",str(round(lon, 5)))
    client.simPrintLogMessage("Lat: ",str(round(lat, 5)))
    client.simPrintLogMessage("Alt: ",str(round(alt, 5)))
    time.sleep(1)
    
action.join()
client.stopRecording()
client.landAsync().join()
client.armDisarm(False)
client.enableApiControl(False)
duration = 10000  # milliseconds
freq = 400  # Hz
winsound.Beep(freq, duration)

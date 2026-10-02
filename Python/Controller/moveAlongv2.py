from fastkml import KML, Placemark, Point
from fastkml.utils import find, find_all
import winsound
import sys
import math
import time
import subprocess
if sys.platform=='win32':
# ====== Add AirSim repo PythonClient path here ======
    sys.path.append(r"A:\AirSim\PythonClient")
else:
    sys.path.append(r"/mnt/a/AirSim/PythonClient")

import airsim


KML_FILE="Zambujeira_north_50m_from_shore.kml"
VELOCITY=20
ALTITUDE=250.0+49.0
CAMERA_NAME=''#'front_center' or '0' or ''
CAMERA_PITCH_ANGLE=-25.0 #-50.0; -90.0;
EXECUTABLE=r'D:\UnrealProjects\Lagoa_de_Albufeira\WindowsNoEditor\Lagoa_de_Albufeira.exe'

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

client.moveToGPSAsync(points[0][0], points[0][1], ALTITUDE, VELOCITY).join()

L=len(points);i=1
client.startRecording()
for lat, lon in points[1:]:
    print(lat, lon, i, 'of', L)
    client.simPrintLogMessage("Moving to ", str(round(lat, 5))+" "+str(round(lon,5)))
    client.simPrintLogMessage("Step ", str(i)+" of "+str(L))
    movingAsync=client.moveToGPSAsync(lat, lon, ALTITUDE, VELOCITY)
    #movingAsync.attach_callback(somefunction)
    #print(client.simGetCameraInfo(CAMERA_NAME, "Drone1", False))
    movingAsync.join()
    print(lat, lon, i, 'of',L,'joined')
    client.simPrintLogMessage("At ", str(round(lat, 5))+" "+str(round(lon,5)))
    state = client.simGetGroundTruthKinematics()
    gps=client.getMultirotorState().gps_location
    client.simPrintLogMessage("Lon: ",str(round(gps.longitude, 5)))
    client.simPrintLogMessage("Lat: ",str(round(gps.latitude, 5)))
    client.simPrintLogMessage("Alt: ",str(round(gps.altitude, 5)))
    i+=1;    
client.stopRecording()
client.landAsync().join()
client.armDisarm(False)
client.enableApiControl(False)
duration = 10000  # milliseconds
freq = 400  # Hz
winsound.Beep(freq, duration)

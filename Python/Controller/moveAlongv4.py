from fastkml import KML, Placemark, Point
from fastkml.utils import find, find_all
import winsound
import sys
import math
import time
import subprocess
import coordinate_system as cs
import json
import pygetwindow as gw
import pyautogui
import os
import shutil
import json


VELOCITY=20
CAMERA_NAME=''#'front_center' or '0' or ''
TIMEOUT=100000
DATA_PATH=r'D:\Thesis_Data'
PLACE='Sesimbra'
SYSTEM='ESD'

def parseKML(kml_file):
    k = KML.parse(kml_file)
    points=[]
    placemarks = list(find_all(k, of_type=Point))
    for p in placemarks:
        points.append([p.geometry.y, p.geometry.x]) #[lat, long]
    return points

def equal(x, y):
    r=abs(x-y)
    if r>0.01: return r
    return True


# =========================
# Initialize AirSim
# =========================
if sys.platform=='win32':
# ====== Add AirSim repo PythonClient path here ======
    sys.path.append(r"A:\AirSim\PythonClient")
else:
    sys.path.append(r"/mnt/a/AirSim/PythonClient")

import airsim

def start_airsim():
    ip="127.0.0.1"
    if sys.platform!='win32':
        ip='172.23.0.1'
    client = airsim.MultirotorClient(ip)
    client.confirmConnection()
    client.enableApiControl(True)
    return client

def get_airsim_reference_frame(client, altitude, NED=True):
    settings=json.loads(client.getSettingsString())
    LAT=settings['OriginGeopoint']['Latitude']
    LON=settings['OriginGeopoint']['Longitude']
    HEIGHT=settings['OriginGeopoint']['Altitude']
    altitude+=HEIGHT

    airsim2ecef=None
    if NED:
        airsim2ecef=cs.AIRSIM2ECEF([LON, LAT, HEIGHT])
    else:
        airsim2ecef=cs.AIRSIM2ECEF_ESD([LON, LAT, HEIGHT])
    recording_folder=settings["Recording"]["Folder"]
    return airsim2ecef, altitude, recording_folder

def get_points_in_airsim_reference(airsim2ecef, altitude, kml_file):
    points_in_airsim=[]
    points=parseKML(kml_file)
    i=1
    for lat, lon in points:
        e,s,d=airsim2ecef.invertfromgeo([lon, lat, altitude])
        print(f'Point #{i}: {lat:.6f},{lon:.6f},{altitude:.2f}->{e:.2f},{s:.2f},{d:.2f}')
        i+=1
        points_in_airsim.append(airsim.Vector3r(e,s,d))
    return points_in_airsim

def set_camera_pose(client, pitch):
    drone1_pose=client.simGetVehiclePose(vehicle_name='Drone1')
    drone_pitch, drone_roll, drone_yaw=airsim.to_eularian_angles(drone1_pose.orientation)
    #print("Drone1 Pose:",drone1_pose)
    #camera_inicial_pose=client.simGetCameraInfo(CAMERA_NAME, "Drone1", False).pose
    camera_pitch=pitch*math.pi/180 
    pose=airsim.Pose(
        airsim.Vector3r(0, 0, 0), #For some unknowned reason it adds past pose to this new one, so i leave it empty
        airsim.to_quaternion(camera_pitch, 0, 0)  # pitch rotation
    )
    client.simSetCameraPose(CAMERA_NAME, pose, "Drone1")
    camera_final_pose=client.simGetCameraInfo(CAMERA_NAME, "Drone1", False).pose
    print('Goal Pose achieve:')
    print("\tZ:", equal(drone1_pose.position.z_val,camera_final_pose.position.z_val)) 
    print("\tY:", equal(drone1_pose.position.y_val+0.46*math.sin(drone_yaw),camera_final_pose.position.y_val))
    print("\tX:", equal(drone1_pose.position.x_val+0.46*math.cos(drone_yaw),camera_final_pose.position.x_val))
    pitch, roll, yaw=airsim.to_eularian_angles(camera_final_pose.orientation)#In radians
    print("Goal Camera Pitch Angle:")
    print("\tPitch:", equal(camera_pitch, pitch)) 
    print("\tRoll:", equal(roll, drone_roll))
    print("\tYaw:", equal(yaw,drone_yaw))

def move_to_initial_position(client, points_in_airsim):
    print("GOING TO ORIGIN POINT")
    client.moveToPositionAsync(0, 0, -10, VELOCITY, TIMEOUT, airsim.DrivetrainType.ForwardOnly, airsim.YawMode(False,0), 20, 2).join()
    print("GOING TO THE STARTING POSITION")
    altitude_difference=abs(points_in_airsim[0].z_val+10)
    velocity=altitude_difference/30 #make it slow to go to initial position otherwise tilling maybe bad/level of detail blury;
    #make it take 30s to reach the final position
    client.moveToPositionAsync(points_in_airsim[0].x_val, points_in_airsim[0].y_val, points_in_airsim[0].z_val, velocity, TIMEOUT, airsim.DrivetrainType.ForwardOnly, airsim.YawMode(False,0), 20, 2).join()

def start_running_along(client, points_in_airsim, airsim2ecef):
    print('STARTING NOW')
    action=client.moveOnPathAsync(points_in_airsim[1:],
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

def move_recording_to_path(recording_folder, info):
    registed_values=[path for path in os.listdir(DATA_PATH) if path.isnumeric()]
    registed_values.sort(key=int)
    new_folder_name=str(int(registed_values[-1])+1)
    new_folder_full_path=os.path.join(DATA_PATH, new_folder_name)
    new_folder_images_full_path=os.path.join(new_folder_full_path, 'images')
    os.makedirs(new_folder_images_full_path)
    images=os.path.join(recording_folder, 'images')
    images_paths=os.listdir(images)
    for image_path in images_paths:
        shutil.move(os.path.join(images, image_path), os.path.join(new_folder_images_full_path, image_path))
    shutil.move(os.path.join(recording_folder, 'airsim_rec.txt'), os.path.join(new_folder_full_path, 'airsim_rec.txt'))
    info_to_save={"Masked": False, "Route Controller": 4}
    info=info|info_to_save
    with open(os.path.join(new_folder_full_path, 'info.json'), 'w') as file:
        json.dump(info, file)

def play_this_path(info, last_window):
    system, altitude, pitch, kml_file=info['System'], info['Altitude'], info['Camera Angles'][1], info['Route']
    print(f'System:{system}')
    print(f'Altitude:{altitude:.2f}')
    print(f'Pitch:{pitch:.2f}')
    print(f'Route:{kml_file}')
    client=start_airsim()
    client.simPause(True)
    airsim2ecef, altitude, parent_recording_folder=get_airsim_reference_frame(client, altitude, system=='NED')
    paths_in_recording_folder=os.listdir(parent_recording_folder)
    points_in_airsim=get_points_in_airsim_reference(airsim2ecef, altitude, kml_file)
    set_camera_pose(client, pitch)
    client.simPause(False)
    move_to_initial_position(client, points_in_airsim)
    start_running_along(client, points_in_airsim, airsim2ecef)
    paths_in_recording_folder_after=os.listdir(parent_recording_folder)
    recording_folder = (set(paths_in_recording_folder_after) - set(paths_in_recording_folder)).pop()
    sucess, last_window=start_or_stop_play_unreal(0, last_window)
    move_recording_to_path(os.path.join(parent_recording_folder, recording_folder), info)
    os.removedirs(os.path.join(os.path.join(parent_recording_folder, recording_folder), 'images'))
    return last_window

def beep():
    duration = 10000  # milliseconds
    freq = 400  # Hz
    winsound.Beep(freq, duration)

def start_or_stop_play_unreal(start=True, last_window=None):
    windows = gw.getWindowsWithTitle("Unreal Editor")
    if not windows and not last_window:
        print("Unreal Editor window not found")
        return False, None
    if not windows:
        windows=last_window
    
    ue = windows[0]
    ue.activate()      # Bring to foreground
    time.sleep(0.5)    # Give Windows time to focus it
        
    if start:
        pyautogui.hotkey('alt', 'p')  # Start PIE
    else:
        pyautogui.press('esc')        # Stop PIE
    return True, windows    

def main(infos):
    last_window=None
    for info in infos:
        sucess, last_window=start_or_stop_play_unreal(1, last_window)
        if sucess:
            last_window=play_this_path(info, last_window)
            time.sleep(5)
    beep()

if __name__=='__main__':
    #altitude is above Origin Point"
    """ infos=[
        {"Place": PLACE, "System": SYSTEM, "Altitude": 200.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Zambujeira_north_50m_from_shore.kml", 'Obs':None},
        {"Place": PLACE, "System": SYSTEM, "Altitude": 200.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Zambujeira_north_100m_from_shore.kml", 'Obs':None},
        {"Place": PLACE, "System": SYSTEM, "Altitude": 200.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Zambujeira_north_200m_from_shore.kml", 'Obs':None},
        {"Place": PLACE, "System": SYSTEM, "Altitude": 200.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Zambujeira_north_500m_from_shore.kml", 'Obs':None},
        ] """
    """ infos=[
        {"Place": PLACE, "System": SYSTEM, "Altitude": 200.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "aveiro_50m_from_shore.kml", 'Obs':None},
        {"Place": PLACE, "System": SYSTEM, "Altitude": 200.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "aveiro_100m_from_shore.kml", 'Obs':None},
        {"Place": PLACE, "System": SYSTEM, "Altitude": 200.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "aveiro_200m_from_shore.kml", 'Obs':None},
        {"Place": PLACE, "System": SYSTEM, "Altitude": 200.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "aveiro_500m_from_shore.kml", 'Obs':None},
        ] """
    """ infos=[
        {"Place": PLACE, "System": SYSTEM, "Altitude": 225.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Zambujeira_north.kml", 'Obs':None},
        {"Place": PLACE, "System": SYSTEM, "Altitude": 75.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Zambujeira_north.kml", 'Obs':None},
        {"Place": PLACE, "System": SYSTEM, "Altitude": 30.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Zambujeira_north.kml", 'Obs':None},
        ] """
    """ infos=[
           {"Place": PLACE, "System": SYSTEM, "Altitude": 300.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "aveiro.kml", 'Obs':None},
           {"Place": PLACE, "System": SYSTEM, "Altitude": 225.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "aveiro.kml", 'Obs':None},
           {"Place": PLACE, "System": SYSTEM, "Altitude": 75.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "aveiro.kml", 'Obs':None},
           {"Place": PLACE, "System": SYSTEM, "Altitude": 30.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "aveiro.kml", 'Obs':None},
           {"Place": PLACE, "System": SYSTEM, "Altitude": 150.0, "Camera Angles": [0, -78, 0], "Offshore": 0,"Route": "aveiro.kml", 'Obs':None},
           {"Place": PLACE, "System": SYSTEM, "Altitude": 300.0, "Camera Angles": [0, -25, 0], "Offshore": 0,"Route": "aveiro.kml", 'Obs':None},
           ] """
    """ infos=[
            {"Place": PLACE, "System": SYSTEM, "Altitude": 225.0, "Camera Angles": [0, -78, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_shoreline.kml", 'Obs':None},
            {"Place": PLACE, "System": SYSTEM, "Altitude": 150.0, "Camera Angles": [0, -78, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_shoreline.kml", 'Obs':None},
            {"Place": PLACE, "System": SYSTEM, "Altitude": 75.0, "Camera Angles": [0, -78, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_shoreline.kml", 'Obs':None},
            ] """

    infos=[
            {"Place": PLACE, "System": SYSTEM, "Altitude": 30.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
            ]

    """ {"Place": PLACE, "System": SYSTEM, "Altitude": 300.0, "Camera Angles": [0, -78, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                {"Place": PLACE, "System": SYSTEM, "Altitude": 300.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                {"Place": PLACE, "System": SYSTEM, "Altitude": 300.0, "Camera Angles": [0, -25, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                {"Place": PLACE, "System": SYSTEM, "Altitude": 300.0, "Camera Angles": [0, -10, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                {"Place": PLACE, "System": SYSTEM, "Altitude": 225.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                {"Place": PLACE, "System": SYSTEM, "Altitude": 150.0, "Camera Angles": [0, -78, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                {"Place": PLACE, "System": SYSTEM, "Altitude": 150.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                {"Place": PLACE, "System": SYSTEM, "Altitude": 150.0, "Camera Angles": [0, -25, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None}, 
                {"Place": PLACE, "System": SYSTEM, "Altitude": 150.0, "Camera Angles": [0, -10, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                {"Place": PLACE, "System": SYSTEM, "Altitude": 75.0, "Camera Angles": [0, -50, 0], "Offshore": 0,"Route": "Lagoa de Albufeira_new_simplified.kml", 'Obs':None},
                """
   
    main(infos)    
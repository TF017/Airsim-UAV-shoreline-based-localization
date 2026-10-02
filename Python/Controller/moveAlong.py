import sys

#os.startfile("D:\\Downloads\\Universidade\\ANO2526\\PIC\\Coastline\\Coastline\\WindowsNoEditor\\Coastline.exe")
if sys.platform=='win32':
# ====== Add AirSim repo PythonClient path here ======
    sys.path.append(r"A:\AirSim\PythonClient")
else:
    sys.path.append(r"/mnt/a/AirSim/PythonClient")

import airsim
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

client.startRecording()
waypoints = [
    (37.612989, -8.810189, 300),
    (37.612980, -8.810180, 300),
    (37.612970, -8.810170, 300),
    (37.612960, -8.810160, 300),
    (37.62, -8.81, 300),
]

for lat, lon, alt in waypoints:
    client.moveToGPSAsync(lat, lon, alt, 5).join()
client.stopRecording()
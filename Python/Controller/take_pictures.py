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
time.sleep(100)
client.stopRecording()
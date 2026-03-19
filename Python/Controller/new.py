import pygame
import time
import sys

# ====== Add AirSim repo PythonClient path here ======
sys.path.append(r"D:\PC\AirSim\PythonClient")

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No joystick detected")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()

print("Controller detected:", joystick.get_name())
print("Number of axes:", joystick.get_numaxes())
print("Number of buttons:", joystick.get_numbuttons())
print("Number of hats:", joystick.get_numhats())
print("----- Starting Debug -----")

try:
    while True:
        pygame.event.pump()

        # Axes
        axes = []
        for i in range(joystick.get_numaxes()):
            axes.append(round(joystick.get_axis(i), 3))

        # Buttons
        buttons = []
        for i in range(joystick.get_numbuttons()):
            buttons.append(joystick.get_button(i))

        # D-pad (hat)
        hats = []
        for i in range(joystick.get_numhats()):
            hats.append(joystick.get_hat(i))

        print("Axes:", axes)
        print("Buttons:", buttons)
        print("Hats:", hats)
        print("------------")

        time.sleep(1)

except KeyboardInterrupt:
    print("Exiting...")
    pygame.quit()

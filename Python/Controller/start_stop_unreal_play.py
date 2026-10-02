import pygetwindow as gw
import pyautogui
import time

# Find Unreal Editor window
windows = gw.getWindowsWithTitle("Unreal Editor")

if windows:
    ue = windows[0]
    ue.activate()      # Bring to foreground
    time.sleep(0.5)    # Give Windows time to focus it

    pyautogui.hotkey('alt', 'p')  # Start PIE

    time.sleep(5)

    pyautogui.press('esc')        # Stop PIE
else:
    print("Unreal Editor window not found")
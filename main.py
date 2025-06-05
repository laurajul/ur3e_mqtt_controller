import paho.mqtt.client as mqtt
import rtde_control
import socket
import time
import pythonosc.udp_client
import pygame

# ----------------- USER CONFIGURATION -------------------
# Replace these IPs and paths with your own setup
ROBOT_IP = "10.0.0.3"         # UR robot IP address
MQTT_BROKER = "127.0.0.1"     # MQTT broker IP address
DASHBOARD_PORT = 29999        # Default UR dashboard server port

OSC_TARGET_IP = "192.168.0.115"   # IP of the OSC receiver (e.g. QLab)
OSC_PORT = 53000                 # Port for OSC communication

AUDIO_BASE_PATH = "/home/youruser/audio/"  # Change to the path where your audio files are stored

# Map of MQTT scene messages to URScript file names
SCENES = {
    "scene_1": "scene_1.urp",
    "scene_2": "scene_2.urp",
    # Add your scenes here
}

SAFE_HOME_JOINTS = [0.0, -1.57, 1.57, -1.57, -1.57, 0.0]
# --------------------------------------------------------


# -------------------- OSC CLIENT -----------------------
osc_client = pythonosc.udp_client.SimpleUDPClient(OSC_TARGET_IP, OSC_PORT)

# ---------------- ROBOT DASHBOARD COMMAND -------------
def send_dashboard_command(command, host=ROBOT_IP, port=DASHBOARD_PORT):
    """Send a command to the UR robot dashboard server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall((command + '\n').encode())
        response = ""
        while True:
            part = s.recv(1024).decode()
            response += part
            if '\n' in part:
                break
        return response.strip()

def stop():
    print("Stopping robot program.")
    send_dashboard_command("stop")

def pause():
    print("Pausing robot program.")
    send_dashboard_command("pause")

def play():
    print("Resuming robot program.")
    send_dashboard_command("play")

# ---------------- FREEDRIVE MODE -----------------------
def enter_freedrive():
    try:
        rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
        rtde_c.teachMode()
        print("Entered freedrive mode.")
    except Exception as e:
        print(f"Error entering freedrive mode: {e}")

def exit_freedrive():
    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
    rtde_c.endTeachMode()
    print("Exited freedrive mode.")

# ---------------- SCENE LOADING ------------------------
def handle_scene(scene_file):
    """Load and play a URScript file on the robot."""
    print(f"Loading script: {scene_file}")
    load_response = send_dashboard_command(f"load {scene_file}")
    time.sleep(0.5)
    print(f"Playing scene: {scene_file}")
    play_response = send_dashboard_command("play")

# ---------------- AUDIO PLAYBACK -----------------------
def play_audio(file_name):
    """Play an audio file using pygame."""
    try:
        pygame.mixer.init()
        file_path = AUDIO_BASE_PATH + file_name
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(3)
    except Exception as e:
        print(f"Error playing audio: {e}")

# ---------------- OSC MESSAGE SEND ---------------------
def send_osc_command(cue_number):
    osc_client.send_message(f"/cue/{cue_number}/start", None)

# ---------------- MQTT CALLBACKS -----------------------
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))
    client.subscribe("robot/scenes")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"Received '{payload}' from topic '{msg.topic}'")

    # Example: triggering a predefined scene
    if payload in SCENES:
        handle_scene(SCENES[payload])

    elif payload == "free":
        enter_freedrive()
    elif payload == "stop":
        stop()
    elif payload == "pause":
        pause()
    elif payload == "play":
        play()
    elif payload == "audio_test":
        play_audio("example.wav")  # Replace with your audio file
    elif payload == "osc_test":
        send_osc_command(1)  # Replace with your OSC cue number
    else:
        print(f"No matching action for payload: {payload}")

# ---------------- MQTT CLIENT SETUP --------------------
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, 1883, 60)
client.loop_forever()


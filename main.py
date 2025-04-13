import time
import RPi.GPIO as GPIO
from paho.mqtt import client as MQTT
import random
import atexit
import os

BROKER = os.getenv("MQTT_BROKER_HOST") # MQTT broker IP address or hostname
PORT = 1883 # MQTT broker port
TOPIC = "rpi-sprinkler/relays/set" # MQTT topic to subscribe to
CLIENT_ID = f"rpi-sprinkler-{random.randint(1000, 9999)}"
USERNAME = os.getenv("MQTT_USERNAME") # MQTT username
PASSWORD = os.getenv("MQTT_PASSWORD") # MQTT password
RECONNECT_DELAY = 15 # reconnect delay in seconds

# GPIO pin numbers for the relays (based on https://learn.sb-components.co.uk/PiRelay-6)
RELAY_PINS = {
    1: 29,
    2: 31,
    3: 33,
    4: 35,
    5: 37,
    6: 40,
}

def setup_gpio():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    for pin in RELAY_PINS.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    print("[INFO] GPIO setup complete, all pins initialized to LOW.")

def cleanup_gpio():
    GPIO.cleanup()
    print("[INFO] GPIO cleanup complete.")


def set_pin_state(pin: int, state: bool):
    if pin in RELAY_PINS.values():
        GPIO.output(pin, GPIO.HIGH if state == True else GPIO.LOW)
        print(f"[INFO] Pin {pin} set to {'HIGH' if state == True else 'LOW'}")
    else:
        print(f"[WARNING] Unknown pin provided for (set_pin_state) function: {pin}")

def connect_mqtt() -> MQTT.Client:
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            print("[INFO] Connected to the MQTT broker.")
        else:
            print("Failed to connect, return code %d\n", rc)

    def on_disconnect(client, userdata, rc):
        print("[ERROR] The MQTT broker got disconnected with the following result code: ", rc)

        reconnect_tries = 1

        while True:
            print("[INFO] Trying to reconnect...")
            try:
                client.reconnect()
                print(f"[INFO] Successfully reconnected to the MQTT broker after {reconnect_tries} tries.")
                return
            except Exception as e:
                print(f"[ERROR] Failed to reconnect to the MQTT broker: {e}")
                time.sleep(RECONNECT_DELAY)
    
    # set client id and api version for the client
    client = MQTT.Client(CLIENT_ID)

    # set username and password for the client
    client.username_pw_set(USERNAME, PASSWORD)

    # connect to the broker
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(host=BROKER, port=PORT)

    return client

def subscribe(client: MQTT.Client):
    def on_message(client, userdata, msg):
        payload = msg.payload.decode()
        print(f"[INFO] Received message on subscribed topic: {payload}")

        # do something with the payload
        try:
            if payload['type'] == "single":
                if payload['relay'] in RELAY_PINS.keys():
                    relay_pin = RELAY_PINS[payload['relay']]
                    if payload['state'].lower() == "on":
                        set_pin_state(relay_pin, True)
                    elif payload['state'].lower() == "off":
                        set_pin_state(relay_pin, False)
                    else:
                        print(f"[WARNING] Unknown state provided for pin ({relay_pin}): {payload['state']}")
                else:
                    print(f"[WARNING] The relay provided is not in the valid range (1-6): {payload['relay']}")
            elif payload['type'] == "multi":
                for relay in payload['relay']:
                    if relay in RELAY_PINS.keys():
                        relay_pin = RELAY_PINS[relay]
                        if payload['state'].lower() == "on":
                            set_pin_state(relay_pin, True)
                        elif payload['state'].lower() == "off":
                            set_pin_state(relay_pin, False)
                        else:
                            print(f"[WARNING] Unknown state provided for pin ({relay_pin}): {payload['state']}")
                    else:
                        print(f"[WARNING] One of the relays provided is not in the valid range (1-6): {relay}")
            else:
                print(f"[WARNING] Unknown payload type provided: {payload['type']}")
        except Exception as e:
            print(f"[ERROR] An error occurred while processing the payload:\n{e}")

    # subscribe to the topic
    client.on_message = on_message
    client.subscribe(TOPIC)

    print(f"[INFO] Subscribed to topic: {TOPIC}")

def exit_handler():
    cleanup_gpio()
    print("[INFO] Exiting GPIO to MQTT bridge script...")
    exit(0)

# register exit handler
atexit.register(exit_handler)

def main():
    # setup GPIO pins
    setup_gpio()

    # connect to the MQTT broker
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()

# run main function
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit_handler()
    except Exception as e:
        print(f"[ERROR] An error occurred:\n{e}")
        exit_handler()
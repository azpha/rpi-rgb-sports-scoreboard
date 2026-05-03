import time
import json
import socket

GOVEE_API_BASE_URL = "https://openapi.api.govee.com/router/api/v1/"

class GoveeApi:
  device_ip = ""

  def __init__(self, device_ip):
    self.device_ip = device_ip

  def send_scene(self, scene_code):
    power_payload = {
        "msg": {
            "cmd": "turn",
            "data": {
                "value": 1  # 1 = on, 0 = off
            }
        }
    }
    self.send_over_socket(power_payload)
    time.sleep(0.5)

    segments = scene_code.split(",")
    for segment in segments:
      payload = {
        "msg": {
          "cmd": "ptReal",
          "data": {
            "command": [segment]
          }
        }
      }
      self.send_over_socket(payload)

  def set_to_original_color(self):
    payload = {
      "msg": {
        "cmd": "colorwc",
        "data": {
          "color": {"r": 255, "g": 0, "b": 0},
          "colorTemInKelvin": 0
        }
      }
    }
    self.send_over_socket(payload)
  
  def send_over_socket(self, payload, retries=2, delay=0.1):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    data = json.dumps(payload).encode()
    
    for attempt in range(retries):
        sock.sendto(data, (self.device_ip, 4003))
        try:
            response, _ = sock.recvfrom(1024)
            print(f"Got response on attempt {attempt + 1}")
            break  # stop retrying once we get an ack
        except socket.timeout:
            if attempt < retries - 1:
                time.sleep(delay)
    
    sock.close()
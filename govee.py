import requests
import json
import socket

GOVEE_API_BASE_URL = "https://openapi.api.govee.com/router/api/v1/"

class GoveeApi:
  device_ip = ""

  def __init__(self, device_ip):
    self.device_ip = device_ip

  def send_scene(self, scene_code):
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
  
  def send_over_socket(self, payload):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(payload).encode(), (self.device_ip, 4003))
    sock.close()

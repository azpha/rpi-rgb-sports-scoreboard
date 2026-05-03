import requests
import random
import string
import json

GOVEE_API_BASE_URL = "https://openapi.api.govee.com/router/api/v1/"

class GoveeApi:
  device_ip = ""

  def __init__(self, key):
    self.key = key

  def get_random_string(self):
      # Choose from all lowercase, uppercase letters, and digits
      characters = string.ascii_letters + string.digits
      result_str = ''.join(random.choices(characters, k=4))
      return result_str

  def get_diy_scenes(self, sku, device):
    headers = {
      'Govee-API-Key': self.key
    }
    payload = {
      "requestId": self.get_random_string(),
      "payload": {
        "sku": sku,
        "device": device
      }
    }

    res = requests.post(GOVEE_API_BASE_URL + 'device/diy-scenes', json=payload, headers=headers)
    res.raise_for_status()
    print(json.dumps(res.json(), indent=4))

  def set_diy_scene(self, sku, device):
    headers = {
      'Govee-API-Key': self.key
    }
    payload = {
      'requestId': self.get_random_string(),
      'payload': {
        'sku': sku,
        'device': device,
        'capability': {
          'type': 'device.capabilities.dynamic_scene',
          'instance': 'diyScene',
          'value': 22757907
        }
      }
    }

    req = requests.post(GOVEE_API_BASE_URL + 'device/control', headers=headers, json=payload)
    req.raise_for_status()
    print(req.json())

  def set_to_original_color(self, sku, device):
    headers = {
      'Govee-API-Key': self.key
    }
    payload = {
      'requestId': self.get_random_string(),
      'payload': {
        'sku': sku,
        'device': device,
        'capability': {
          'type': 'devices.capabilities.color_setting',
          'instance': 'colorRgb',
          'value': 16711680
        }
      }
    }

    req = requests.post(GOVEE_API_BASE_URL + 'device/control', json=payload, headers=headers)
    req.raise_for_status()
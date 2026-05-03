import requests
import random
import string
import json

GOVEE_API_BASE_URL = "https://openapi.api.govee.com/router/api/v1/"

class GoveeApi:
  key = ""
  headers = {}

  def __init__(self, key):
    self.key = key
    self.headers = {
      'Govee-API-Key': key
    }

  def __get_random_string(self):
      characters = string.ascii_letters + string.digits
      result_str = ''.join(random.choices(characters, k=4))
      return result_str

  def get_diy_scenes(self, sku, device):
    payload = {
      "requestId": self.__get_random_string(),
      "payload": {
        "sku": sku,
        "device": device
      }
    }

    res = requests.post(GOVEE_API_BASE_URL + 'device/diy-scenes', json=payload, headers=self.headers)
    res.raise_for_status()
    
    print("[GOVEE] DIY scene fetch: " + json.dumps(res.json(), indent=4))

    return res.ok

  def set_diy_scene(self, sku, device):
    payload = {
      'requestId': self.__get_random_string(),
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

    res = requests.post(GOVEE_API_BASE_URL + 'device/control', headers=self.headers, json=payload)
    res.raise_for_status()

    print("[GOVEE] Set DIY scene: " + json.dumps(res.json(), indent=4))

    return res.ok

  def set_to_original_color(self, sku, device):
    payload = {
      'requestId': self.__get_random_string(),
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

    res = requests.post(GOVEE_API_BASE_URL + 'device/control', json=payload, headers=self.headers)
    res.raise_for_status()

    print("[GOVEE] Set to original: " + json.dumps(res.json(), indent=4))

    return res.ok 
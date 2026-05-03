from govee import GoveeApi 
from time import sleep

GOVEE_DEVICE = "3D:22:D7:94:40:46:2F:72"
GOVEE_SKU = "H6168"
GOVEE_AWS = "owABAgT/AGQMACr//+YAADb//8k=,o//QAAIDAwAAAAAAAAAAAAAAAI4=,MwUKdwAAAAAAAAAAAAAAAAAAAEs="
GOVEE_IP = "172.16.0.15"

govee_api = GoveeApi(device_ip=GOVEE_IP)
govee_api.send_scene(GOVEE_AWS)
# sleep(5)
# govee_api.set_?to_original_color()
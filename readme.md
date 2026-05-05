# scoreboard

Scoreboard script for showing active sports I like.

## Equipment

I have a small setup to make this work, all specs found below

- [Raspberry Pi 4, 2GB](https://www.amazon.com/dp/B07TYK4RL8?ref=ppx_yo2ov_dt_b_fed_asin_title)
- [4x waveshare P2.5 64x32 LED panels](https://www.amazon.com/dp/B0BRBGHFKQ?ref=ppx_yo2ov_dt_b_fed_asin_title)
- [MEAN WELL LRS-100-5 5v PSU](https://www.amazon.com/dp/B07DKCMJN9?ref=ppx_yo2ov_dt_b_fed_asin_title)
- [Adafruit Triple LED Matrix HUB75 Bonnet](https://www.adafruit.com/product/6358)

## Setup

- Install Python, Python build tools & build rpi-rgb-led-matrix [from source](https://github.com/hzeller/rpi-rgb-led-matrix) or install it via pip
- Clone this repository
- Install requirements using `pip install -r requirements.txt`
- Download logos using the `download_logos.py` Python script
- Run `scoreboard.py` Python script

## Govee Lighting

If you have Govee lighting you want to setup for celebrations, create a `.env` file and complete the arguments in the template file.

#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
libdir = os.path.join(os.path.expanduser('~'), 'e-Paper', 'RaspberryPi_JetsonNano', 'python', 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
import logging
from waveshare_epd import epd7in3e
from PIL import Image, ImageDraw, ImageFont
from astral.moon import phase
from astral import LocationInfo
from astral.sun import sun
from datetime import date, datetime
import json
import random
import urllib.request
logging.basicConfig(level=logging.DEBUG)

WHITE        = (255, 255, 255)
BLACK        = (0, 0, 0)
DARK_PURPLE  = (60, 20, 90)
BLUE         = (0, 80, 200)
YELLOW       = (230, 180, 0)
SHADOW       = (180, 160, 100)

FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

PHASE_NAMES = [
    (0,  1,  "new moon"),
    (1,  6,  "waxing crescent"),
    (6,  8,  "first quarter"),
    (8,  13, "waxing gibbous"),
    (13, 15, "full moon"),
    (15, 20, "waning gibbous"),
    (20, 22, "last quarter"),
    (22, 28, "waning crescent"),
]

DAY_PLANETS = {
    0: "moon", 1: "mars", 2: "mercury",
    3: "jupiter", 4: "venus", 5: "saturn", 6: "sun",
}

PLANETARY_HOURS = ["sun", "venus", "mercury", "moon", "saturn", "jupiter", "mars"]

PLANET_SYMBOLS = {
    "moon": "☽",
    "mars": "♂",
    "mercury": "☿",
    "jupiter": "♃",
    "venus": "♀",
    "saturn": "♄",
    "sun": "☉",
}

WEATHER_LAT = 48.2082
WEATHER_LON = 16.3738

def get_phase_name(phase_value):
    for lo, hi, name in PHASE_NAMES:
        if lo <= phase_value < hi:
            return name
    return "waning crescent"

def get_day_planet():
    return DAY_PLANETS[date.today().weekday()]

def get_planetary_hour():
    city = LocationInfo("Vienna", "Austria", "Europe/Vienna", 48.2082, 16.3738)
    s = sun(city.observer, date=date.today())
    sunrise = s['sunrise'].replace(tzinfo=None)
    now = datetime.now()
    hour_index = int((now - sunrise).total_seconds() // 3600)
    day_index = date.today().weekday()
    day_start = [3, 6, 2, 4, 5, 1, 0][day_index]
    return PLANETARY_HOURS[(day_start + hour_index) % 7]

def get_weather_data():
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,weather_code"
        "&forecast_days=1"
        "&timezone=Europe%2FVienna"
    ).format(lat=WEATHER_LAT, lon=WEATHER_LON)
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        daily = data["daily"]
        return {
            "high": round(daily["temperature_2m_max"][0]),
            "low": round(daily["temperature_2m_min"][0]),
            "code": daily["weather_code"][0],
        }
    except Exception as e:
        logging.warning("weather fetch failed: %s", e)
        return None

def get_weather_symbol(code):
    if code == 0:
        return "☀"
    if code in (1, 2, 3):
        return "⛅"
    if code in (45, 48):
        return "☁"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "☔"
    if code in (71, 73, 75, 77, 85, 86):
        return "❄"
    if code in (95, 96, 99):
        return "⚡"
    return "☁"

def draw_text_line(draw, text, x, y, font, fill, spacing=10):
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text((x, y), text, font=font, fill=fill)
    return y + (bbox[3] - bbox[1]) + spacing

def draw_moon(draw, cx, cy, radius, phase_value):
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=YELLOW)
    if phase_value < 14:
        fraction = phase_value / 14.0
        shadow_offset = int(radius * (1 - 2 * fraction))
        draw.ellipse((cx + shadow_offset - radius, cy - radius,
                      cx + shadow_offset + radius, cy + radius), fill=SHADOW)
    else:
        fraction = (phase_value - 14) / 14.0
        shadow_offset = int(radius * (2 * fraction - 1))
        draw.ellipse((cx + shadow_offset - radius, cy - radius,
                      cx + shadow_offset + radius, cy + radius), fill=SHADOW)
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=DARK_PURPLE, width=2)

def draw_cat(draw, cx, cy, size):
    # head
    draw.ellipse((cx-size, cy-size, cx+size, cy+size), fill=BLACK, outline=BLACK)
    # ears
    ear = size // 2
    draw.polygon([
        (cx-size, cy-size+4),
        (cx-size+ear, cy-size-ear),
        (cx-ear, cy-size+4)
    ], fill=BLACK)
    draw.polygon([
        (cx+size, cy-size+4),
        (cx+size-ear, cy-size-ear),
        (cx+ear, cy-size+4)
    ], fill=BLACK)
    # blue eyes
    eye_y = cy - size // 4
    draw.ellipse((cx-size//2-4, eye_y-4, cx-size//2+4, eye_y+4), fill=BLUE)
    draw.ellipse((cx+size//2-4, eye_y-4, cx+size//2+4, eye_y+4), fill=BLUE)
    # nose
    draw.polygon([(cx, cy+4), (cx-3, cy), (cx+3, cy)], fill=WHITE)
    # mouth
    draw.line((cx, cy+6, cx-3, cy+10), fill=WHITE, width=1)
    draw.line((cx, cy+6, cx+3, cy+10), fill=WHITE, width=1)
    # whiskers
    draw.line((cx-size, cy,   cx-size//2-4, cy+2),  fill=WHITE, width=1)
    draw.line((cx-size, cy+8, cx-size//2-4, cy+4),  fill=WHITE, width=1)
    draw.line((cx+size, cy,   cx+size//2+4, cy+2),  fill=WHITE, width=1)
    draw.line((cx+size, cy+8, cx+size//2+4, cy+4),  fill=WHITE, width=1)

try:
    epd = epd7in3e.EPD()
    epd.init()
    Himage = Image.new('RGB', (epd.width, epd.height), WHITE)
    draw = ImageDraw.Draw(Himage)

    font_sm = ImageFont.truetype(FONT_PATH, 44)
    font_md = ImageFont.truetype(FONT_PATH, 56)
    font_lg = ImageFont.truetype(FONT_PATH, 72)
    MARGIN = 80

    # moon
    moon_phase = phase(date.today())
    draw_moon(draw, cx=epd.width//2, cy=epd.height//2 + 25, radius=120, phase_value=moon_phase)

    # moon phase name
    phase_name = get_phase_name(moon_phase)
    bbox = draw.textbbox((0, 0), phase_name, font=font_md)
    tw = bbox[2] - bbox[0]
    draw.text(((epd.width - tw) // 2, epd.height//2 + 170), phase_name, font=font_md, fill=DARK_PURPLE)

    # day + planetary hour — top left
    top_left_x = 40
    day_symbol = PLANET_SYMBOLS[get_day_planet()]
    hour_symbol = PLANET_SYMBOLS[get_planetary_hour()]
    day_text = f"Day: {day_symbol}"
    hour_text = f"Hour: {hour_symbol}"
    day_bbox = draw.textbbox((0, 0), day_text, font=font_sm)
    next_y = draw_text_line(draw, day_text, top_left_x, 10 - day_bbox[1], font_sm, DARK_PURPLE)
    next_y = draw_text_line(draw, hour_text, top_left_x, next_y, font_sm, DARK_PURPLE)

    # weather — left side, below day/hour
    weather = get_weather_data()
    if weather:
        symbol = get_weather_symbol(weather["code"])
        high = weather["high"]
        low = weather["low"]
    else:
        symbol = "?"
        high = "?"
        low = "?"

    weather_x = 40
    next_y = draw_text_line(draw, symbol, weather_x, next_y + 30, font_lg, DARK_PURPLE)
    next_y = draw_text_line(draw, f"H:{high}°", weather_x, next_y, font_md, DARK_PURPLE, spacing=5)
    draw_text_line(draw, f"L:{low}°", weather_x, next_y, font_md, DARK_PURPLE, spacing=50)

    # favours — top right, dark purple
    zodiac = random.choice(["♈", "♑", "♎"])
    label = "Favours: "
    label_bbox = draw.textbbox((0, 0), label, font=font_sm)
    label_w = label_bbox[2] - label_bbox[0]
    label_h = label_bbox[3] - label_bbox[1]
    symbol_bbox = draw.textbbox((0, 0), zodiac, font=font_md)
    symbol_w = symbol_bbox[2] - symbol_bbox[0]
    symbol_h = symbol_bbox[3] - symbol_bbox[1]
    total_w = label_w + symbol_w
    x = epd.width - 40 - total_w
    y = 10 - label_bbox[1]
    draw.text((x, y), label, font=font_sm, fill=DARK_PURPLE)
    draw.text((x + label_w, y + (label_h - symbol_h) // 2), zodiac, font=font_md, fill=DARK_PURPLE)

    # cat in bottom-right corner, safely away from text
    CAT_SIZE = 80
    CAT_MARGIN = 100
    cx, cy = epd.width - CAT_MARGIN, epd.height - CAT_MARGIN
    draw_cat(draw, cx, cy, size=CAT_SIZE)

    epd.display(epd.getbuffer(Himage))
    epd.sleep()

except IOError as e:
    logging.info(e)
except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd7in3e.epdconfig.module_exit(cleanup=True)
    exit()

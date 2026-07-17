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
RED          = (220, 40, 40)
ORANGE       = (240, 130, 0)
YELLOW       = (230, 180, 0)
SHADOW       = (180, 160, 100)

TEXT_FONT_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]
SYMBOL_FONT_PATHS = [
    '/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf',
    '/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]

def load_font(size, paths):
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

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
WINDY_THRESHOLD = 30

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
        "&daily=temperature_2m_max,temperature_2m_min,weather_code,wind_speed_10m_max"
        "&forecast_days=1"
        "&temperature_unit=celsius"
        "&wind_speed_unit=kmh"
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
            "wind": daily["wind_speed_10m_max"][0],
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

def get_wind_message(max_wind_kmh):
    if max_wind_kmh >= WINDY_THRESHOLD:
        return "It fucken WIMDY"
    return None

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
    # keep the shadow inside the moon disk
    draw.ellipse((cx-2*radius, cy-2*radius, cx+2*radius, cy+2*radius), outline=WHITE, width=radius)
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=DARK_PURPLE, width=2)

def draw_cat(draw, cx, cy, size, color=BLACK):
    # head
    draw.ellipse((cx-size, cy-size, cx+size, cy+size), fill=color, outline=color)
    # ears
    ear = size // 2
    draw.polygon([
        (cx-size, cy-size+4),
        (cx-size+ear, cy-size-ear),
        (cx-ear, cy-size+4)
    ], fill=color)
    draw.polygon([
        (cx+size, cy-size+4),
        (cx+size-ear, cy-size-ear),
        (cx+ear, cy-size+4)
    ], fill=color)
    # blue eyes
    eye_r = max(4, size // 8)
    eye_y = cy - size // 4
    draw.ellipse((cx-size//2-eye_r, eye_y-eye_r, cx-size//2+eye_r, eye_y+eye_r), fill=BLUE)
    draw.ellipse((cx+size//2-eye_r, eye_y-eye_r, cx+size//2+eye_r, eye_y+eye_r), fill=BLUE)
    # nose
    nose_w = max(3, size // 8)
    nose_h = max(2, size // 12)
    draw.polygon([(cx, cy+nose_h), (cx-nose_w, cy), (cx+nose_w, cy)], fill=WHITE)
    # mouth
    mouth_len = max(4, size // 7)
    mouth_down = max(4, size // 10)
    draw.line((cx, cy+nose_h+2, cx-mouth_len, cy+nose_h+mouth_down), fill=WHITE, width=2)
    draw.line((cx, cy+nose_h+2, cx+mouth_len, cy+nose_h+mouth_down), fill=WHITE, width=2)
    # whiskers
    whisker_end = size // 2 + size // 6
    draw.line((cx-size, cy,                cx-whisker_end, cy+size//12),     fill=WHITE, width=2)
    draw.line((cx-size, cy+size//6,        cx-whisker_end, cy+size//8),      fill=WHITE, width=2)
    draw.line((cx+size, cy,                cx+whisker_end, cy+size//12),     fill=WHITE, width=2)
    draw.line((cx+size, cy+size//6,        cx+whisker_end, cy+size//8),      fill=WHITE, width=2)

try:
    epd = epd7in3e.EPD()
    epd.init()
    Himage = Image.new('RGB', (epd.width, epd.height), WHITE)
    draw = ImageDraw.Draw(Himage)

    font_sm = load_font(44, TEXT_FONT_PATHS)
    font_md = load_font(56, TEXT_FONT_PATHS)
    font_lg = load_font(72, TEXT_FONT_PATHS)
    font_xl = load_font(96, TEXT_FONT_PATHS)
    symbol_sm = load_font(56, SYMBOL_FONT_PATHS)
    symbol_md = load_font(72, SYMBOL_FONT_PATHS)
    symbol_xl = load_font(96, SYMBOL_FONT_PATHS)
    CAT_SIZE = 80
    CAT_X_MARGIN = 100
    CAT_Y_MARGIN = 140

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
    line_y = 10
    day_label = "Day: "
    hour_label = "Hour: "
    day_symbol = PLANET_SYMBOLS[get_day_planet()]
    hour_symbol = PLANET_SYMBOLS[get_planetary_hour()]
    label_bbox = draw.textbbox((0, 0), day_label, font=font_sm)
    symbol_bbox = draw.textbbox((0, 0), day_symbol, font=symbol_sm)
    day_x = top_left_x
    day_y = line_y - label_bbox[1]
    draw.text((day_x, day_y), day_label, font=font_sm, fill=DARK_PURPLE)
    label_w = label_bbox[2] - label_bbox[0]
    label_h = label_bbox[3] - label_bbox[1]
    draw.text((day_x + label_w, day_y + label_h // 2), day_symbol,
              font=symbol_sm, fill=DARK_PURPLE, anchor="lm")
    hour_x = top_left_x
    hour_y = day_y + label_h + 10
    draw.text((hour_x, hour_y), hour_label, font=font_sm, fill=DARK_PURPLE)
    draw.text((hour_x + label_w, hour_y + label_h // 2), hour_symbol,
              font=symbol_sm, fill=DARK_PURPLE, anchor="lm")
    next_y = hour_y + label_h

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
    temps_y = next_y + 30
    next_y = draw_text_line(draw, f"{high}°", weather_x, temps_y, font_md, RED, spacing=5)
    draw_text_line(draw, f"{low}°", weather_x, next_y, font_md, BLUE, spacing=50)

    # large weather symbol above the cat
    cat_cx = epd.width - CAT_X_MARGIN
    cat_cy = epd.height - CAT_Y_MARGIN
    sym_bbox = draw.textbbox((0, 0), symbol, font=symbol_xl)
    sym_w = sym_bbox[2] - sym_bbox[0]
    sym_h = sym_bbox[3] - sym_bbox[1]
    sym_x = cat_cx - sym_w // 2
    sym_y = (cat_cy - CAT_SIZE) - sym_h + 30
    draw.text((sym_x, sym_y), symbol, font=symbol_xl, fill=DARK_PURPLE)

    # windy warning — above the moon
    if weather and weather["wind"] >= WINDY_THRESHOLD:
        wimdy_text = "It fucken WIMDY"
        wimdy_bbox = draw.textbbox((0, 0), wimdy_text, font=font_sm)
        wimdy_w = wimdy_bbox[2] - wimdy_bbox[0]
        wimdy_h = wimdy_bbox[3] - wimdy_bbox[1]
        moon_top = (epd.height // 2 + 25) - 120
        draw.text(((epd.width - wimdy_w) // 2, moon_top - wimdy_h - 10), wimdy_text, font=font_sm, fill=DARK_PURPLE)

    # favours — top right, dark purple
    zodiac = random.choice(["♈", "♑", "♎"])
    label = "Favours: "
    label_bbox = draw.textbbox((0, 0), label, font=font_sm)
    label_w = label_bbox[2] - label_bbox[0]
    label_h = label_bbox[3] - label_bbox[1]
    symbol_bbox = draw.textbbox((0, 0), zodiac, font=symbol_md)
    symbol_w = symbol_bbox[2] - symbol_bbox[0]
    symbol_h = symbol_bbox[3] - symbol_bbox[1]
    total_w = label_w + symbol_w
    x = epd.width - 40 - total_w
    y = 10 - label_bbox[1]
    draw.text((x, y), label, font=font_sm, fill=DARK_PURPLE)
    draw.text((x + label_w, y + label_h // 2), zodiac,
              font=symbol_md, fill=DARK_PURPLE, anchor="lm")

    # cat in bottom-right corner, safely away from text
    cat_color = random.choice([BLACK, ORANGE])
    cx, cy = epd.width - CAT_X_MARGIN, epd.height - CAT_Y_MARGIN
    draw_cat(draw, cx, cy, size=CAT_SIZE, color=cat_color)

    epd.display(epd.getbuffer(Himage))
    epd.sleep()

except IOError as e:
    logging.info(e)
except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd7in3e.epdconfig.module_exit(cleanup=True)
    exit()

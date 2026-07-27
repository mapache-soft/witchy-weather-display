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
import math
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
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf',
    '/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf',
    '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
]

def load_font(size, paths):
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

PHASE_NAMES = [
    (0,  1,  "new moon"),
    (1,  6,  "waxing croissant"),
    (6,  8,  "first quarter"),
    (8,  13, "waxing gibbon"),
    (13, 15, "full moon"),
    (15, 20, "waning gibbon"),
    (20, 22, "last quarter"),
    (22, 28, "waning croissant"),
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
    return "waning croissant"

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

def get_weather_kind(code):
    if code == 0:
        return "sun"
    if code in (1, 2, 3):
        return "partly"
    if code in (45, 48):
        return "cloud"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "cloud"

def get_weather_color(code):
    if code == 0:
        return YELLOW
    if code in (1, 2, 3):
        return ORANGE
    if code in (45, 48):
        return BLACK
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return BLUE
    if code in (71, 73, 75, 77, 85, 86):
        return DARK_PURPLE
    if code in (95, 96, 99):
        return RED
    return BLACK

def get_wind_message(max_wind_kmh):
    if max_wind_kmh >= WINDY_THRESHOLD:
        return "It fucken WIMDY"
    return None

def _draw_sun_disk(draw, cx, cy, r, color):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    ray_inner = r + max(4, r // 4)
    ray_outer = r + max(10, r // 2)
    for i in range(8):
        angle = i * math.pi / 4
        x1 = cx + int(ray_inner * math.cos(angle))
        y1 = cy + int(ray_inner * math.sin(angle))
        x2 = cx + int(ray_outer * math.cos(angle))
        y2 = cy + int(ray_outer * math.sin(angle))
        draw.line((x1, y1, x2, y2), fill=color, width=max(3, r // 5))

def _draw_cloud(draw, cx, cy, w, h, color):
    left = cx - w // 2
    top = cy - h // 2
    r1 = h // 2
    r2 = int(h * 0.42)
    r3 = int(h * 0.38)
    draw.ellipse((left, cy - r1, left + 2 * r1, cy + r1), fill=color)
    draw.ellipse((left + w // 5, top, left + w // 5 + 2 * r2, top + 2 * r2), fill=color)
    draw.ellipse((cx - r3, top + h // 10, cx + r3, top + h // 10 + 2 * r3), fill=color)
    draw.ellipse((left + w - 2 * r1, cy - r1, left + w, cy + r1), fill=color)
    draw.rectangle((left + r1 // 2, cy - h // 6, left + w - r1 // 2, cy + r1), fill=color)

def draw_weather_icon(draw, cx, cy, size, kind, color):
    if kind == "sun":
        _draw_sun_disk(draw, cx, cy, size // 3, color)
        return
    if kind == "partly":
        sun_r = size // 5
        _draw_sun_disk(draw, cx - size // 6, cy - size // 6, sun_r, YELLOW)
        _draw_cloud(draw, cx + size // 10, cy + size // 10, int(size * 0.85), int(size * 0.45), color)
        return
    if kind == "cloud":
        _draw_cloud(draw, cx, cy, int(size * 0.95), int(size * 0.5), color)
        return
    if kind == "rain":
        _draw_cloud(draw, cx, cy - size // 8, int(size * 0.9), int(size * 0.42), color)
        drop_y = cy + size // 6
        for dx in (-size // 4, 0, size // 4):
            draw.line((cx + dx, drop_y, cx + dx - 4, drop_y + size // 4),
                      fill=BLUE, width=max(3, size // 18))
        return
    if kind == "snow":
        _draw_cloud(draw, cx, cy - size // 8, int(size * 0.9), int(size * 0.42), color)
        flake_y = cy + size // 5
        for dx in (-size // 4, 0, size // 4):
            fx, fy = cx + dx, flake_y
            arm = max(4, size // 14)
            draw.line((fx - arm, fy, fx + arm, fy), fill=color, width=2)
            draw.line((fx, fy - arm, fx, fy + arm), fill=color, width=2)
            draw.line((fx - arm, fy - arm, fx + arm, fy + arm), fill=color, width=2)
            draw.line((fx - arm, fy + arm, fx + arm, fy - arm), fill=color, width=2)
        return
    if kind == "storm":
        _draw_cloud(draw, cx, cy - size // 8, int(size * 0.9), int(size * 0.42), BLACK)
        bolt = [
            (cx + size // 12, cy - size // 20),
            (cx - size // 10, cy + size // 8),
            (cx + size // 30, cy + size // 8),
            (cx - size // 8, cy + size // 3),
            (cx + size // 6, cy + size // 12),
            (cx + size // 40, cy + size // 12),
        ]
        draw.polygon(bolt, fill=YELLOW)
        return
    _draw_cloud(draw, cx, cy, int(size * 0.95), int(size * 0.5), color)

def draw_text_line(draw, text, x, y, font, fill, spacing=10):
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text((x, y), text, font=font, fill=fill)
    return y + (bbox[3] - bbox[1]) + spacing

def draw_moon(draw, cx, cy, radius, phase_value):
    """Northern-hemisphere moon: waxing lit on the right, waning on the left."""
    size = max(2, int(radius) * 2)
    radius = size // 2
    moon_img = Image.new("RGB", (size, size), WHITE)
    moon_draw = ImageDraw.Draw(moon_img)

    p = phase_value % 28.0
    angle = math.pi * (p / 14.0)
    cos_a = math.cos(angle)
    term_half = max(1, int(round(abs(cos_a) * radius)))
    left = radius - term_half
    right = radius + term_half

    moon_draw.ellipse((0, 0, size - 1, size - 1), fill=YELLOW)

    if p <= 14:
        # waxing: shadow on the left, lit grows on the right
        moon_draw.rectangle((0, 0, radius, size), fill=SHADOW)
        if cos_a >= 0:
            moon_draw.ellipse((left, 0, right, size - 1), fill=SHADOW)
        else:
            moon_draw.ellipse((left, 0, right, size - 1), fill=YELLOW)
    else:
        # waning: shadow on the right, lit shrinks on the left
        moon_draw.rectangle((radius, 0, size, size), fill=SHADOW)
        if cos_a <= 0:
            moon_draw.ellipse((left, 0, right, size - 1), fill=YELLOW)
        else:
            moon_draw.ellipse((left, 0, right, size - 1), fill=SHADOW)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    draw._image.paste(moon_img, (cx - radius, cy - radius), mask)

    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        outline=DARK_PURPLE,
        width=2,
    )

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
    symbol_xxl = load_font(140, SYMBOL_FONT_PATHS)
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
    draw.text((day_x + label_w + 10, day_y + 5 + label_h // 2), day_symbol,
              font=symbol_md, fill=DARK_PURPLE, anchor="lm")
    hour_x = top_left_x
    hour_y = day_y + label_h + 20
    draw.text((hour_x, hour_y), hour_label, font=font_sm, fill=DARK_PURPLE)
    draw.text((hour_x + label_w + 10, hour_y + label_h // 2), hour_symbol,
              font=symbol_md, fill=DARK_PURPLE, anchor="lm")
    next_y = hour_y + label_h

    # weather — left side, below day/hour
    weather = get_weather_data()
    if weather:
        weather_kind = get_weather_kind(weather["code"])
        high = weather["high"]
        low = weather["low"]
    else:
        weather_kind = "cloud"
        high = "?"
        low = "?"

    weather_x = 40
    temp_font = font_lg
    high_text = f"{high}°"
    low_text = f"{low}°"
    high_bbox = draw.textbbox((0, 0), high_text, font=temp_font)
    low_bbox = draw.textbbox((0, 0), low_text, font=temp_font)
    high_h = high_bbox[3] - high_bbox[1]
    low_h = low_bbox[3] - low_bbox[1]
    temp_gap = 20
    block_h = high_h + temp_gap + low_h
    center_y = epd.height // 2
    temps_top = center_y - block_h // 2
    draw.text((weather_x, temps_top), high_text, font=temp_font, fill=RED)
    draw.text((weather_x, temps_top + high_h + temp_gap), low_text, font=temp_font, fill=BLUE)

    # large weather icon above the cat (drawn geometry, not emoji)
    cat_cx = epd.width - CAT_X_MARGIN
    cat_cy = epd.height - CAT_Y_MARGIN
    weather_color = get_weather_color(weather["code"]) if weather else DARK_PURPLE
    icon_size = 120
    icon_cx = cat_cx
    icon_cy = (cat_cy - CAT_SIZE) - icon_size // 2 - 40
    draw_weather_icon(draw, icon_cx, icon_cy, icon_size, weather_kind, weather_color)

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
    draw.text((x + label_w, y + label_h // 2 + 10), zodiac,
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

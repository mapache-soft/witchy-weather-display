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
import random
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

    font_sm = ImageFont.truetype(FONT_PATH, 22)
    font_md = ImageFont.truetype(FONT_PATH, 28)

    # moon
    moon_phase = phase(date.today())
    draw_moon(draw, cx=epd.width//2, cy=epd.height//2, radius=120, phase_value=moon_phase)

    # moon phase name
    phase_name = get_phase_name(moon_phase)
    bbox = draw.textbbox((0, 0), phase_name, font=font_md)
    tw = bbox[2] - bbox[0]
    draw.text(((epd.width - tw) // 2, epd.height//2 + 140), phase_name, font=font_md, fill=DARK_PURPLE)

    # day + planetary hour — top left, safely clear of cat
    draw.text((120, 30), f"day of {get_day_planet()}", font=font_sm, fill=DARK_PURPLE)
    draw.text((120, 60), f"hour of {get_planetary_hour()}", font=font_sm, fill=DARK_PURPLE)

    # cat in random corner, safely away from text
    CAT_SIZE = 30
    MARGIN = 50
    corners = [
        (MARGIN, epd.height - MARGIN),           # bottom left
        (epd.width - MARGIN, epd.height - MARGIN), # bottom right
        (epd.width - MARGIN, MARGIN),             # top right
        # top left reserved for text
    ]
    cx, cy = random.choice(corners)
    draw_cat(draw, cx, cy, size=CAT_SIZE)

    epd.display(epd.getbuffer(Himage))
    epd.sleep()

except IOError as e:
    logging.info(e)
except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd7in3e.epdconfig.module_exit(cleanup=True)
    exit()

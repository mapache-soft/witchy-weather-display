#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
libdir = os.path.join(os.path.expanduser('~'), 'e-Paper', 'RaspberryPi_JetsonNano', 'python', 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
import logging
from waveshare_epd import epd7in3e
from PIL import Image, ImageDraw
from astral.moon import phase
from datetime import date
import math
logging.basicConfig(level=logging.DEBUG)

def draw_moon(draw, cx, cy, radius, phase_value):
    # phase_value: 0=new, 7=first quarter, 14=full, 21=last quarter, 28=new
    DARK_LAVENDER = (100, 80, 140)
    LIGHT = (230, 220, 245)
    SHADOW = (140, 120, 170)

    # draw full circle
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=LIGHT)

    # calculate illumination
    if phase_value < 14:
        # waxing
        fraction = phase_value / 14.0
        shadow_offset = int(radius * (1 - 2 * fraction))
        draw.ellipse((cx + shadow_offset - radius, cy - radius,
                      cx + shadow_offset + radius, cy + radius), fill=SHADOW)
    else:
        # waning
        fraction = (phase_value - 14) / 14.0
        shadow_offset = int(radius * (2 * fraction - 1))
        draw.ellipse((cx + shadow_offset - radius, cy - radius,
                      cx + shadow_offset + radius, cy + radius), fill=SHADOW)

    # outline
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=DARK_LAVENDER, width=2)

try:
    LAVENDER = (182, 160, 210)
    epd = epd7in3e.EPD()
    epd.init()
    Himage = Image.new('RGB', (epd.width, epd.height), LAVENDER)
    draw = ImageDraw.Draw(Himage)

    moon_phase = phase(date.today())
    draw_moon(draw, cx=epd.width//2, cy=epd.height//2, radius=120, phase_value=moon_phase)

    epd.display(epd.getbuffer(Himage))
    epd.sleep()
except IOError as e:
    logging.info(e)
except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd7in3e.epdconfig.module_exit(cleanup=True)
    exit()

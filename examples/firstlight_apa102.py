# SPDX-FileCopyrightText: 2026 stefan krüger
# SPDX-License-Identifier: MIT

# Minimal first-light: one white dot moving through all APA102 pixels.

import time
import board
import adafruit_dotstar

NUM_APA = 57  # 29 + 28, folded

pixels = adafruit_dotstar.DotStar(
    board.IO12,
    board.IO11,
    NUM_APA,
    brightness=0.1,
    auto_write=False,
    baudrate=1_000_000,
)

print("first light — white dot sweeping all pixels")

pos = 0
while True:
    pixels.fill((0, 0, 0))
    pixels[pos] = (255, 255, 255)
    pixels.show()
    pos = (pos + 1) % NUM_APA
    time.sleep(0.05)

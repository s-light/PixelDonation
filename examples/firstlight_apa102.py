# SPDX-FileCopyrightText: 2026 stefan krüger
# SPDX-License-Identifier: MIT

# Minimal first-light: one white dot at position 0 on the APA102 strip.

import board
import adafruit_dotstar

NUM_APA = 57  # 29 + 28, folded

pixels = adafruit_dotstar.DotStar(board.IO12, board.IO11, NUM_APA,
                                   brightness=0.1, auto_write=False,
                                   baudrate=1_000_000)
pixels.fill((0, 0, 0))
pixels[0] = (255, 255, 255)
pixels.show()

print("first light — pixel 0 should be white")

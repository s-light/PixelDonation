# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Simple FancyLED example for NeoPixel strip"""


import time
import board
import keypad

keys = keypad.Keys(
    (
        # onboard buttons
        board.GP20,
        board.GP21,
        # GROVE dual Button on `GROVE 2` port.
        board.GP2,
        board.GP3,
    ),
    value_when_pressed=False,
    pull=True,
)


# leds
import neopixel
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.color import PURPLE

num_leds = 20
pixels_left = neopixel.NeoPixel(board.GP14, num_leds, brightness=0.5, auto_write=False)
pixels_right = neopixel.NeoPixel(board.GP15, num_leds, brightness=0.5, auto_write=False)

comet_left = Comet(
    pixels_left,
    speed=0.02,
    color=PURPLE,
    tail_length=10,
)

comet_right = Comet(
    pixels_right,
    speed=0.02,
    color=PURPLE,
    tail_length=10,
)


def comet_stop(animation):
    if animation.cycle_count >= 2:
        animation.freeze()
        animation.reset()
        animation.cycle_count = 0


comet_left.add_cycle_complete_receiver(comet_stop)
comet_left.freeze()
comet_right.add_cycle_complete_receiver(comet_stop)
comet_right.freeze()


while True:
    comet_left.animate()
    comet_right.animate()

    event = keys.events.get()
    # event will be None if nothing has happened.
    # if event:
    #     print(event)
    if event and event.pressed:
        if event.key_number == 0:
            comet_left.resume()
        if event.key_number == 1:
            comet_right.resume()
        if event.key_number == 2:
            comet_left.resume()
        if event.key_number == 3:
            comet_right.resume()

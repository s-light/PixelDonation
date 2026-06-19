# SPDX-FileCopyrightText: 2026 stefan krüger
# SPDX-License-Identifier: MIT

import time
import math
import board
import analogio
import usb_cdc
import neopixel
import adafruit_dotstar
from adafruit_fancyled.adafruit_fancyled import CHSV, gamma_adjust
from adafruit_led_animation.animation.comet import Comet

# ── hardware ───────────────────────────────────────────────────────────────────
NUM_APA = 57   # 29 + 28 pixels, folded strip — treated as linear for now
NUM_WS  = 30   # adjust to actual WS2812B strip length

pixels_apa = adafruit_dotstar.DotStar(board.IO12, board.IO11, NUM_APA, brightness=0.3, auto_write=False, baudrate=1_000_000)
pixels_ws  = neopixel.NeoPixel(board.IO13, NUM_WS, brightness=0.3, auto_write=False)

sensor_pin = analogio.AnalogIn(board.IO4)
dataio     = usb_cdc.data   # second CDC port for SerialPlot

# ── sensor / event detection ───────────────────────────────────────────────────
_ema_fast     = 0.0
_ema_slow     = 0.0
ALPHA_FAST    = 0.1
ALPHA_SLOW    = 0.002
DELTA_THRESHOLD = 3000   # 16-bit ADC units — tune after first run
DEBOUNCE_S    = 3.0
_last_event_t = -DEBOUNCE_S

def read_sensor():
    global _ema_fast, _ema_slow
    raw       = sensor_pin.value
    _ema_fast = ALPHA_FAST * raw + (1 - ALPHA_FAST) * _ema_fast
    _ema_slow = ALPHA_SLOW * raw + (1 - ALPHA_SLOW) * _ema_slow
    delta     = _ema_fast - _ema_slow
    return raw, _ema_fast, _ema_slow, delta

# ── color helper ───────────────────────────────────────────────────────────────
def hsv(h, s=1.0, v=1.0):
    c = gamma_adjust(CHSV(h % 1.0, s, v))
    return (int(c.red * 255), int(c.green * 255), int(c.blue * 255))

# ── thank-you animation ────────────────────────────────────────────────────────
THANKYOU_COLOR = hsv(0.13, 1.0, 1.0)   # warm gold

comet_apa = Comet(pixels_apa, speed=0.02, color=THANKYOU_COLOR, tail_length=12, bounce=False)
comet_ws  = Comet(pixels_ws,  speed=0.02, color=THANKYOU_COLOR, tail_length=8,  bounce=False)

# ── state machine ──────────────────────────────────────────────────────────────
STATE_STANDBY  = 0
STATE_THANKYOU = 1
state = STATE_STANDBY

def _on_thankyou_done(animation):
    global state
    if animation.cycle_count >= 2:
        comet_apa.freeze()
        comet_ws.freeze()
        state = STATE_STANDBY

comet_apa.add_cycle_complete_receiver(_on_thankyou_done)
comet_apa.freeze()
comet_ws.freeze()

def start_thankyou():
    global state
    comet_apa.reset()
    comet_apa.cycle_count = 0
    comet_ws.reset()
    comet_ws.cycle_count  = 0
    comet_apa.resume()
    comet_ws.resume()
    state = STATE_THANKYOU

# ── plasma standby ─────────────────────────────────────────────────────────────
_PLASMA_SPEED = 0.4
_PLASMA_SCALE = 4.0
_PLASMA_VALUE = 0.3    # tune to taste

def plasma_frame(t):
    for pixels in (pixels_apa, pixels_ws):
        n = len(pixels)
        for i in range(n):
            hue = (
                math.sin(i / n * _PLASMA_SCALE + t * _PLASMA_SPEED) * 0.25
                + math.sin(t * 0.23 + i / n * 2.0) * 0.15
                + t * 0.04
            )
            pixels[i] = hsv(hue, 1.0, _PLASMA_VALUE)
        pixels.show()

# ── main ───────────────────────────────────────────────────────────────────────
print("PixelDonation - ready")

while True:
    now = time.monotonic()

    raw, filtered, baseline, delta = read_sensor()
    event = 0

    if abs(delta) > DELTA_THRESHOLD and (now - _last_event_t) > DEBOUNCE_S:
        _last_event_t = now
        event = 1
        if state == STATE_STANDBY:
            start_thankyou()

    if dataio:
        dataio.write(f"{raw};{filtered:.0f};{baseline:.0f};{delta:.0f};{event};\n".encode())

    if state == STATE_STANDBY:
        plasma_frame(now)
    else:
        comet_apa.animate()
        comet_ws.animate()

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
# APA102 strip is physically folded: col 0 goes up (29 px), col 1 goes down (28 px)
COL_HEIGHTS = (29, 28)
NUM_APA = sum(COL_HEIGHTS)  # 57
NUM_WS = 30  # adjust to actual WS2812B strip length

pixels_apa = adafruit_dotstar.DotStar(
    board.IO12,
    board.IO11,
    NUM_APA,
    brightness=0.3,
    auto_write=False,
    baudrate=1_000_000,
)
pixels_ws = neopixel.NeoPixel(board.IO13, NUM_WS, brightness=0.3, auto_write=False)

sensor_pin = analogio.AnalogIn(board.IO4)
# dataio = usb_cdc.data  # second CDC port for SerialPlot → not available on ESP32-S3
dataio = usb_cdc.console

# ── sensor / event detection ───────────────────────────────────────────────────
# seed EMAs with the current reading so delta starts at zero
_ema_fast = float(sensor_pin.value)
_ema_slow = _ema_fast
ALPHA_FAST = 0.1
ALPHA_SLOW = 0.002
DELTA_THRESHOLD = 70  # empirically derived: standby noise peaks ~35 (1σ), coin drop sustains ~90-107
SUSTAINED_COUNT = 5   # consecutive samples above threshold required — filters 1-3 sample noise blips
DEBOUNCE_S = 3.0
_last_event_t = -DEBOUNCE_S
_above_count = 0


def read_sensor():
    global _ema_fast, _ema_slow
    raw = sensor_pin.value
    _ema_fast = ALPHA_FAST * raw + (1 - ALPHA_FAST) * _ema_fast
    _ema_slow = ALPHA_SLOW * raw + (1 - ALPHA_SLOW) * _ema_slow
    delta = _ema_fast - _ema_slow
    return raw, _ema_fast, _ema_slow, delta


# ── strip layout ───────────────────────────────────────────────────────────────
def pixel_xy(i):
    """Map linear APA102 index to (col, row), origin bottom-left.

    Col 0 (left):  pixels 0‥28, row increases upward.
    Col 1 (right): pixels 29‥56, row decreases downward (snake).
    Col 1 is one pixel shorter, so its bottom is at row 1.
    """
    if i < COL_HEIGHTS[0]:
        return 0, i
    else:
        return 1, COL_HEIGHTS[0] - 1 - (i - COL_HEIGHTS[0])


# ── color helper ───────────────────────────────────────────────────────────────
def hsv(h, s=1.0, v=1.0):
    c = gamma_adjust(CHSV(h % 1.0, s, v))
    return (int(c.red * 255), int(c.green * 255), int(c.blue * 255))


# ── thank-you animation ────────────────────────────────────────────────────────
THANKYOU_COLOR = hsv(0.13, 1.0, 1.0)  # warm gold

comet_apa = Comet(
    pixels_apa, speed=0.02, color=THANKYOU_COLOR, tail_length=12, bounce=False
)
comet_ws = Comet(
    pixels_ws, speed=0.02, color=THANKYOU_COLOR, tail_length=8, bounce=False
)

# ── state machine ──────────────────────────────────────────────────────────────
STATE_STANDBY = 0
STATE_THANKYOU = 1
state = STATE_STANDBY


def _reseed_emas():
    global _ema_fast, _ema_slow, _above_count
    _ema_fast = float(sensor_pin.value)
    _ema_slow = _ema_fast
    _above_count = 0


def _on_thankyou_done(animation):
    global state
    if animation.cycle_count >= 2:
        comet_apa.freeze()
        comet_ws.freeze()
        _reseed_emas()  # avoid delta spike when standby resumes
        state = STATE_STANDBY


comet_apa.add_cycle_complete_receiver(_on_thankyou_done)
comet_apa.freeze()
comet_ws.freeze()


def start_thankyou():
    global state
    comet_apa.reset()
    comet_apa.cycle_count = 0
    comet_ws.reset()
    comet_ws.cycle_count = 0
    comet_apa.resume()
    comet_ws.resume()
    state = STATE_THANKYOU


# ── plasma standby ─────────────────────────────────────────────────────────────
_PLASMA_SPEED = 0.4
_PLASMA_SCALE = 4.0
_PLASMA_VALUE = 0.3  # tune to taste


def plasma_frame(t):
    # APA102: use real 2D (col, row) coordinates for spatial variation
    max_row = COL_HEIGHTS[0] - 1  # 28
    for i in range(NUM_APA):
        col, row = pixel_xy(i)
        x = col  # 0.0 or 1.0 — sin(x*π) inverts phase between columns
        y = row / max_row  # 0.0 .. 1.0
        hue = (
            math.sin(x * math.pi + y * _PLASMA_SCALE + t * _PLASMA_SPEED) * 0.25
            + math.sin(y * 2.0 + t * 0.23) * 0.15
            + t * 0.04
        )
        pixels_apa[i] = hsv(hue, 1.0, _PLASMA_VALUE)
    pixels_apa.show()

    # WS2812B: 1D plasma
    n = len(pixels_ws)
    for i in range(n):
        hue = (
            math.sin(i / n * _PLASMA_SCALE + t * _PLASMA_SPEED) * 0.25
            + math.sin(t * 0.23 + i / n * 2.0) * 0.15
            + t * 0.04
        )
        pixels_ws[i] = hsv(hue, 1.0, _PLASMA_VALUE)
    pixels_ws.show()


# ── main ───────────────────────────────────────────────────────────────────────
print("PixelDonation - ready")

while True:
    now = time.monotonic()

    if state == STATE_STANDBY:
        raw, filtered, baseline, delta = read_sensor()
        event = 0

        if abs(delta) > DELTA_THRESHOLD:
            _above_count += 1
        else:
            _above_count = 0

        if _above_count >= SUSTAINED_COUNT and (now - _last_event_t) > DEBOUNCE_S:
            _last_event_t = now
            _above_count = 0
            event = 1
            start_thankyou()

        if dataio:
            dataio.write(
                f"{raw};{filtered:.0f};{baseline:.0f};{delta:.0f};{event};\r\n".encode()
            )

        plasma_frame(now)
    else:
        comet_apa.animate()
        comet_ws.animate()

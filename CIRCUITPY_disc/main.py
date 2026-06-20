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

# ── hardware ───────────────────────────────────────────────────────────────────
# APA102 strip is physically folded: col 0 goes up (29 px), col 1 goes down (28 px)
COL_HEIGHTS = (29, 28)
NUM_APA = sum(COL_HEIGHTS)  # 57
NUM_WS = 64

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
dataio = usb_cdc.console

# ── sensor / event detection ───────────────────────────────────────────────────
# Adaptive baseline + delta detection:
#   - Slow EMA tracks ambient light drift (alpha ~0.005, tau ~2 s at ~100 Hz loop)
#   - Baseline is frozen while coin_in=True so dips don't pull it down
#   - coin_in fires when raw drops more than COIN_DIP_THRESHOLD below baseline
#   - Event fires on the RISING EDGE (coin leaves sensor)
#   - If coin_in stays True for > AMBIENT_RESEED_S, ambient light shifted → reseed baseline
EMA_ALPHA = 0.005           # baseline time constant ~200 samples
COIN_DIP_THRESHOLD = 2500   # raw must fall this far below baseline to register
COIN_RISE_MARGIN = 1000     # hysteresis: rising edge when raw > baseline − COIN_RISE_MARGIN
DEBOUNCE_S = 0.5
AMBIENT_RESEED_S = 2.0      # stuck coin_in longer than this → ambient shift, reseed

_baseline = None            # initialised from first sensor reading
_coin_in = False
_last_event_t = -DEBOUNCE_S
_coin_in_start = 0.0


# ── strip layout ───────────────────────────────────────────────────────────────
def pixel_xy(i):
    """Map linear APA102 index to (col, row), origin bottom-left.

    Col 0 (left):  pixels 0‥28, row increases upward.
    Col 1 (right): pixels 29‥56, row decreases downward (snake).
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
THANKYOU_HUE = 0.13      # warm gold
THANKYOU_DURATION = 4.0  # seconds

# APA102: comet rising from bottom to top on both columns simultaneously
_APA_SWEEP_SPEED = 18.0  # rows per second (~1.6 s per pass over 28 rows)
_APA_SWEEP_TAIL = 8      # rows of fading tail below the head


def apa_thankyou_frame(elapsed):
    max_row = COL_HEIGHTS[0] - 1  # 28
    head = (elapsed * _APA_SWEEP_SPEED) % (max_row + _APA_SWEEP_TAIL + 2)
    for i in range(NUM_APA):
        _col, row = pixel_xy(i)
        dist = head - row
        if 0 <= dist < _APA_SWEEP_TAIL:
            pixels_apa[i] = hsv(THANKYOU_HUE, 1.0, 1.0 - dist / _APA_SWEEP_TAIL)
        else:
            pixels_apa[i] = (0, 0, 0)
    pixels_apa.show()


# WS2812B: multiple gold segments chasing around the ring
_WS_SEGMENTS = 4     # evenly-spaced segments
_WS_SEG_LEN = 5      # lit pixels per segment (including head)
_WS_CHASE_SPEED = 32.0  # pixels per second (~2 s per revolution)


def ws_chase_frame(elapsed):
    offset = int(elapsed * _WS_CHASE_SPEED) % NUM_WS
    pixels_ws.fill((0, 0, 0))
    step = NUM_WS // _WS_SEGMENTS
    for seg in range(_WS_SEGMENTS):
        head = (offset + seg * step) % NUM_WS
        for j in range(_WS_SEG_LEN):
            v = 1.0 - j / _WS_SEG_LEN
            pixels_ws[(head - j) % NUM_WS] = hsv(THANKYOU_HUE, 1.0, v)
    pixels_ws.show()


# ── state machine ──────────────────────────────────────────────────────────────
STATE_STANDBY = 0
STATE_THANKYOU = 1
state = STATE_STANDBY
_thankyou_start_t = 0.0


def start_thankyou():
    global state, _thankyou_start_t, _coin_in
    _thankyou_start_t = time.monotonic()
    _coin_in = False
    state = STATE_THANKYOU


def end_thankyou():
    global state, _coin_in
    pixels_apa.fill((0, 0, 0))
    pixels_apa.show()
    pixels_ws.fill((0, 0, 0))
    pixels_ws.show()
    _coin_in = False
    state = STATE_STANDBY


# ── plasma standby ─────────────────────────────────────────────────────────────
_PLASMA_SPEED = 0.4
_PLASMA_SCALE = 4.0
_PLASMA_VALUE = 0.3


def plasma_frame(t):
    max_row = COL_HEIGHTS[0] - 1  # 28
    for i in range(NUM_APA):
        col, row = pixel_xy(i)
        x = col            # 0 or 1 — gentle 1-radian phase shift between columns
        y = row / max_row  # 0.0 .. 1.0
        hue = (
            math.sin(x + y * _PLASMA_SCALE + t * _PLASMA_SPEED) * 0.25
            + math.sin(y * 2.0 + t * 0.23) * 0.15
            + t * 0.04
        )
        pixels_apa[i] = hsv(hue, 1.0, _PLASMA_VALUE)
    pixels_apa.show()

    n = NUM_WS
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

    raw = sensor_pin.value
    event = 0

    if _baseline is None:
        _baseline = float(raw)

    delta = raw - int(_baseline)

    if not _coin_in:
        _baseline += EMA_ALPHA * (raw - _baseline)
        if delta < -COIN_DIP_THRESHOLD:
            _coin_in = True
            _coin_in_start = now
    else:
        if delta >= -COIN_RISE_MARGIN:
            _coin_in = False
            if (now - _last_event_t) > DEBOUNCE_S:
                _last_event_t = now
                event = 1
                if state == STATE_STANDBY:
                    start_thankyou()
        elif (now - _coin_in_start) > AMBIENT_RESEED_S:
            _baseline = float(raw)
            _coin_in = False

    if dataio:
        dataio.write(f"{raw};{int(_baseline)};{delta};{event};{int(_coin_in)};{state};\r\n".encode())

    if state == STATE_STANDBY:
        plasma_frame(now)
    else:
        elapsed = now - _thankyou_start_t
        if elapsed >= THANKYOU_DURATION:
            end_thankyou()
        else:
            apa_thankyou_frame(elapsed)
            ws_chase_frame(elapsed)

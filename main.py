#!/usr/bin/env python3
"""Draw a one-image broadsheet summary of the world news of
Thursday 19 November 2026 and write it to /output/entry.png
(falling back to ./entry.png when /output is unavailable).

Pure Python standard library: the picture is rendered pixel by
pixel into a frame buffer and encoded as a PNG with zlib.
No network, no clock, no randomness - every run is identical.
"""

import binascii
import os
import struct
import zlib

W = 1024
H = 1024
MX = 36                      # side margin
RIGHT = W - MX               # right edge of the content column

PAPER = (247, 243, 233)
INK = (28, 26, 22)
ACCENT = (148, 32, 26)
GRAY = (122, 116, 106)
POLE = (90, 86, 80)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- font
# A 5x7 bitmap font, drawn in code.  '#' marks a filled cell.
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#####", "...#.", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '$': ("..#..", ".####", "#.#.#", ".###.", "#.#.#", "####.", "..#.."),
    '%': ("##..#", "##..#", "....#", "...#.", "..#..", ".#...", "#..##"),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '•': (".....", ".....", ".###.", ".###.", ".###.", ".....", "....."),
    '°': (".##..", "#..#.", ".##..", ".....", ".....", ".....", "....."),
    '—': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
}

# ---------------------------------------------------------------- text
MASTHEAD = "THE WORLD IN ONE PICTURE"
DATELINE = "Thursday 19 November 2026"
LEAD_HEADLINE = ("TRUMP, XI, PUTIN", "MEET FACE TO FACE")
LEAD_SUMMARY = (
    "First-ever trilateral summit in Shenzhen issues a joint peace "
    "declaration — UN reform, nuclear-risk talks, 'a nuclear war "
    "cannot be won' — but no breakthrough on Ukraine."
)
PANELS = [
    ("WORLD COURT: MYANMAR COMMITTED GENOCIDE",
     "ICJ rules the 2017 campaign against the Rohingya was "
     "state-sponsored genocide; orders reparations and return "
     "of the displaced."),
    ("UKRAINE HITS KERCH BRIDGE A THIRD TIME",
     "Overnight strike suspends rail traffic hours before the "
     "summit; Kyiv claims Neptune missiles, Moscow says drones."),
    ("ANTHROPIC'S RECORD IPO, MARKETS SLIDE",
     "Claude-maker debuts near a $1.5 trillion valuation and "
     "briefly tops $2 trillion; US stocks fall 2% to "
     "seven-month lows."),
    ("COP31 DRAFT DROPS FOSSIL-FUEL PHASEOUT",
     "Antalya draft strips out phaseout language and admits "
     "a 1.5°C overshoot ahead of Friday's deadline."),
    ("BANGLADESH SHUTS DOWN IN PROTESTS",
     "Awami League lockdown: two killed, blasts and arson "
     "across at least 28 districts."),
    ("SENATE BACKS TRUMP ON IRAN WAR",
     "War-powers resolution rejected 51-48; Congress will not "
     "force an end to the war."),
]
TICKER_ITEMS = [
    "MIGRANT BOAT CAPSIZES OFF SENEGAL, DOZENS MISSING",
    "INDONESIA FIRE EMISSIONS THIRD-HIGHEST ON RECORD",
    "DENMARK RATIFIES GREENLAND DEFENCE DEAL 109-0",
    "NEW PULSAR SPINS 261 TIMES A SECOND",
]

# ---------------------------------------------------------------- canvas
buf = bytearray(bytes(PAPER) * (W * H))


def rect(x, y, w, h, color):
    if w <= 0 or h <= 0:
        return
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        off = (yy * W + x0) * 3
        buf[off:off + len(row)] = row


def frame(x, y, w, h, color):
    rect(x, y, w, 1, color)
    rect(x, y + h - 1, w, 1, color)
    rect(x, y, 1, h, color)
    rect(x + w - 1, y, 1, h, color)


def circle(cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                if 0 <= xx < W and 0 <= yy < H:
                    off = (yy * W + xx) * 3
                    buf[off:off + 3] = bytes(color)


def text_width(text, scale, adv=None):
    if not text:
        return 0
    if adv is None:
        adv = 6 * scale
    return len(text) * adv - (adv - 5 * scale)


def draw_text(x, y, text, scale, color, bold=False, adv=None):
    if adv is None:
        adv = 6 * scale
    text = text.upper()
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[' '])
        for row_i, row in enumerate(glyph):
            for col_i, cell in enumerate(row):
                if cell == '#':
                    gx = cx + col_i * scale
                    gy = y + row_i * scale
                    rect(gx, gy, scale, scale, color)
                    if bold:
                        rect(gx + 1, gy, scale, scale, color)
        cx += adv
    return cx


def draw_text_centered(y, text, scale, color, bold=False, adv=None):
    w = text_width(text.upper(), scale, adv)
    return draw_text((W - w) // 2, y, text, scale, color, bold, adv)


def wrap(text, max_chars):
    """Greedy word wrap, then tighten the limit so the same number
    of lines comes out as evenly filled as possible."""
    words = text.upper().split()

    def greedy(limit):
        lines, cur = [], ""
        for word in words:
            if not cur:
                cur = word
            elif len(cur) + 1 + len(word) <= limit:
                cur = cur + " " + word
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    count = len(greedy(max_chars))
    lo, hi = 1, max_chars
    while lo < hi:
        mid = (lo + hi) // 2
        if len(greedy(mid)) <= count:
            hi = mid
        else:
            lo = mid + 1
    return greedy(lo)


def draw_paragraph(x, y, text, scale, max_chars, color, step):
    lines = wrap(text, max_chars)
    for line in lines:
        draw_text(x, y, line, scale, color)
        y += step
    return y


# ---------------------------------------------------------------- motif
def draw_flags(x, y):
    """Three summit flags on poles: United States, China, Russia."""
    fw, fh = 62, 40
    for i, pole_x in enumerate((x + 16, x + 96, x + 176)):
        rect(pole_x, y, 4, 128, POLE)
        fx = pole_x + 4
        if i == 0:      # United States: stripes and a blue canton
            stripe_h = (6, 6, 6, 6, 6, 5, 5)
            sy = y
            for j, sh in enumerate(stripe_h):
                c = (176, 36, 48) if j % 2 == 0 else WHITE
                rect(fx, sy, fw, sh, c)
                sy += sh
            rect(fx, y, 28, 21, (58, 56, 110))
            for r in range(4):
                for c in range(5):
                    rect(fx + 3 + c * 5, y + 3 + r * 5, 2, 2, WHITE)
        elif i == 1:    # China: red field, yellow stars
            rect(fx, y, fw, fh, (216, 40, 20))
            circle(fx + 11, y + 11, 5, (255, 220, 0))
            for dx, dy in ((22, 5), (25, 11), (25, 18), (22, 24)):
                circle(fx + dx, y + dy, 2, (255, 220, 0))
        else:           # Russia: white, blue, red bands
            rect(fx, y, fw, 13, WHITE)
            rect(fx, y + 13, fw, 14, (0, 57, 166))
            rect(fx, y + 27, fw, 13, (213, 0, 50))
        frame(fx, y, fw, fh, POLE)
    rect(x + 8, y + 128, 224, 2, GRAY)


# ---------------------------------------------------------------- page
def draw_page():
    # top double rule
    rect(MX, 18, RIGHT - MX, 4, INK)
    rect(MX, 27, RIGHT - MX, 2, INK)

    # masthead and date
    draw_text_centered(42, MASTHEAD, 6, INK, bold=True)
    draw_text_centered(98, DATELINE, 4, ACCENT, bold=True)
    rect(MX, 140, RIGHT - MX, 3, INK)
    rect(MX, 148, RIGHT - MX, 1, INK)

    # lead story
    draw_text_centered(166, LEAD_HEADLINE[0], 7, INK, bold=True)
    draw_text_centered(224, LEAD_HEADLINE[1], 7, INK, bold=True)
    rect((W - 140) // 2, 286, 140, 5, ACCENT)
    draw_flags(MX, 308)
    draw_paragraph(300, 308, LEAD_SUMMARY, 3, 38, INK, 29)
    rect(MX, 468, RIGHT - MX, 2, INK)

    # six panels in two columns and three rows
    col_x = (MX, 536)
    row_y = (486, 634, 782)
    for idx, (headline, summary) in enumerate(PANELS):
        px = col_x[idx % 2]
        py = row_y[idx // 2]
        rect(px, py, 5, 48, ACCENT)
        tx = px + 14
        lines = wrap(headline, 24)
        hy = py
        for line in lines:
            draw_text(tx, hy, line, 3, INK, bold=True)
            hy += 27
        draw_paragraph(tx, py + 56, summary, 2, 36, INK, 19)
    rect(512, 486, 1, 436, GRAY)
    rect(MX, 622, RIGHT - MX, 1, GRAY)
    rect(MX, 770, RIGHT - MX, 1, GRAY)

    # a fine double frame around the whole page (the ticker band
    # is drawn over its foot, so the frame ends at the band)
    frame(10, 10, W - 20, H - 20, INK)
    frame(11, 11, W - 22, H - 22, INK)

    # ticker band along the foot of the page
    rect(0, 944, W, 3, ACCENT)
    rect(0, 947, W, H - 947, INK)
    line1 = TICKER_ITEMS[0] + " • " + TICKER_ITEMS[1]
    line2 = TICKER_ITEMS[2] + " • " + TICKER_ITEMS[3]
    draw_text_centered(962, line1, 2, PAPER, adv=10)
    draw_text_centered(990, line2, 2, PAPER, adv=10)


# ---------------------------------------------------------------- png
def write_png(path):
    raw = bytearray()
    row_len = W * 3
    for yy in range(H):
        raw.append(0)
        raw += buf[yy * row_len:(yy + 1) * row_len]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack('>I', len(data)) + kind + data
        out += struct.pack('>I', binascii.crc32(kind + data) & 0xFFFFFFFF)
        return out

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', comp)
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as fh:
        fh.write(png)


def output_path():
    out_dir = '/output'
    if os.path.isdir(out_dir):
        candidate = os.path.join(out_dir, 'entry.png')
        try:
            with open(candidate, 'ab'):
                pass
            return candidate
        except OSError:
            pass
    return os.path.join('.', 'entry.png')


def main():
    draw_page()
    write_png(output_path())


if __name__ == '__main__':
    main()

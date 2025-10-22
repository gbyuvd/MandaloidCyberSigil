#!/usr/bin/env python3
# mandaloid_sigil.py
import math
import hashlib
import sys
import os
import time
from typing import List, Tuple

# Optional: try to import Pillow for GIF support
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    pass

# ---------- config ----------
CHARS = " ○◦✧•∘*+◉◎◈⬢⊡"
DEFAULT_SIZE = 21      # ← changed from 25 to 21 as requested
HASH_LEN = 25          # keep at 25
# ----------------------------

Vec = Tuple[float, float]

def text_to_seed(text: str) -> bytes:
    """Deterministic seed from any string."""
    return hashlib.blake2b(text.encode(), digest_size=HASH_LEN).digest()

def byte_to_float(b: bytes) -> float:
    """Map 4 bytes → 0…1"""
    return int.from_bytes(b, 'big') / 0xffffffff

class Mandala:
    def __init__(self, seed: bytes, size: int):
        # unpack seed into parameters
        self.sym   = 4 + (seed[0]  & 7)   # 4–11 fold symmetry
        self.rings = 3 + (seed[1]  & 3)   # 3–6 rings
        self.depth = 2 + (seed[2]  & 1)   # 2–3 recursion depth
        self.spin  = byte_to_float(seed[4:8])
        self.fat   = 0.3 + 0.4 * byte_to_float(seed[8:12])
        # Use passed size
        self.size  = size
        self.c     = self.size // 2
        self.grid  = [[' ' for _ in range(self.size)] for _ in range(self.size)]
        self.build()

    # ---------- geometry helpers ----------
    def rot(self, v: Vec, a: float) -> Vec:
        c, s = math.cos(a), math.sin(a)
        return (v[0]*c - v[1]*s, v[0]*s + v[1]*c)

    def to_px(self, v: Vec) -> Tuple[int, int]:
        x = int(round(self.c + v[0]))
        y = int(round(self.c - v[1]))  # y grows downward
        return x, y

    def plot(self, v: Vec, char: str):
        x, y = self.to_px(v)
        if 0 <= x < self.size and 0 <= y < self.size:
            if self.grid[y][x] == ' ':
                self.grid[y][x] = char

    # ---------- fractal motif ----------
    def motif(self, centre: Vec, radius: float, angle: float, lvl: int):
        if radius < 0.6 or lvl < 0:
            return
        char = CHARS[lvl % len(CHARS)]
        for k in range(8):
            pet_angle = angle + k * math.pi/4 + self.spin * math.pi
            tip = self.rot((0, radius), pet_angle)
            steps = max(3, int(radius))
            for i in range(steps):
                r = radius * (i / steps)
                p = self.rot((0, r), pet_angle)
                self.plot((centre[0] + p[0], centre[1] + p[1]), char)
            self.motif(
                (centre[0] + tip[0], centre[1] + tip[1]),
                radius * self.fat,
                angle + self.spin,
                lvl - 1
            )

    # ---------- full build ----------
    def build(self):
        max_r = self.c * 0.85
        for ring in range(self.rings):
            r = max_r * (1 - ring / self.rings)
            for s in range(self.sym):
                a = s * 2 * math.pi / self.sym
                pos = (r * math.cos(a), r * math.sin(a))
                self.motif(pos, r / 4, a, self.depth)
        self.plot((0, 0), CHARS[-1])

    # ---------- export ----------
    def __str__(self):
        return '\n'.join(''.join(row) for row in self.grid)

# ---------- utilities ----------
def mandaloid_sigil(text: str, size: int) -> str:
    seed = text_to_seed(text)
    return str(Mandala(seed, size=size))

def text_to_image(grid: List[List[str]]) -> 'Image.Image':
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow (PIL) is required to generate GIFs. Install with: pip install Pillow")
    
    # Use a fixed square character size (e.g., 12x12 pixels)
    char_size = 12  # ← key: make it square!

    height = len(grid)
    width = len(grid[0]) if height else 0
    img_w = width * char_size
    img_h = height * char_size  # ← same as width per cell

    img = Image.new("RGB", (img_w, img_h), "black")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", int(char_size * 0.8))
    except OSError:
        try:
            font = ImageFont.truetype("Consolas.ttf", int(char_size * 0.8))
        except OSError:
            try:
                font = ImageFont.truetype("Courier New.ttf", int(char_size * 0.8))
            except OSError:
                font = ImageFont.load_default()

    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != ' ':
                # Center the character in the square cell
                draw.text((x * char_size, y * char_size), ch, fill="white", font=font)
    return img

def save_sigil_gif(base_text: str, size: int, gif_path: str, delay_ms: int = 200):
    print(f"Generating {size} frames for GIF...")
    frames = []
    for i in range(1, size + 1):
        seed_text = f"{base_text} {i}"
        mandala = Mandala(text_to_seed(seed_text), size=size)  # ✅ pass size!
        img = text_to_image(mandala.grid)
        frames.append(img)
        print(f"Frame {i}/{size} rendered")

    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=delay_ms,
        loop=0
    )
    print(f"GIF saved to: {gif_path}")

def animate_hash_sequence(base_text: str, size: int, delay: float = 0.25):
    print("Ctrl+C to stop")
    try:
        frame = 1
        while True:
            seed_text = f"{base_text} {frame}"
            sigil = mandaloid_sigil(seed_text, size=size)  # ✅ pass size!
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"Seed: {repr(seed_text)}  (frame {frame}/{size})")
            print(sigil)
            time.sleep(delay)
            frame = 1 if frame >= size else frame + 1
    except KeyboardInterrupt:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Animation stopped.")
        sys.exit(0)

# ---------- main ----------
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate or animate mystical ASCII sigils from text.",
        epilog="Example: python mandaloid_sigil.py --animate-hash --size 30 'chaos'",
    )
    parser.add_argument("text", nargs="*", default=["though they are far"],
                        help="Base text for sigil generation (default: 'though they are far')")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE,
                        help=f"Canvas size (must be odd, default: {DEFAULT_SIZE})")
    parser.add_argument("--animate-hash", action="store_true",
                        help="Animate sigils: base_text + ' 1', ' 2', ..., looping")
    parser.add_argument("--gif", metavar="FILE.gif",
                        help="Save animation as GIF (requires Pillow)")

    args = parser.parse_args()
    base_text = " ".join(args.text)
    size = args.size

    if size % 2 == 0:
        print("Warning: SIZE should be odd for perfect center. Adding 1.", file=sys.stderr)
        size += 1

    try:
        if args.gif:
            if not PIL_AVAILABLE:
                print("Error: Pillow is required for GIF export. Install with: pip install Pillow", file=sys.stderr)
                sys.exit(1)
            save_sigil_gif(base_text, size, args.gif, delay_ms=250)
        elif args.animate_hash:
            animate_hash_sequence(base_text, size=size, delay=0.25)
        else:
            print(mandaloid_sigil(base_text, size=size))
    except KeyboardInterrupt:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Animation stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
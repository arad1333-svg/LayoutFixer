"""
generate_icon.py — One-time script to generate the LayoutFixer app icon.

Design: "The Swap" (Kinetic Terminal, matches docs/index.html): a muted grey
Hebrew א fading behind a glowing LED-green A on a dark rounded square with a
faint green grid — a freeze-frame of the landing page's letter-factory
animation.

Outputs (into this directory):
  icon.png  — 1024x1024 master (also used by the tray/menu-bar icon)
  icon.ico  — multi-size Windows icon
  icon.icns is produced separately from icon.png with:
      sips -s format icns icon.png --out icon.icns

Run from the assets/ directory: python3 generate_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 1024
# Apple Big Sur icon grid: 824x824 rounded square centered on a 1024 canvas
INSET = 100
RADIUS = 185

# Kinetic Terminal palette (see CLAUDE.md / docs/index.html)
PRIMARY = (142, 255, 113)          # #8eff71
GLOW = (57, 255, 20)               # glow tint used across the website
SURFACE = (14, 14, 14)             # #0e0e0e
SURFACE_CONTAINER = (26, 25, 25)   # #1a1919
MUTED = (173, 170, 170)            # #adaaaa

# (path, collection-index) candidates per glyph role, first existing wins
FONTS_HEBREW_BOLD = [
    ('/System/Library/Fonts/Supplemental/ArialHB.ttc', 1),        # macOS
    ('C:/Windows/Fonts/arialbd.ttf', 0),                          # Windows
    ('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 0),
]
FONTS_LATIN_BLACK = [
    ('/System/Library/Fonts/Supplemental/Arial Black.ttf', 0),    # macOS
    ('C:/Windows/Fonts/ariblk.ttf', 0),                           # Windows
    ('C:/Windows/Fonts/arialbd.ttf', 0),
]


def _font(candidates, px):
    for path, idx in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, px, index=idx)
    raise OSError(f'None of the candidate fonts exist: {candidates}')


def _base_plate():
    """Dark squircle: vertical gradient, faint green grid, ambient glow, border."""
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))

    grad = Image.new('RGBA', (SIZE, SIZE))
    gd = ImageDraw.Draw(grad)
    for y in range(SIZE):
        t = y / SIZE
        c = tuple(int(SURFACE_CONTAINER[i] + (SURFACE[i] - SURFACE_CONTAINER[i]) * t)
                  for i in range(3))
        gd.line([(0, y), (SIZE, y)], fill=c + (255,))

    grid = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    gdr = ImageDraw.Draw(grid)
    for p in range(128, SIZE, 128):
        gdr.line([(p, 0), (p, SIZE)], fill=PRIMARY + (14,), width=2)
        gdr.line([(0, p), (SIZE, p)], fill=PRIMARY + (14,), width=2)
    grad.alpha_composite(grid)

    blob = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(blob).ellipse(
        [SIZE * 0.15, SIZE * 0.05, SIZE * 0.85, SIZE * 0.55], fill=GLOW + (26,))
    grad.alpha_composite(blob.filter(ImageFilter.GaussianBlur(120)))

    mask = Image.new('L', (SIZE, SIZE), 0)
    box = (INSET, INSET, SIZE - INSET, SIZE - INSET)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=RADIUS, fill=255)
    img.paste(grad, (0, 0), mask)

    ImageDraw.Draw(img).rounded_rectangle(
        box, radius=RADIUS, outline=PRIMARY + (60,), width=4)
    return img


def _glow_layer(render_fn, blur_wide=45, blur_tight=14, alpha_wide=110, alpha_tight=160):
    """Render green art via render_fn(draw), doubled-blurred behind it for LED glow."""
    art = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    render_fn(ImageDraw.Draw(art))

    solid = art.split()[3]
    wide = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    wide.paste(Image.new('RGBA', (SIZE, SIZE), GLOW + (255,)), (0, 0), solid)
    tight = wide.copy()
    wide = wide.filter(ImageFilter.GaussianBlur(blur_wide))
    tight = tight.filter(ImageFilter.GaussianBlur(blur_tight))
    wide.putalpha(wide.split()[3].point(lambda a: a * alpha_wide // 255))
    tight.putalpha(tight.split()[3].point(lambda a: a * alpha_tight // 255))

    out = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    out.alpha_composite(wide)
    out.alpha_composite(tight)
    out.alpha_composite(art)
    return out


def make_icon() -> Image.Image:
    img = _base_plate()

    # Muted grey aleph behind — the "wrong layout" letter fading out
    heb = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(heb).text(
        (SIZE * 0.41, SIZE * 0.42), 'א',
        font=_font(FONTS_HEBREW_BOLD, 500), fill=MUTED + (95,), anchor='mm')
    img.alpha_composite(heb)

    # Glowing green A in front — the fixed letter
    fnt = _font(FONTS_LATIN_BLACK, 470)
    img.alpha_composite(_glow_layer(
        lambda d: d.text((SIZE * 0.55, SIZE * 0.57), 'A',
                         font=fnt, fill=PRIMARY + (255,), anchor='mm')))
    return img


def main():
    out_dir = Path(__file__).parent
    img = make_icon()

    png_path = out_dir / 'icon.png'
    img.save(png_path, 'PNG')
    print(f'Saved {png_path}')

    ico_path = out_dir / 'icon.ico'
    img.save(ico_path, format='ICO',
             sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
    print(f'Saved {ico_path}')


if __name__ == '__main__':
    main()

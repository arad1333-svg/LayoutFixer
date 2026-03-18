"""
generate_icon.py — One-time script to generate icon.png and icon.ico.
Run from the assets/ directory: python generate_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def make_icon(size: int = 256) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark background circle
    draw.ellipse([0, 0, size, size], fill=(30, 30, 46, 255))

    # Blue inner circle
    margin = size // 10
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(59, 130, 246, 255),
    )

    # "LF" text
    try:
        font_size = size // 3
        font = ImageFont.truetype('segoeui.ttf', font_size)
    except OSError:
        font = ImageFont.load_default()

    draw.text(
        (size // 2, size // 2),
        'LF',
        fill='white',
        font=font,
        anchor='mm',
    )

    return img


def main():
    out_dir = Path(__file__).parent
    img = make_icon(256)

    # Save PNG
    png_path = out_dir / 'icon.png'
    img.save(png_path, 'PNG')
    print(f'Saved {png_path}')

    # Save multi-size ICO
    ico_path = out_dir / 'icon.ico'
    sizes = [16, 32, 48, 64, 128, 256]
    icons = [make_icon(s) for s in sizes]
    icons[0].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:],
    )
    print(f'Saved {ico_path}')


if __name__ == '__main__':
    main()

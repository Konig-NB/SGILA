from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF = Path(r"C:\Users\mtsha\Downloads\Colorful Coloring Book Cover A4 Document.pdf")
OUT = ROOT / "static" / "img" / "lerato"
EXTRACTED = OUT / "extracted"


def load_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def extract_pdf_images():
    OUT.mkdir(parents=True, exist_ok=True)
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(PDF))
    for page_number, page in enumerate(reader.pages, 1):
        for image_number, image in enumerate(page.images, 1):
            ext = Path(image.name).suffix or ".png"
            target = EXTRACTED / f"p{page_number:02d}_{image_number:02d}{ext}"
            target.write_bytes(image.data)


def open_image(name):
    return Image.open(EXTRACTED / name).convert("RGBA")


def cover_background(size):
    bg = Image.new("RGBA", size, "#fff8ef")
    draw = ImageDraw.Draw(bg)
    for y in range(0, size[1], 42):
        color = "#fff4c7" if (y // 42) % 2 == 0 else "#d7f8f6"
        draw.rounded_rectangle([24, y + 14, size[0] - 24, y + 36], radius=14, fill=color)
    try:
        pattern = open_image("p01_01.jpg")
        pattern = pattern.resize(size)
        bg = Image.blend(bg, pattern, 0.18)
    except FileNotFoundError:
        pass
    return bg


def paste_contained(canvas, image, box):
    x, y, w, h = box
    image = image.copy()
    image.thumbnail((w, h), Image.LANCZOS)
    px = x + (w - image.width) // 2
    py = y + (h - image.height) // 2
    canvas.alpha_composite(image, (px, py))


def label(draw, xy, text, fill="#14213d", size=44, bold=True):
    draw.text(xy, text, fill=fill, font=load_font(size, bold))


def make_story_image(filename, title, sentence, main_image_name, accent="#ffd22e", side_image_name=None):
    canvas = cover_background((1200, 760))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([60, 60, 1140, 700], radius=52, fill=(255, 255, 255, 226))
    draw.rounded_rectangle([60, 60, 1140, 92], radius=18, fill=accent)
    label(draw, (100, 122), title, size=54)
    draw.text((104, 190), sentence, fill="#59647f", font=load_font(30, False), spacing=8)

    main = open_image(main_image_name)
    paste_contained(canvas, main, (92, 286, 460, 360))

    if side_image_name:
        side = open_image(side_image_name)
        paste_contained(canvas, side, (620, 270, 420, 330))

    for idx, (word, color) in enumerate([("apple", "#ff5a66"), ("banana", "#ffd22e"), ("orange", "#ff9f1c"), ("mango", "#31ca83")]):
        x = 625 + (idx % 2) * 190
        y = 520 + (idx // 2) * 76
        draw.rounded_rectangle([x, y, x + 150, y + 48], radius=24, fill=color)
        draw.text((x + 24, y + 13), word, fill="#14213d" if word != "apple" else "#ffffff", font=load_font(20, True))

    canvas.convert("RGB").save(OUT / filename, quality=94)


def copy_fruit_assets():
    mapping = {
        "fruit_basket.png": "p01_04.png",
        "fruit_watermelon.png": "p01_05.png",
        "fruit_orange.png": "p01_06.png",
        "fruit_banana.png": "p07_01.png",
        "fruit_apple.png": "p07_02.jpg",
        "lerato_basket.png": "p02_01.png",
        "lerato_market.png": "p03_01.png",
        "lerato_eating.png": "p04_01.png",
    }
    for target, source in mapping.items():
        image = open_image(source)
        image.save(OUT / target)


def make_cover():
    canvas = cover_background((1200, 760))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([70, 72, 1130, 688], radius=54, fill=(255, 255, 255, 224))
    label(draw, (115, 132), "Lerato's", size=70)
    label(draw, (115, 206), "Fruit Basket", size=78)
    draw.text((120, 306), "A colourful SGILA reading story", fill="#59647f", font=load_font(32, False))
    paste_contained(canvas, open_image("p01_04.png"), (620, 140, 420, 400))
    paste_contained(canvas, open_image("p02_01.png"), (170, 390, 220, 240))
    draw.rounded_rectangle([430, 552, 776, 620], radius=34, fill="#ffd22e")
    draw.text((488, 570), "Read with Koaly", fill="#14213d", font=load_font(30, True))
    canvas.convert("RGB").save(OUT / "cover.png", quality=94)


def main():
    if not PDF.exists():
        raise FileNotFoundError(PDF)
    extract_pdf_images()
    copy_fruit_assets()
    make_cover()
    make_story_image(
        "story_page_1.png",
        "Fruit at home",
        "Lerato has a basket with a red apple, a yellow banana, and a sweet orange.",
        "p02_01.png",
        "#ffd22e",
        "p01_04.png",
    )
    make_story_image(
        "story_page_2.png",
        "Mango at the market",
        "Her mother bought a juicy mango from the market.",
        "p03_01.png",
        "#5bdad4",
        "p01_04.png",
    )
    make_story_image(
        "story_page_3.png",
        "Healthy and strong",
        "Lerato eats fruit every day to stay healthy and strong.",
        "p04_01.png",
        "#a37cf3",
        "p01_06.png",
    )
    print(f"Built Lerato assets in {OUT}")


if __name__ == "__main__":
    main()

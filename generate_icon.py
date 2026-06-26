from PIL import Image, ImageDraw, ImageFont
import os

def create_ico(output_path="kino.ico"):
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = max(1, size // 16)
        radius = max(2, size // 8)
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=radius,
            fill=(30, 30, 30, 230)
        )
        font_size = max(8, size // 3)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "KL", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (size - tw) // 2
        y = (size - th) // 2
        draw.text((x, y), "KL", fill=(255, 255, 255), font=font)
        images.append(img)

    images[0].save(output_path, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(f"Icon saved: {output_path}")

if __name__ == "__main__":
    create_ico()

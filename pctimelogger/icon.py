"""The tray and exe icon: a white clock face on blue."""


def icon_image(size: int = 64):
    from PIL import Image, ImageDraw

    s = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    d.ellipse((4 * s, 4 * s, 60 * s, 60 * s), fill=(32, 110, 200, 255), outline=white, width=max(1, int(4 * s)))
    d.line((32 * s, 32 * s, 32 * s, 14 * s), fill=white, width=max(1, int(5 * s)))
    d.line((32 * s, 32 * s, 46 * s, 38 * s), fill=white, width=max(1, int(5 * s)))
    return img


if __name__ == "__main__":
    import sys

    icon_image(256).save(sys.argv[1] if len(sys.argv) > 1 else "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])

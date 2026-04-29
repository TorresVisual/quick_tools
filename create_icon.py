"""Generate a polished exe icon (lightning bolt style)."""
from pathlib import Path
from PIL import Image, ImageDraw

def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # === Background circle ===
    pad = max(1, size // 16)

    d.ellipse(
        (pad, pad, size - pad, size - pad),
        fill=(20, 20, 35, 255),
        outline=(255, 255, 255, 255),  # softer than pure white
        width=max(1, size // 32)
    )

    # === Subtle inner highlight (only visible on larger sizes) ===
    if size >= 64:
        highlight_pad = pad + size // 32
        d.ellipse(
            (highlight_pad, highlight_pad, size - highlight_pad, size // 2),
            fill=(255, 255, 255, 20)
        )

    # === Lightning bolt ===
    def P(x, y):
        return (int(x * size), int(y * size))

    bolt = [
        P(0.60, 0.10),
        P(0.25, 0.60),
        P(0.48, 0.60),
        P(0.36, 0.92),
        P(0.80, 0.40),
        P(0.58, 0.40),
    ]

    d.polygon(bolt, fill=(255, 255, 255, 255))

    return img


if __name__ == "__main__":
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [make_frame(s) for s in sizes]

    out = Path(__file__).parent / "quick_tools.ico"
    frames[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:]
    )

    print(f"Saved {out}")
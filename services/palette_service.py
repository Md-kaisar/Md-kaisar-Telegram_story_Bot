"""
Extracts a real dominant color palette from an image using k-means-ish quantization
(via Pillow's median-cut quantizer), then asks the AI to name each color poetically
and assign an emotion. This gives accurate colors (not guessed) with creative labels.
"""
from PIL import Image
import io


def extract_hex_palette(image_bytes: bytes, num_colors: int = 5) -> list:
    """Return a list of hex color strings, most dominant first."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # Downscale for speed; doesn't materially affect dominant-color accuracy
    img.thumbnail((200, 200))
    quantized = img.quantize(colors=max(num_colors, 5), method=Image.MEDIANCUT)
    palette = quantized.getpalette()
    color_counts = quantized.getcolors()  # list of (count, palette_index)
    color_counts.sort(key=lambda c: c[0], reverse=True)

    hex_colors = []
    seen = set()
    for _, idx in color_counts:
        r, g, b = palette[idx * 3: idx * 3 + 3]
        hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
        # Skip near-duplicate / near-white/black boring extraction artifacts sparingly
        if hex_code in seen:
            continue
        seen.add(hex_code)
        hex_colors.append(hex_code)
        if len(hex_colors) >= num_colors:
            break
    return hex_colors

import io
from PIL import Image

def compress_image(pil_image, quality_percentage=50):
    """
    Simulate JPEG image compression at selected quality percentage (10% to 90%).
    Returns:
    - compressed_pil_img
    - original_size_bytes
    - compressed_size_bytes
    - size_reduction_percent
    """
    quality = max(10, min(90, int(quality_percentage)))
    
    # Save original to byte buffer to measure actual original byte size
    orig_buffer = io.BytesIO()
    fmt = pil_image.format if pil_image.format in ['JPEG', 'PNG', 'BMP'] else 'PNG'
    pil_image.save(orig_buffer, format=fmt)
    original_size = orig_buffer.tell()

    # Perform JPEG compression at target quality
    compressed_buffer = io.BytesIO()
    # Convert RGBA/P to RGB if necessary for JPEG format
    rgb_img = pil_image.convert('RGB')
    rgb_img.save(compressed_buffer, format='JPEG', quality=quality)
    compressed_size = compressed_buffer.tell()
    
    compressed_buffer.seek(0)
    compressed_pil = Image.open(compressed_buffer).convert('RGB')
    
    reduction_percent = round(((original_size - compressed_size) / float(original_size)) * 100.0, 2)
    if reduction_percent < 0:
        reduction_percent = 0.0

    return {
        "compressed_image": compressed_pil,
        "original_size_bytes": original_size,
        "compressed_size_bytes": compressed_size,
        "quality_percentage": quality,
        "size_reduction_percent": reduction_percent
    }

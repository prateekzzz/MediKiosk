import qrcode
from PIL import Image
import io

def generate_qr_code(data: str) -> Image.Image:
    """Generate QR code from data"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def generate_abha_qr(abha_id: str, name: str = "") -> bytes:
    """Generate ABHA ID QR code"""
    data = f"ABHA:{abha_id}|NAME:{name}"
    img = generate_qr_code(data)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
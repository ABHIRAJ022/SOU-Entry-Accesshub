import base64
import binascii
from io import BytesIO

from PIL import Image, ImageStat, UnidentifiedImageError

MAX_SNAPSHOT_BYTES = 200 * 1024
Image.MAX_IMAGE_PIXELS = 4_000_000


class SnapshotError(Exception):
    pass


def process_webcam_snapshot(payload):
    if payload.get('capture_mode') != 'webcam':
        raise SnapshotError('Only live webcam capture is accepted.')
    try:
        raw = base64.b64decode(str(payload.get('image', '')).partition(',')[2], validate=True)
        with Image.open(BytesIO(raw)) as image:
            if image.format != 'JPEG' or image.width < 320 or image.height < 240:
                raise SnapshotError('Capture a clear webcam photo at least 320x240 pixels.')
            image.verify()
        with Image.open(BytesIO(raw)) as image:
            image = image.convert('RGB')
            brightness = ImageStat.Stat(image.convert('L')).mean[0]
            if brightness < 25 or brightness > 245:
                raise SnapshotError('The photo is too dark or overexposed. Keep your face clearly visible.')
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            encoded = BytesIO()
            for quality in (85, 75, 65, 55, 45):
                encoded.seek(0)
                encoded.truncate()
                image.save(encoded, format='JPEG', quality=quality, optimize=True)
                if encoded.tell() <= MAX_SNAPSHOT_BYTES:
                    break
            snapshot = encoded.getvalue()
    except (binascii.Error, Image.DecompressionBombError, Image.DecompressionBombWarning, ValueError, UnidentifiedImageError) as exc:
        raise SnapshotError('The webcam photo could not be decoded.') from exc
    if len(snapshot) > MAX_SNAPSHOT_BYTES:
        raise SnapshotError('The webcam photo must be no larger than 200KB.')
    return snapshot
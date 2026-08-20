import base64
import binascii
import math

import cv2
import numpy as np

MAX_FRAME_BYTES = 1_500_000
MIN_BRIGHTNESS = 35.0
MIN_FACE_CONFIDENCE = 0.6


class VisionError(ValueError):
    pass


def _face_recognition():
    try:
        import face_recognition
    except ImportError as exc:
        raise VisionError('Face recognition runtime is unavailable. Install face-recognition and dlib on the server.') from exc
    return face_recognition


def decode_webcam_frame(data_url):
    if not isinstance(data_url, str) or not data_url.startswith('data:image/jpeg;base64,'):
        raise VisionError('Only JPEG webcam frames are accepted.')
    encoded = data_url.split(',', 1)[1]
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise VisionError('The webcam frame is not valid base64.') from exc
    if len(raw) > MAX_FRAME_BYTES:
        raise VisionError('Each webcam frame must be smaller than 1.5 MB.')
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise VisionError('The webcam frame could not be decoded.')
    if image.shape[1] > 1280 or image.shape[0] > 1280:
        raise VisionError('Webcam frame dimensions are too large.')
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def analyze_frame(image):
    face_recognition = _face_recognition()
    brightness = float(np.mean(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)))
    if brightness < MIN_BRIGHTNESS:
        raise VisionError('Lighting is too low. Move to a brighter location.')
    locations = face_recognition.face_locations(image, model='hog', number_of_times_to_upsample=1)
    if not locations:
        raise VisionError('No face detected. Center your face in the camera.')
    if len(locations) > 1:
        raise VisionError('Multiple faces detected. Only one person may be in frame.')
    encodings = face_recognition.face_encodings(image, known_face_locations=locations, num_jitters=1)
    if not encodings:
        raise VisionError('Face confidence is below the 0.6 threshold.')
    landmarks = face_recognition.face_landmarks(image, locations)
    return encodings[0], landmarks[0] if landmarks else {}, brightness


def eye_aspect_ratio(eye):
    if len(eye) < 6:
        return 0.0
    points = np.asarray(eye, dtype=float)
    vertical_a = np.linalg.norm(points[1] - points[5])
    vertical_b = np.linalg.norm(points[2] - points[4])
    horizontal = np.linalg.norm(points[0] - points[3])
    return float((vertical_a + vertical_b) / (2.0 * horizontal)) if horizontal else 0.0


def liveness_score(landmarks):
    eyes = []
    for key in ('left_eye', 'right_eye'):
        if key in landmarks:
            eyes.append(eye_aspect_ratio(landmarks[key]))
    if not eyes:
        return 0.0
    return min(1.0, max(0.0, sum(eyes) / len(eyes) / 0.32))


def has_liveness_variation(analyses):
    if len(analyses) < 5:
        return False
    eye_scores = [liveness_score(item[1]) for item in analyses]
    brightness = [item[2] for item in analyses]
    eye_variation = max(eye_scores) - min(eye_scores)
    brightness_variation = max(brightness) - min(brightness)
    return eye_variation >= 0.08 or brightness_variation >= 2.0


def average_vectors(vectors):
    return np.mean(np.asarray(vectors, dtype=np.float64), axis=0).tolist()


def compare_vector(candidate, stored):
    distance = float(np.linalg.norm(np.asarray(candidate) - np.asarray(stored)))
    confidence = max(0.0, min(1.0, 1.0 - distance / 0.6))
    return distance, confidence

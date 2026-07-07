"""
face_utils.py – Core face recognition helpers for SecureID
Uses: face_recognition (dlib wrapper) + OpenCV
"""

import base64
import io
import json
import logging
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional imports – graceful fallback when libs are not installed (dev mode)
# ---------------------------------------------------------------------------
try:
    import face_recognition
    import cv2
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning(
        "face_recognition / cv2 not installed. "
        "Running in DEMO mode – face matching is disabled."
    )

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def base64_to_numpy(b64_string: str) -> np.ndarray | None:
    """
    Convert a base64-encoded image string (from JS webcam) to an RGB numpy array.
    Accepts both 'data:image/jpeg;base64,…' and raw base64.
    """
    try:
        if ',' in b64_string:
            b64_string = b64_string.split(',', 1)[1]
        img_bytes = base64.b64decode(b64_string)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)

        if FACE_RECOGNITION_AVAILABLE:
            img_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            return img_rgb
        elif PIL_AVAILABLE:
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            return np.array(img)
        else:
            return None
    except Exception as e:
        logger.error(f"base64_to_numpy error: {e}")
        return None


def file_to_numpy(image_file) -> np.ndarray | None:
    """Convert a Django UploadedFile / PIL image to an RGB numpy array."""
    try:
        if PIL_AVAILABLE:
            img = Image.open(image_file).convert('RGB')
            return np.array(img)
        return None
    except Exception as e:
        logger.error(f"file_to_numpy error: {e}")
        return None


# ---------------------------------------------------------------------------
# Face encoding
# ---------------------------------------------------------------------------

def encode_face(image_rgb: np.ndarray) -> list | None:
    """
    Detect faces in image and return the encoding of the first (largest) face.
    Returns a Python list[float] or None if no face found.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        # Demo mode: return a fake encoding
        return list(np.random.rand(128).tolist())

    try:
        from django.conf import settings
        model = getattr(settings, 'FACE_RECOGNITION_MODEL', 'hog')

        face_locations = face_recognition.face_locations(image_rgb, model=model)
        if not face_locations:
            return None

        # Pick the largest face (by bounding-box area)
        largest = max(face_locations, key=lambda loc: (loc[2]-loc[0]) * (loc[1]-loc[3]))

        encodings = face_recognition.face_encodings(image_rgb, [largest])
        if encodings:
            return encodings[0].tolist()
        return None
    except Exception as e:
        logger.error(f"encode_face error: {e}")
        return None


def encode_face_from_b64(b64_string: str) -> list | None:
    """Pipeline: base64 string → RGB numpy → face encoding."""
    img = base64_to_numpy(b64_string)
    if img is None:
        return None
    return encode_face(img)


def encode_face_from_file(image_file) -> list | None:
    """Pipeline: Django file → RGB numpy → face encoding."""
    img = file_to_numpy(image_file)
    if img is None:
        return None
    return encode_face(img)


# ---------------------------------------------------------------------------
# Face matching
# ---------------------------------------------------------------------------

def find_matching_student(b64_frame: str, students_qs, tolerance: float = None):
    """
    Compare a webcam frame against all active students with registered face encodings.

    Parameters
    ----------
    b64_frame   : base64-encoded webcam frame
    students_qs : QuerySet of Student objects
    tolerance   : face matching tolerance (0.4 strict → 0.6 lenient)

    Returns
    -------
    (Student | None, confidence: float | None)
    """
    from django.conf import settings

    if tolerance is None:
        tolerance = getattr(settings, 'FACE_RECOGNITION_TOLERANCE', 0.5)

    img_rgb = base64_to_numpy(b64_frame)
    if img_rgb is None:
        return None, None

    if not FACE_RECOGNITION_AVAILABLE:
        # Demo mode: always return the first student
        first = students_qs.filter(face_encoding__isnull=False).first()
        return first, 0.95

    try:
        model = getattr(settings, 'FACE_RECOGNITION_MODEL', 'hog')
        face_locations = face_recognition.face_locations(img_rgb, model=model)
        if not face_locations:
            return None, None

        unknown_encodings = face_recognition.face_encodings(img_rgb, face_locations)
        if not unknown_encodings:
            return None, None

        unknown_enc = unknown_encodings[0]

        # Build list of known encodings
        known_encodings = []
        known_students  = []
        for student in students_qs.filter(is_active=True):
            enc = student.get_face_encoding()
            if enc is not None:
                known_encodings.append(np.array(enc))
                known_students.append(student)

        if not known_encodings:
            return None, None

        face_distances = face_recognition.face_distance(known_encodings, unknown_enc)
        best_idx       = int(np.argmin(face_distances))
        best_distance  = float(face_distances[best_idx])

        if best_distance <= tolerance:
            confidence = round((1 - best_distance) * 100, 1)
            return known_students[best_idx], confidence

        return None, None

    except Exception as e:
        logger.error(f"find_matching_student error: {e}")
        return None, None


# ---------------------------------------------------------------------------
# Liveness / quality helpers  (basic, can be extended)
# ---------------------------------------------------------------------------

def check_face_quality(image_rgb: np.ndarray) -> dict:
    """
    Basic checks: brightness, blur, face count.
    Returns {'ok': bool, 'issues': [str]}
    """
    issues = []
    if not FACE_RECOGNITION_AVAILABLE:
        return {'ok': True, 'issues': []}

    try:
        gray       = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        brightness = float(np.mean(gray))
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        if brightness < 40:
            issues.append('Image too dark – improve lighting')
        elif brightness > 240:
            issues.append('Image overexposed – reduce lighting')

        if blur_score < 50:
            issues.append('Image too blurry – hold still')

        face_locs = face_recognition.face_locations(image_rgb)
        if len(face_locs) == 0:
            issues.append('No face detected')
        elif len(face_locs) > 1:
            issues.append('Multiple faces detected – ensure only one person is in frame')

        return {'ok': len(issues) == 0, 'issues': issues}
    except Exception as e:
        return {'ok': False, 'issues': [str(e)]}

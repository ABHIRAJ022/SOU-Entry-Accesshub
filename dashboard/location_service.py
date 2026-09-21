from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import LocationHistory, UserLocation


def distance_meters(latitude_a, longitude_a, latitude_b, longitude_b):
    latitude_a, longitude_a, _ = validate_coordinates(latitude_a, longitude_a)
    latitude_b, longitude_b, _ = validate_coordinates(latitude_b, longitude_b)
    earth_radius = 6371000
    dlat = radians(latitude_b - latitude_a)
    dlng = radians(longitude_b - longitude_a)
    a = sin(dlat / 2) ** 2 + cos(radians(latitude_a)) * cos(radians(latitude_b)) * sin(dlng / 2) ** 2
    return 2 * earth_radius * asin(sqrt(a))


def validate_coordinates(latitude, longitude, accuracy=None):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        accuracy = None if accuracy in (None, '') else float(accuracy)
    except (TypeError, ValueError):
        raise ValueError('Latitude and longitude must be valid numbers.')
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError('Latitude must be between -90 and 90 and longitude between -180 and 180.')
    if accuracy is not None and (accuracy < 0 or accuracy > 100000):
        raise ValueError('Accuracy must be between 0 and 100000 metres.')
    return latitude, longitude, accuracy


def parse_recorded_at(value):
    if not value:
        return timezone.now()
    from django.utils.dateparse import parse_datetime
    timestamp = parse_datetime(str(value))
    if timestamp is None:
        raise ValueError('recorded_at must be a valid ISO-8601 timestamp.')
    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp)
    now = timezone.now()
    if timestamp > now + timedelta(minutes=5) or timestamp < now - timedelta(days=30):
        raise ValueError('recorded_at is outside the allowed time window.')
    return timestamp


def record_location(user, latitude, longitude, accuracy=None, recorded_at=None):
    latitude, longitude, accuracy = validate_coordinates(latitude, longitude, accuracy)
    recorded_at = parse_recorded_at(recorded_at)
    latest = UserLocation.objects.filter(user=user).first()
    duplicate_window = timedelta(seconds=getattr(settings, 'LOCATION_DUPLICATE_WINDOW_SECONDS', 45))
    if latest and latest.recorded_at >= recorded_at - duplicate_window:
        if abs(float(latest.latitude) - latitude) < 0.000001 and abs(float(latest.longitude) - longitude) < 0.000001:
            return latest
    LocationHistory.objects.create(
        user=user, latitude=latitude, longitude=longitude,
        accuracy=accuracy, recorded_at=recorded_at,
    )
    latest, _ = UserLocation.objects.update_or_create(
        user=user,
        defaults={'latitude': latitude, 'longitude': longitude, 'accuracy': accuracy, 'recorded_at': recorded_at},
    )
    return latest


def is_inside_campus(latitude, longitude):
    latitude, longitude, _ = validate_coordinates(latitude, longitude)
    center_lat = float(getattr(settings, 'CAMPUS_CENTER_LATITUDE', 23.097214))
    center_lng = float(getattr(settings, 'CAMPUS_CENTER_LONGITUDE', 72.540600))
    radius = float(getattr(settings, 'CAMPUS_GEOFENCE_RADIUS_METERS', 1000))
    earth_radius = 6371000
    dlat = radians(latitude - center_lat)
    dlng = radians(longitude - center_lng)
    a = sin(dlat / 2) ** 2 + cos(radians(center_lat)) * cos(radians(latitude)) * sin(dlng / 2) ** 2
    return 2 * earth_radius * asin(sqrt(a)) <= radius


def rate_limit(key, limit=30, window=60):
    cache_key = f'location-rate:{key}'
    count = cache.get(cache_key, 0)
    if count >= limit:
        return False
    cache.set(cache_key, count + 1, window)
    return True

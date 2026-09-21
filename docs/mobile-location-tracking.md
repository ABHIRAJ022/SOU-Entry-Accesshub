# Flutter background location client

The Django API remains opt-in: an administrator or user must enable `location_sharing_enabled`, and the mobile app must call `/api/v1/location/start/`. A mobile token is a bearer credential, not a Django session cookie. Provision one over an authenticated admin shell and store the returned value only in platform secure storage:

```python
user = User.objects.get(email='student@example.com')
user.location_sharing_enabled = True
user.save(update_fields=['location_sharing_enabled'])
print(user.issue_mobile_location_token())
```

## Flutter dependencies

```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_background_service: ^5.0.6
  geolocator: ^13.0.2
  http: ^1.2.2
  flutter_secure_storage: ^9.2.2
```

## Android

In `android/app/src/main/AndroidManifest.xml`, add these permissions directly under `<manifest>` and the service/boot receiver under `<application>`:

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />

<application ...>
  <service
      android:name="id.flutter.flutter_background_service.BackgroundService"
      android:exported="false"
      android:foregroundServiceType="location" />
  <receiver
      android:name="id.flutter.flutter_background_service.WatchdogReceiver"
      android:enabled="true"
      android:exported="true" />
</application>
```

Request foreground location first, then background location on Android 10+. Explain the permission in the app UI. Android 13+ also needs `POST_NOTIFICATIONS` for the visible service notification. Android may still restrict background work under battery optimization; the user must explicitly allow unrestricted battery use for the app where required by the device vendor.

## iOS

Add the following keys to `ios/Runner/Info.plist`:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Your live location is shared with campus security only while you have enabled location sharing.</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>Your enabled campus safety service needs location updates while the app is in the background.</string>
<key>UIBackgroundModes</key>
<array>
  <string>location</string>
  <string>processing</string>
</array>
```

Enable the Xcode **Background Modes** capability and check **Location updates** and **Background processing**. iOS does not guarantee execution after the user force-quits the app; no Flutter package can bypass that OS rule. Reboot behavior must be tested on each supported OS version.

## Dart collector

```dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;

const apiBase = 'https://accesshub.example.edu';
const locationToken = String.fromEnvironment('LOCATION_TOKEN');

Future<void> configureLocationService() async {
  final service = FlutterBackgroundService();
  await service.configure(
    androidConfiguration: AndroidConfiguration(
      onStart: onStart,
      autoStart: false,
      autoStartOnBoot: true,
      isForegroundMode: true,
      notificationChannelId: 'accesshub_location',
      initialNotificationTitle: 'Campus location sharing',
      initialNotificationContent: 'Location sharing is enabled',
      foregroundServiceNotificationId: 4101,
    ),
    iosConfiguration: IosConfiguration(
      autoStart: false,
      onForeground: onStart,
      onBackground: onIosBackground,
    ),
  );
}

@pragma('vm:entry-point')
Future<bool> onIosBackground(ServiceInstance service) async => true;

@pragma('vm:entry-point')
void onStart(ServiceInstance service) {
  Timer.periodic(const Duration(seconds: 30), (_) async {
    if (service is AndroidServiceInstance && !await service.isForegroundService()) return;
    if (!await Geolocator.isLocationServiceEnabled()) return;
    final permission = await Geolocator.checkPermission();
    if (permission != LocationPermission.always && permission != LocationPermission.whileInUse) return;
    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );
    final response = await http.post(
      Uri.parse('$apiBase/api/v1/location/update/'),
      headers: {
        'Authorization': 'Bearer $locationToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'latitude': position.latitude,
        'longitude': position.longitude,
        'accuracy': position.accuracy,
        'recorded_at': position.timestamp.toUtc().toIso8601String(),
      }),
    );
    if (response.statusCode == 401 || response.statusCode == 403) {
      service.invoke('authentication_failed');
    }
  });
}

Future<void> startSharing() async {
  await http.post(Uri.parse('$apiBase/api/v1/location/start/'), headers: {
    'Authorization': 'Bearer $locationToken',
  });
  await FlutterBackgroundService().startService();
}

Future<void> stopSharing() async {
  await http.post(Uri.parse('$apiBase/api/v1/location/stop/'), headers: {
    'Authorization': 'Bearer $locationToken',
  });
  FlutterBackgroundService().invoke('stopService');
}
```

Use `flutter_secure_storage` instead of a compile-time constant in production, rotate tokens after device loss, and never log the bearer token. The API rate limit is intentionally compatible with a 30-second interval and duplicate coordinates are ignored inside the configured duplicate window.

## Leaflet polling

```js
const markers = new Map();
const map = L.map('map').setView([23.097214, 72.540600], 16);
L.tileLayer('/tiles/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);

async function refreshUsers() {
  const response = await fetch('/api/v1/location/users/', { credentials: 'same-origin' });
  if (!response.ok) return;
  const { users } = await response.json();
  for (const user of users) {
    const point = [user.latitude, user.longitude];
    let marker = markers.get(user.id);
    if (!marker) {
      marker = L.marker(point).addTo(map).bindPopup(user.name);
      markers.set(user.id, marker);
    } else {
      marker.setLatLng(point);
    }
    marker.setOpacity(user.online ? 1 : 0.45);
  }
}
refreshUsers();
setInterval(refreshUsers, 30000);
```

## Scheduled reports

Create `AccessReportSchedule` rows in Django admin with `daily`, `weekly`, or `monthly`, recipient email addresses, and formats. Run `python manage.py send_access_reports` from cron once per day, or pass `--period daily`, `--period weekly`, or `--period monthly` from separate schedulers. The generated attachments include entries, exits (zero until an exit event is modeled), active users, visitors, expired tokens, failed scans, suspicious GPS failures, and overstays.

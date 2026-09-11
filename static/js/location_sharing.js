document.addEventListener('DOMContentLoaded', async () => {
  const root = document.querySelector('[data-location-sharing]');
  if (!root) return;
  const startButton = root.querySelector('[data-location-start]');
  const stopButton = root.querySelector('[data-location-stop]');
  const status = root.querySelector('[data-location-status]');
  const current = root.querySelector('[data-location-current]');
  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  let watchId = null;

  const call = (url, options = {}) => fetch(url, {
    credentials: 'same-origin',
    headers: {'X-CSRFToken': csrf, 'Content-Type': 'application/json', ...(options.headers || {})},
    ...options,
  }).then(async response => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Location request failed.');
    return data;
  });
  const render = (position) => {
    const {latitude, longitude, accuracy} = position.coords;
    current.textContent = `Current position: ${latitude.toFixed(6)}, ${longitude.toFixed(6)} (accuracy ${Math.round(accuracy)}m) at ${new Date(position.timestamp).toLocaleString()}`;
  };
  const update = (position) => call('/api/v1/location/update/', {
    method: 'POST',
    body: JSON.stringify({
      latitude: position.coords.latitude, longitude: position.coords.longitude,
      accuracy: position.coords.accuracy, recorded_at: new Date(position.timestamp).toISOString(),
    }),
  }).then(() => render(position)).catch(error => { status.textContent = error.message; });
  const stopWatching = async () => {
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    watchId = null;
    try { await call('/api/v1/location/stop/', {method: 'POST', body: '{}'}); } catch (error) { status.textContent = error.message; }
    startButton.disabled = false; stopButton.disabled = true;
  };
  startButton.addEventListener('click', async () => {
    if (!window.isSecureContext && location.hostname !== 'localhost') {
      status.textContent = 'Location sharing requires HTTPS.';
      return;
    }
    if (!navigator.geolocation) { status.textContent = 'Geolocation is unavailable in this browser.'; return; }
    try {
      await call('/api/v1/location/start/', {method: 'POST', body: '{}'});
      watchId = navigator.geolocation.watchPosition(update, error => {
        status.textContent = error.code === 1 ? 'Location permission was denied.' : 'Location is currently unavailable.';
      }, {enableHighAccuracy: true, maximumAge: 30000, timeout: 10000});
      startButton.disabled = true; stopButton.disabled = false; status.textContent = 'Location sharing enabled.';
    } catch (error) { status.textContent = error.message; }
  });
  stopButton.addEventListener('click', stopWatching);
  try {
    const data = await call('/api/v1/location/me/');
    startButton.disabled = data.sharing_enabled;
    stopButton.disabled = !data.sharing_enabled;
    if (data.location) current.textContent = `Last position: ${data.location.latitude}, ${data.location.longitude} at ${new Date(data.location.recorded_at).toLocaleString()}`;
  } catch (error) { status.textContent = error.message; }
});

document.addEventListener('DOMContentLoaded', async () => {
  const element = document.querySelector('#campus-map');
  if (!element || !window.L) return;
  const map = L.map(element).setView([20.5937, 78.9629], 5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
  const markers = [];
  let route;
  let locations = [];
  const message = document.querySelector('[data-map-message]');
  const draw = (items) => {
    markers.splice(0).forEach((marker) => map.removeLayer(marker));
    items.forEach((location) => {
      const marker = L.marker([location.latitude, location.longitude], {draggable: element.dataset.locationAdmin === 'true'}).addTo(map);
      const popup = document.createElement('div');
      const title = document.createElement('strong');
      title.textContent = location.name;
      popup.append(title, document.createElement('br'));
      const category = document.createElement('span');
      category.textContent = location.category_label;
      popup.append(category, document.createElement('br'));
      const description = document.createElement('span');
      description.textContent = location.description || '';
      popup.append(description, document.createElement('br'));
      const routeButton = document.createElement('button');
      routeButton.dataset.routeLat = location.latitude;
      routeButton.dataset.routeLng = location.longitude;
      routeButton.textContent = 'Route here';
      popup.append(routeButton);
      if (element.dataset.locationAdmin === 'true') {
        popup.append(document.createElement('br'));
        const deleteButton = document.createElement('button');
        deleteButton.dataset.deleteLocation = location.id;
        deleteButton.textContent = 'Deactivate';
        popup.append(deleteButton);
      }
      marker.bindPopup(popup);
      markers.push(marker);
      if (element.dataset.locationAdmin === 'true') marker.on('dragend', async () => {
        const point = marker.getLatLng();
        await fetch(`/api/locations/${location.id}/`, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value}, body: JSON.stringify({...location, latitude: point.lat, longitude: point.lng})});
      });
    });
  };
  const response = await fetch('/api/locations/', {credentials: 'same-origin'});
  locations = (await response.json()).locations || [];
  draw(locations);
  if (locations.length) map.fitBounds(L.latLngBounds(locations.map((location) => [location.latitude, location.longitude])).pad(0.15));
  document.querySelectorAll('[data-map-filter]').forEach((button) => button.addEventListener('click', () => draw(button.dataset.mapFilter === 'ALL' ? locations : locations.filter((location) => location.category === button.dataset.mapFilter))));
  map.on('popupopen', (event) => event.popup.getElement().querySelector('[data-route-lat]')?.addEventListener('click', () => {
    navigator.geolocation.getCurrentPosition(async (position) => {
      const start = `${position.coords.longitude},${position.coords.latitude}`; const end = `${event.popup.getElement().querySelector('[data-route-lng]').dataset.routeLng},${event.popup.getElement().querySelector('[data-route-lat]').dataset.routeLat}`;
      const routeResponse = await fetch(`https://router.project-osrm.org/route/v1/foot/${start};${end}?overview=full&geometries=geojson`); const data = await routeResponse.json();
      if (route) map.removeLayer(route); route = L.geoJSON(data.routes[0].geometry, {style: {color: '#0d6efd', weight: 5}}).addTo(map); message.textContent = `Walking time: approximately ${Math.ceil(data.routes[0].duration / 60)} minutes.`; map.fitBounds(route.getBounds());
    }, () => { message.textContent = 'Location permission is required for walking directions.'; });
  }));
  map.on('popupopen', (event) => event.popup.getElement().querySelector('[data-delete-location]')?.addEventListener('click', async () => {
    const id = event.popup.getElement().querySelector('[data-delete-location]').dataset.deleteLocation;
    const response = await fetch(`/api/locations/${id}/delete/`, {method: 'POST', headers: {'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value}});
    if (response.ok) { locations = locations.filter((location) => String(location.id) !== id); draw(locations); message.textContent = 'Location deactivated.'; }
  }));
  if (element.dataset.locationAdmin === 'true') {
    map.on('click', (event) => { document.querySelector('[data-location-lat]').value = event.latlng.lat.toFixed(6); document.querySelector('[data-location-lng]').value = event.latlng.lng.toFixed(6); });
    document.querySelector('[data-location-form]').addEventListener('submit', async (event) => {
      event.preventDefault(); const form = event.currentTarget; const body = {name: form.querySelector('[data-location-name]').value, category: form.querySelector('[data-location-category]').value, building_code: form.querySelector('[data-location-building]').value, latitude: form.querySelector('[data-location-lat]').value, longitude: form.querySelector('[data-location-lng]').value, description: form.querySelector('[data-location-description]').value};
      const createResponse = await fetch('/api/locations/create/', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value}, body: JSON.stringify(body)}); const data = await createResponse.json(); document.querySelector('[data-location-message]').textContent = createResponse.ok ? 'Location created.' : data.error; if (createResponse.ok) { locations.push(data); draw(locations); form.reset(); }
    });
  }
});
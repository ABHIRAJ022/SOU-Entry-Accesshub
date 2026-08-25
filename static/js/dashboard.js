document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  const duration = document.querySelector('[data-token-duration]');
  const pass = document.querySelector('[data-token-pass]');
  const qr = document.querySelector('[data-token-qr]');
  const countdown = document.querySelector('[data-token-countdown]');
  const status = document.querySelector('[data-token-status]');
  const result = document.querySelector('[data-token-result]');
  const camera = document.querySelector('[data-token-camera]');
  const cameraStart = document.querySelector('[data-token-camera-start]');
  const snapshotButton = document.querySelector('[data-token-snapshot]');
  const cameraStatus = document.querySelector('[data-token-camera-status]');
  const preview = document.querySelector('[data-token-preview]');
  const photoPreview = document.querySelector('[data-token-photo-preview]');
  const photo = document.querySelector('[data-token-photo]');
  let snapshot;
  let stream;
  let timer;
  let notified = new Set();
  let lastStatusCheck = 0;

  const persistentToken = document.querySelector('[data-token-persistent]');
  const persistentCountdown = document.querySelector('[data-token-persistent-countdown]');
  const persistentStatus = document.querySelector('[data-token-persistent-status]');
  const guestTokenCard = document.querySelector('[data-guest-token-card]');
  const guestTokenStatus = document.querySelector('[data-guest-token-status]');
  const guestTokenCountdown = document.querySelector('[data-guest-token-countdown]');
  const guestTokenPdf = document.querySelector('[data-guest-token-pdf]');
  const guestQueueTokens = document.querySelectorAll('[data-guest-queue-token]');

  const persistGuestToken = (payload) => {
    try { localStorage.setItem('smartcampus_guest_token', JSON.stringify(payload)); } catch (error) {}
  };

  const restoreGuestToken = () => {
    if (!guestTokenCard) return;
    try {
      const saved = JSON.parse(localStorage.getItem('smartcampus_guest_token') || 'null');
      if (!saved || !saved.tokenId || !saved.expiresAt) return;
      guestTokenCard.dataset.tokenId = saved.tokenId;
      guestTokenCard.dataset.tokenExpires = saved.expiresAt;
      guestTokenCard.dataset.tokenPdfUrl = saved.pdfUrl || guestTokenCard.dataset.tokenPdfUrl;
      guestTokenCard.dataset.tokenQrUrl = saved.qrUrl || guestTokenCard.dataset.tokenQrUrl;
      guestTokenCard.dataset.tokenStatusUrl = saved.statusUrl || guestTokenCard.dataset.tokenStatusUrl;
      const qr = document.querySelector('[data-guest-token-qr]');
      if (qr && saved.qrUrl) qr.src = saved.qrUrl;
      if (guestTokenPdf && saved.pdfUrl) guestTokenPdf.href = saved.pdfUrl;
    } catch (error) {}
  };

  const renderGuestTokenCountdown = async () => {
    if (!guestTokenCard || !guestTokenCountdown || !guestTokenStatus) return;
    const expiresAt = Date.parse(guestTokenCard.dataset.tokenExpires || '');
    if (!expiresAt) return;
    const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
    guestTokenCountdown.textContent = `${String(Math.floor(remaining / 3600)).padStart(2, '0')}:${String(Math.floor((remaining % 3600) / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
    if (!remaining) guestTokenStatus.textContent = 'EXPIRED';
    else guestTokenStatus.textContent = 'ACTIVE';
    persistGuestToken({
      tokenId: guestTokenCard.dataset.tokenId,
      expiresAt: guestTokenCard.dataset.tokenExpires,
      pdfUrl: guestTokenCard.dataset.tokenPdfUrl,
      qrUrl: guestTokenCard.dataset.tokenQrUrl,
      statusUrl: guestTokenCard.dataset.tokenStatusUrl,
      status: guestTokenStatus.textContent,
    });
    const statusUrl = guestTokenCard.dataset.tokenStatusUrl;
    if (statusUrl && Date.now() - lastStatusCheck >= 60000) {
      lastStatusCheck = Date.now();
      try {
        const response = await fetch(statusUrl, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
        if (response.ok) {
          const data = await response.json();
          guestTokenStatus.textContent = data.status || guestTokenStatus.textContent;
          if (data.expires_at) guestTokenCard.dataset.tokenExpires = data.expires_at;
        }
      } catch (error) {}
    }
  };

  if (guestTokenCard) {
    restoreGuestToken();
    renderGuestTokenCountdown();
    setInterval(renderGuestTokenCountdown, 1000);
  }

  guestQueueTokens.forEach((card) => {
    const statusEl = card.querySelector('[data-guest-queue-status]');
    const countdownEl = card.querySelector('[data-guest-queue-countdown]');
    const updateQueueCard = async () => {
      if (!statusEl || !countdownEl) return;
      const expiresAt = Date.parse(card.dataset.tokenExpires || '');
      if (!expiresAt) return;
      const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
      countdownEl.textContent = `${String(Math.floor(remaining / 3600)).padStart(2, '0')}:${String(Math.floor((remaining % 3600) / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
      statusEl.textContent = remaining ? 'ACTIVE' : 'EXPIRED';
      if (card.dataset.tokenStatusUrl && !remaining && Date.now() - lastStatusCheck >= 60000) {
        lastStatusCheck = Date.now();
        try { const response = await fetch(card.dataset.tokenStatusUrl, {credentials: 'same-origin', headers: {'Accept': 'application/json'}}); if (response.ok) { const data = await response.json(); if (data.status) statusEl.textContent = data.status; }} catch (error) {}
      }
    };
    updateQueueCard();
    setInterval(updateQueueCard, 1000);
  });

  const stopCamera = () => {
    if (stream) stream.getTracks().forEach((track) => track.stop());
    stream = null;
    if (camera) camera.srcObject = null;
    if (cameraStatus) cameraStatus.textContent = 'Camera is off';
    if (cameraStart) { cameraStart.disabled = false; cameraStart.textContent = 'Enable camera'; }
    if (snapshotButton) snapshotButton.disabled = true;
  };

  if (cameraStart) cameraStart.addEventListener('click', async () => {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) { preview.textContent = 'Live camera access requires HTTPS.'; return; }
    try {
      stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: {ideal: 'user'}, width: {ideal: 640}, height: {ideal: 480}}, audio: false});
      camera.srcObject = stream; snapshotButton.disabled = false; cameraStart.disabled = true; cameraStatus.textContent = 'Camera ready. Keep your face clearly visible.';
    } catch (error) { preview.textContent = 'Camera could not start. Allow camera access and try again.'; }
  });

  if (snapshotButton) snapshotButton.addEventListener('click', () => {
    const canvas = document.createElement('canvas'); canvas.width = 640; canvas.height = 480;
    canvas.getContext('2d').drawImage(camera, 0, 0, canvas.width, canvas.height);
    snapshot = canvas.toDataURL('image/jpeg', 0.82);
    if (photo) photo.src = snapshot;
    if (photoPreview) photoPreview.classList.remove('d-none');
    preview.textContent = 'Live photo captured. You can now create the token.';
    document.querySelectorAll('[data-token-action]').forEach((button) => { button.disabled = false; });
    stopCamera();
  });

  const notify = (message, key) => {
    if (notified.has(key)) return;
    notified.add(key);
    if ('Notification' in window && Notification.permission === 'granted') new Notification('Smart Campus token', {body: message});
  };

  const startCountdown = (data) => {
    clearInterval(timer);
    notified = new Set();
    const expiry = Date.parse(data.expires_at);
    const serverOffset = Date.parse(data.server_now) - Date.now();
    const update = async () => {
      const remaining = Math.max(0, expiry - (Date.now() + serverOffset));
      const seconds = Math.floor(remaining / 1000);
      countdown.textContent = `${String(Math.floor(seconds / 3600)).padStart(2, '0')}:${String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
      if (seconds <= 600) notify('Your campus token expires in 10 minutes.', '10m');
      if (seconds <= 300) notify('Your campus token expires in 5 minutes.', '5m');
      if (seconds <= 120) notify('Your campus token is expiring in 2 minutes. If you want to stay on campus, generate a new token.', '2m');
      if (seconds <= 60) notify('Your campus token expires in 1 minute.', '1m');
      if (data.status_url && Date.now() - lastStatusCheck >= 60000) {
        lastStatusCheck = Date.now();
        fetch(data.status_url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}}).catch(() => {});
      }
      if (!seconds) {
        clearInterval(timer); status.textContent = 'EXPIRED'; notify('Your campus token has expired.', 'expired');
        const response = await fetch(data.status_url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
        if (response.ok) status.textContent = (await response.json()).status;
      }
    };
    update();
    timer = setInterval(update, 1000);
  };

  const startPersistentCountdown = () => {
    if (!persistentToken || !persistentCountdown) return;
    const expiry = Date.parse(persistentToken.dataset.tokenExpires);
    const statusUrl = persistentToken.dataset.tokenStatusUrl;
    const update = async () => {
      const seconds = Math.max(0, Math.floor((expiry - Date.now()) / 1000));
      persistentCountdown.textContent = `${String(Math.floor(seconds / 3600)).padStart(2, '0')}:${String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
      if (!seconds) {
        persistentStatus.textContent = 'EXPIRED';
        const response = await fetch(statusUrl, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
        if (response.ok) persistentStatus.textContent = (await response.json()).status;
      }
    };
    update();
    setInterval(update, 1000);
  };

  startPersistentCountdown();

  document.querySelectorAll('[data-token-action]').forEach((button) => button.addEventListener('click', async () => {
    button.disabled = true;
    stopCamera();
    try {
      const response = await fetch(button.dataset.url, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken(), 'Accept': 'application/json'}, body: JSON.stringify({duration_minutes: Number(duration.value), capture_mode: 'webcam', captured_at: Date.now() / 1000, image: snapshot})});
      const responseText = await response.text();
      let data;
      try { data = JSON.parse(responseText); } catch (error) { data = {error: `Token request failed (${response.status}). Reload the page and try again.`}; }
      if (response.ok) {
        result.textContent = `Token ${data.token_id} created.`;
        qr.src = data.qr_data_url;
        document.querySelector('[data-token-pdf]').href = data.pdf_url;
        status.textContent = 'ACTIVE';
        pass.classList.remove('d-none');
        startCountdown(data);
      } else result.textContent = data.error || 'Token could not be created.';
    } catch (error) { result.textContent = error.message || 'Token request failed. Check your connection and try again.'; }
    button.disabled = false;
  }));

  window.addEventListener('pagehide', stopCamera);

  document.querySelectorAll('[data-approval]').forEach((button) => button.addEventListener('click', async () => {
    button.disabled = true;
    const response = await fetch(button.dataset.url, {method: 'POST', headers: {'X-CSRFToken': csrfToken(), 'Accept': 'application/json'}, body: new URLSearchParams({action: button.dataset.action})});
    if (response.ok) {
      if (button.dataset.action === 'revoke') window.location.reload();
      else button.closest('[data-user-row]').remove();
    }
    else if (response.status === 403) window.location.reload();
    else button.disabled = false;
  }));
  document.querySelectorAll('[data-cancel-token]').forEach((button) => button.addEventListener('click', async () => {
    if (!window.confirm('Cancel this live token?')) return;
    button.disabled = true;
    const response = await fetch(button.dataset.url, {method: 'POST', credentials: 'same-origin', headers: {'X-CSRFToken': csrfToken(), 'Accept': 'application/json'}});
    if (response.ok) window.location.reload();
    else { button.disabled = false; window.alert((await response.json()).error || 'The token could not be cancelled.'); }
  }));
  const search = document.querySelector('[data-student-search]');
  const results = document.querySelector('[data-student-results]');
  if (search) search.addEventListener('input', async () => {
    const response = await fetch(`/dashboard/students/lookup/?q=${encodeURIComponent(search.value)}`, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
    const data = await response.json();
    results.replaceChildren(...data.results.map((student) => {
      const row = document.createElement('tr');
      [student.name, student.enrollment_number, student.email_verified ? 'Verified' : 'Unverified', student.approved ? 'Approved' : 'Pending'].forEach((value) => {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      });
      return row;
    }));
  });
});
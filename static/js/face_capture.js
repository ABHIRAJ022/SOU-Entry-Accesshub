(() => {
  const video = document.querySelector('[data-camera]');
  const startButton = document.querySelector('[data-camera-start]');
  const captureButton = document.querySelector('[data-camera-capture]');
  const progress = document.querySelector('[data-capture-progress]');
  const status = document.querySelector('[data-camera-status]');
  const result = document.querySelector('[data-camera-result]');
  let stream;

  const csrf = () => document.querySelector(`input[name="csrfmiddlewaretoken"]`)?.value || document.cookie.split('; ').find((item) => item.startsWith('campus_csrftoken_v2='))?.split('=')[1];
  const setResult = (message, success = false) => { result.textContent = message; result.className = `small mt-3 ${success ? 'text-success' : 'text-danger'}`; };

  startButton.addEventListener('click', async () => {
    if (!window.isSecureContext) { setResult('Camera access requires HTTPS. Open the secure https:// site URL.'); return; }
    if (!navigator.mediaDevices?.getUserMedia) { setResult('This browser or embedded preview does not expose camera access. Open the app in a full browser tab.'); return; }
    try {
      try {
        stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: {ideal: 'user'}, width: {ideal: 640}, height: {ideal: 480}}, audio: false});
      } catch (firstError) {
        if (firstError.name !== 'OverconstrainedError' && firstError.name !== 'NotFoundError') throw firstError;
        stream = await navigator.mediaDevices.getUserMedia({video: true, audio: false});
      }
      video.srcObject = stream; captureButton.disabled = false; startButton.disabled = true; status.textContent = 'Camera ready. Center your face.';
    } catch (error) {
      const messages = {NotAllowedError: 'Camera permission is blocked. Allow camera access for this site, then reload.', NotFoundError: 'No camera was found. Connect a webcam and try again.', NotReadableError: 'The camera is busy in another application. Close other camera apps and try again.', SecurityError: 'The browser blocked camera access for this page.', AbortError: 'Camera startup was interrupted. Try again.'};
      setResult(messages[error.name] || `Camera could not start (${error.name || 'unknown browser error'}).`);
    }
  });

  captureButton.addEventListener('click', async () => {
    captureButton.disabled = true; setResult('Capturing live frames...');
    const canvas = document.createElement('canvas'); canvas.width = 640; canvas.height = 480; const context = canvas.getContext('2d'); const frames = [];
    for (let index = 0; index < 5; index += 1) {
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      frames.push({sequence: index, timestamp_ms: Date.now(), data: canvas.toDataURL('image/jpeg', 0.72)});
      progress.style.width = `${((index + 1) / 5) * 100}%`;
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
    const endpoint = window.BIOMETRIC_MODE === 'verify' ? '/api/face/verify/' : (window.BIOMETRIC_MODE === 'login' ? '/api/face/login-verify/' : '/api/face/enroll/submit/');
    const body = {capture_mode: 'webcam', capture_id: window.BIOMETRIC_CAPTURE_ID, frames};
    if (window.BIOMETRIC_MODE === 'login') body.email = document.querySelector('#id_username')?.value.trim().toLowerCase();
    const response = await fetch(endpoint, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'Accept': 'application/json'}, body: JSON.stringify(body)});
    const data = await response.json();
    if (response.ok && (data.enrolled || data.verified)) { setResult(data.message || `Face verified with ${Math.round(data.confidence * 100)}% confidence.`, true); if (window.BIOMETRIC_MODE === 'login') document.querySelector('[data-camera-result]').dataset.verified = '1'; if (window.BIOMETRIC_MODE === 'enroll' && data.registration_complete) window.location.href = '/accounts/login/'; } else setResult(data.error || 'Biometric operation failed. Try again.');
    captureButton.disabled = false;
  });
})();

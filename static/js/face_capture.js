(() => {
  const video = document.querySelector('[data-camera]');
  const startButton = document.querySelector('[data-camera-start]');
  const captureButton = document.querySelector('[data-camera-capture]');
  const otpButton = document.querySelector('[data-request-otp]');
  const codeInput = document.querySelector('[data-identity-code]');
  const status = document.querySelector('[data-camera-status]');
  const result = document.querySelector('[data-camera-result]');
  let stream;

  const csrf = () => document.cookie.split('; ').find((item) => item.startsWith('campus_csrftoken_v2='))?.split('=')[1];
  const show = (message, success = false) => { result.textContent = message; result.className = `small mt-3 ${success ? 'text-success' : 'text-danger'}`; };

  startButton.addEventListener('click', async () => {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) { show('Camera access requires HTTPS in a browser that supports webcam capture.'); return; }
    try {
      stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: {ideal: 'user'}, width: {ideal: 640}, height: {ideal: 480}}, audio: false});
      video.srcObject = stream; captureButton.disabled = false; startButton.disabled = true; status.textContent = 'Camera ready. Center your face and take a snapshot.';
    } catch (error) {
      show(({NotAllowedError: 'Camera permission is blocked. Allow camera access and reload.', NotFoundError: 'No camera was found.', NotReadableError: 'The camera is busy in another application.'})[error.name] || 'Camera could not start.');
    }
  });

  otpButton.addEventListener('click', async () => {
    otpButton.disabled = true;
    const response = await fetch('/api/request-emergency-otp/', {method: 'POST', credentials: 'same-origin', headers: {'X-CSRFToken': csrf(), 'Accept': 'application/json'}});
    const data = await response.json(); show(data.message || data.error || 'Unable to send the emergency code.', response.ok); otpButton.disabled = false;
  });

  captureButton.addEventListener('click', async () => {
    captureButton.disabled = true;
    const canvas = document.createElement('canvas'); canvas.width = 640; canvas.height = 480;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const code = codeInput.value.trim();
    const body = {capture_mode: 'webcam', capture_id: window.IDENTITY_CAPTURE_ID, captured_at: Date.now() / 1000, image: canvas.toDataURL('image/jpeg', 0.72)};
    if (/^\d{4}$/.test(code)) body.otp = code; else body.pin = code;
    try {
      const response = await fetch('/api/verify-identity/', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'Accept': 'application/json'}, body: JSON.stringify(body)});
      const data = await response.json();
      show(response.ok ? 'Identity verified. Return to the dashboard to generate your token.' : (data.error || 'Identity verification failed.'), response.ok);
      if (response.ok) setTimeout(() => { window.location.href = '/dashboard/'; }, 1200);
    } catch (error) { show('The verification request could not be completed.'); }
    captureButton.disabled = false;
  });
})();
document.addEventListener('DOMContentLoaded', () => {
  const result = document.querySelector('[data-scan-result]');
  const openButton = document.querySelector('[data-open-scanner]');
  const closeButton = document.querySelector('[data-close-scanner]');
  const details = document.querySelector('[data-scan-details]');
  const photo = document.querySelector('[data-scan-photo]');
  const fields = {
    name: document.querySelector('[data-scan-name]'), holderType: document.querySelector('[data-scan-holder-type]'),
    enrollment: document.querySelector('[data-scan-enrollment]'), email: document.querySelector('[data-scan-email]'),
    mobile: document.querySelector('[data-scan-mobile]'), gender: document.querySelector('[data-scan-gender]'),
    branch: document.querySelector('[data-scan-branch]'), purpose: document.querySelector('[data-scan-purpose]'),
    expires: document.querySelector('[data-scan-expires]'), tokenId: document.querySelector('[data-scan-token-id]'),
  };
  const pdf = document.querySelector('[data-scan-pdf]');
  const show = (valid, message) => {
    result.textContent = message;
    result.className = `scan-result mt-3 p-4 text-center fw-bold ${valid ? 'bg-success text-white' : 'bg-danger text-white'}`;
    if (window.navigator.vibrate) navigator.vibrate(valid ? [100] : [300, 100, 300]);
    if (window.speechSynthesis) speechSynthesis.speak(new SpeechSynthesisUtterance(message));
  };

  const showDetails = (data) => {
    Object.entries({name: data.full_name, holderType: data.holder_type, enrollment: data.enrollment_number || 'Not provided', email: data.email || 'Not provided', mobile: data.phone_number || 'Not provided', gender: data.gender || 'Not provided', branch: data.branch || 'Not provided', purpose: data.purpose || 'Not provided', expires: new Date(data.expires_at).toLocaleString(), tokenId: data.token_id}).forEach(([key, value]) => { fields[key].textContent = value; });
    if (data.profile_photo) { photo.src = data.profile_photo; photo.alt = `Profile photo of ${data.full_name}`; photo.classList.remove('d-none'); }
    else { photo.removeAttribute('src'); photo.classList.add('d-none'); }
    pdf.href = data.pdf_url;
    details.classList.remove('d-none');
  };

  const scanner = new Html5Qrcode('qr-reader');
  let scanning = false;

  const enableButtons = () => {
    if (openButton) openButton.disabled = scanning;
    if (closeButton) closeButton.disabled = !scanning;
  };

  const startScanner = async () => {
    if (scanning) return;
    try {
      result.textContent = 'Starting scanner...';
      await scanner.start({facingMode: 'environment'}, {fps: 10, qrbox: {width: 250, height: 250}}, onScan, () => {});
      scanning = true;
      result.textContent = 'Ready to scan.';
    } catch (err) {
      result.textContent = 'Camera permission is required for QR scanning.';
      scanning = false;
    }
    enableButtons();
  };

  const stopScanner = async () => {
    if (!scanning) return;
    try {
      await scanner.stop();
      result.textContent = 'Scanner closed.';
    } catch (err) {
      // ignore
    }
    scanning = false;
    enableButtons();
  };

  const onScan = async (qrPayload) => {
    // stop to avoid duplicate reads
    try { await scanner.stop(); } catch (err) {}
    scanning = false;
    enableButtons();

    const response = await fetch('/api/tokens/validate/', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.cookie.split('; ').find((item) => item.startsWith('campus_csrftoken_v2='))?.split('=')[1], 'Accept': 'application/json'}, body: JSON.stringify({qr_payload: qrPayload})});
    const data = await response.json();
    show(response.ok && data.valid, response.ok && data.valid ? `VALID: ${data.student}` : `INVALID: ${data.error || 'Token rejected.'}`);
    if (response.ok && data.valid) showDetails(data);
    else details.classList.add('d-none');

    // wait a bit then restart if user hasn't closed scanner
    setTimeout(async () => {
      if (!scanning) {
        try { await scanner.start({facingMode: 'environment'}, {fps: 10, qrbox: {width: 250, height: 250}}, onScan, () => {}); scanning = true; } catch (err) { result.textContent = 'Camera permission is required for QR scanning.'; }
        enableButtons();
      }
    }, 4000);
  };

  // Wire up buttons
  if (openButton) openButton.addEventListener('click', () => startScanner());
  if (closeButton) closeButton.addEventListener('click', () => stopScanner());

  // Initialize buttons state: scanner closed by default
  scanning = false;
  enableButtons();
});
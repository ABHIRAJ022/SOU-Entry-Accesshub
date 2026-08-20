document.addEventListener('DOMContentLoaded', () => {
  const result = document.querySelector('[data-scan-result]');
  const show = (valid, message) => { result.textContent = message; result.className = `scan-result mt-3 p-4 text-center fw-bold ${valid ? 'bg-success text-white' : 'bg-danger text-white'}`; if (window.navigator.vibrate) navigator.vibrate(valid ? [100] : [300, 100, 300]); if (window.speechSynthesis) speechSynthesis.speak(new SpeechSynthesisUtterance(message)); };
  const scanner = new Html5Qrcode('qr-reader');
  const onScan = async (qrPayload) => {
    await scanner.stop();
    const response = await fetch('/api/tokens/validate/', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.cookie.split('; ').find((item) => item.startsWith('campus_csrftoken_v2='))?.split('=')[1], 'Accept': 'application/json'}, body: JSON.stringify({qr_payload: qrPayload})});
    const data = await response.json();
    show(response.ok && data.valid, response.ok && data.valid ? `VALID: ${data.student} (${data.enrollment_number || 'No enrollment number'})` : `INVALID: ${data.error || 'Token rejected.'}`);
    setTimeout(() => { result.textContent = 'Ready to scan.'; result.className = 'scan-result mt-3'; scanner.start({facingMode: 'environment'}, {fps: 10, qrbox: {width: 250, height: 250}}, onScan, () => {}); }, 4000);
  };
  scanner.start({facingMode: 'environment'}, {fps: 10, qrbox: {width: 250, height: 250}}, onScan, () => {}).catch(() => { result.textContent = 'Camera permission is required for QR scanning.'; });
});
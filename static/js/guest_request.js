document.addEventListener('DOMContentLoaded', () => {
  const video = document.querySelector('[data-guest-camera]');
  const startButton = document.querySelector('[data-guest-camera-start]');
  const captureButton = document.querySelector('[data-guest-camera-capture]');
  const status = document.querySelector('[data-guest-camera-status]');
  const imageInput = document.querySelector('#id_live_photo');
  const preview = document.querySelector('[data-guest-photo-preview]');
  let stream;

  startButton.addEventListener('click', async () => {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) { status.textContent = 'Live camera access requires HTTPS.'; return; }
    try {
      stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: {ideal: 'user'}, width: {ideal: 640}, height: {ideal: 480}}, audio: false});
      video.srcObject = stream; captureButton.disabled = false; startButton.disabled = true; status.textContent = 'Camera ready. Center your face and take a photo.';
    } catch (error) { status.textContent = 'Camera could not start. Allow camera access and try again.'; }
  });

  captureButton.addEventListener('click', () => {
    const canvas = document.createElement('canvas'); canvas.width = 640; canvas.height = 480;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    imageInput.value = canvas.toDataURL('image/jpeg', 0.72); preview.src = imageInput.value; preview.classList.remove('d-none');
    status.textContent = 'Live photo captured.'; captureButton.disabled = true;
    stream?.getTracks().forEach((track) => track.stop()); video.srcObject = null;
  });

  window.addEventListener('pagehide', () => stream?.getTracks().forEach((track) => track.stop()));
});
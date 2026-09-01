document.addEventListener('DOMContentLoaded', () => {
  // DOM elements
  const result = document.querySelector('[data-scan-result]');
  const openButton = document.querySelector('[data-open-scanner]');
  const closeButton = document.querySelector('[data-close-scanner]');
  const details = document.querySelector('[data-scan-details]');
  const photo = document.querySelector('[data-scan-photo]');
  const pdf = document.querySelector('[data-scan-pdf]');

  // Field mappings
  const fields = {
    name: document.querySelector('[data-scan-name]'),
    holderType: document.querySelector('[data-scan-holder-type]'),
    enrollment: document.querySelector('[data-scan-enrollment]'),
    email: document.querySelector('[data-scan-email]'),
    mobile: document.querySelector('[data-scan-mobile]'),
    gender: document.querySelector('[data-scan-gender]'),
    branch: document.querySelector('[data-scan-branch]'),
    purpose: document.querySelector('[data-scan-purpose]'),
    generated: document.querySelector('[data-scan-generated]'),
    expires: document.querySelector('[data-scan-expires]'),
    tokenId: document.querySelector('[data-scan-token-id]'),
  };

  const scanner = new Html5Qrcode('qr-reader');
  let scanning = false;

  const getCsrfToken = () => {
    return document.cookie
      .split('; ')
      .find((item) => item.startsWith('campus_csrftoken_v2='))
      ?.split('=')[1] || '';
  };

  const show = (valid, message) => {
    result.textContent = message;
    result.className = `scan-result mt-3 p-4 text-center fw-bold ${valid ? 'bg-success text-white' : 'bg-danger text-white'}`;
    if (window.navigator.vibrate) {
      navigator.vibrate(valid ? [100] : [300, 100, 300]);
    }
    if (window.speechSynthesis) {
      speechSynthesis.speak(new SpeechSynthesisUtterance(message));
    }
  };

  const showDetails = (data) => {
    try {
      // Populate all fields with data
      if (fields.name) fields.name.textContent = data.full_name || 'Not provided';
      if (fields.holderType) fields.holderType.textContent = data.holder_type || 'Not provided';
      if (fields.enrollment) fields.enrollment.textContent = data.enrollment_number || 'Not provided';
      if (fields.email) fields.email.textContent = data.email || 'Not provided';
      if (fields.mobile) fields.mobile.textContent = data.phone_number || 'Not provided';
      if (fields.gender) fields.gender.textContent = data.gender || 'Not provided';
      if (fields.branch) fields.branch.textContent = data.branch || 'Not provided';
      if (fields.purpose) fields.purpose.textContent = data.purpose || 'Not provided';

      // Format and display dates
      if (fields.generated) {
        try {
          const generatedDate = new Date(data.created_at);
          fields.generated.textContent = generatedDate.toLocaleString() || data.created_at;
        } catch (e) {
          fields.generated.textContent = data.created_at || 'Invalid date';
        }
      }
      if (fields.expires) {
        try {
          const expiresDate = new Date(data.expires_at);
          fields.expires.textContent = expiresDate.toLocaleString() || data.expires_at;
        } catch (e) {
          fields.expires.textContent = data.expires_at || 'Invalid date';
        }
      }

      if (fields.tokenId) fields.tokenId.textContent = data.token_id || 'Not provided';

      // Handle profile photo
      if (data.profile_photo && data.profile_photo.trim() !== '') {
        photo.src = data.profile_photo;
        photo.alt = `Profile photo of ${data.full_name}`;
        photo.classList.remove('d-none');
      } else {
        photo.removeAttribute('src');
        photo.classList.add('d-none');
      }

      // Set PDF link
      if (data.pdf_url) {
        pdf.href = data.pdf_url;
      }

      // Show details section
      details.classList.remove('d-none');
      console.log('Token details displayed successfully');
    } catch (error) {
      console.error('Error displaying token details:', error);
      result.textContent = 'Error displaying token information.';
    }
  };

  const enableButtons = () => {
    if (openButton) openButton.disabled = scanning;
    if (closeButton) closeButton.disabled = !scanning;
  };

  const startScanner = async () => {
    if (scanning) return;
    try {
      result.textContent = 'Starting scanner...';
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        onScan,
        () => {}
      );
      scanning = true;
      result.textContent = 'Ready to scan.';
    } catch (err) {
      console.error('Scanner error:', err);
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
      console.error('Error stopping scanner:', err);
    }
    scanning = false;
    enableButtons();
  };

  const onScan = async (qrPayload) => {
    // Stop to avoid duplicate reads
    try {
      await scanner.stop();
    } catch (err) {
      console.error('Error stopping scanner for rescan:', err);
    }
    scanning = false;
    enableButtons();

    try {
      const csrfToken = getCsrfToken();
      
      if (!csrfToken) {
        console.warn('CSRF token not found. Attempting to continue anyway.');
      }

      console.log('Scanning QR payload:', qrPayload.substring(0, 50) + '...');
      
      const response = await fetch('/api/tokens/validate/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken || '',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ qr_payload: qrPayload }),
      });

      console.log('API Response Status:', response.status);
      
      const data = await response.json();
      console.log('Token validation response:', data);

      if (response.ok && data.valid) {
        show(true, `✓ VALID: ${data.student}`);
        showDetails(data);
      } else {
        const errorMessage = data.error || 'Token rejected.';
        console.warn('Token validation failed:', errorMessage);
        show(false, `✗ INVALID: ${errorMessage}`);
        details.classList.add('d-none');
      }
    } catch (error) {
      console.error('Error during token validation:', {
        message: error.message,
        stack: error.stack,
        name: error.name
      });
      show(false, `Error: ${error.message || 'Failed to validate token'}`);
      details.classList.add('d-none');
    }

    // Wait a bit then restart if user hasn't closed scanner
    setTimeout(async () => {
      if (!scanning) {
        try {
          await scanner.start(
            { facingMode: 'environment' },
            { fps: 10, qrbox: { width: 250, height: 250 } },
            onScan,
            () => {}
          );
          scanning = true;
        } catch (err) {
          console.error('Error restarting scanner:', err);
          result.textContent = 'Camera permission is required for QR scanning.';
        }
        enableButtons();
      }
    }, 4000);
  };

  // Wire up buttons
  if (openButton) {
    openButton.addEventListener('click', () => startScanner());
  }
  if (closeButton) {
    closeButton.addEventListener('click', () => stopScanner());
  }

  // Initialize buttons state: scanner closed by default
  scanning = false;
  enableButtons();
  console.log('Security scanner initialized');
});
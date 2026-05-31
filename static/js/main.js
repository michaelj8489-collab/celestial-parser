document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('download-form');
    const urlInput = document.getElementById('url-input');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    
    const statusMsg = document.getElementById('status-message');
    const resultContainer = document.getElementById('result-container');
    const filenameDisplay = document.getElementById('filename-display');
    const downloadLink = document.getElementById('download-link');
    const resetBtn = document.getElementById('reset-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const url = urlInput.value.trim();
        if (!url) return;

        // Reset UI state
        setLoading(true);
        hideStatus();
        resultContainer.classList.add('hidden');

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (data.success) {
                showSuccess(data);
            } else {
                showError(data.error || 'An error occurred during download.');
            }
        } catch (err) {
            showError('Network error. Please try again.');
        } finally {
            setLoading(false);
        }
    });

    resetBtn.addEventListener('click', () => {
        urlInput.value = '';
        resultContainer.classList.add('hidden');
        urlInput.focus();
    });

    function setLoading(isLoading) {
        if (isLoading) {
            submitBtn.disabled = true;
            btnText.textContent = 'Processing...';
            loader.classList.remove('hidden');
        } else {
            submitBtn.disabled = false;
            btnText.textContent = 'Download';
            loader.classList.add('hidden');
        }
    }

    function showError(msg) {
        statusMsg.textContent = msg;
        statusMsg.className = 'status-error';
        statusMsg.classList.remove('hidden');
    }

    function hideStatus() {
        statusMsg.classList.add('hidden');
        statusMsg.className = '';
        statusMsg.textContent = '';
    }

    function showSuccess(data) {
        form.classList.add('hidden'); // Optional: hide form to focus on result
        // Wait, we probably want to keep the form visible in case they want to download another right away.
        // Let's keep it visible.
        
        filenameDisplay.textContent = data.filename;
        downloadLink.href = `/api/serve/${encodeURIComponent(data.filename)}`;
        downloadLink.download = data.filename;
        
        resultContainer.classList.remove('hidden');
    }
});

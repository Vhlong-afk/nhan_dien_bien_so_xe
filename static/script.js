document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    const fileInfo = document.getElementById('fileInfo');
    const loading = document.getElementById('loading');
    const loadingText = document.querySelector('.loading p');
    const result = document.getElementById('result');
    const errorDiv = document.getElementById('error');
    const plateImg = document.getElementById('plateImg');
    const plateText = document.getElementById('plateText');
    const confidence = document.getElementById('confidence');
    const newDetectBtn = document.getElementById('newDetect');

    let isProcessing = false;

    // Click upload area to trigger file input
    uploadArea.addEventListener('click', (event) => {
        event.stopPropagation();  // 
    });

    // File input change
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const sizeMB = (file.size / 1024 / 1024).toFixed(2);
            fileInfo.textContent = `✅ File: ${file.name} (${sizeMB} MB)`;
            processFile(file);
        }
    });

    // New detect button
    newDetectBtn.addEventListener('click', () => {
        resetUI();
    });

    function processFile(file) {
        if (isProcessing) return;
        
        resetUI();
        isProcessing = true;
        
        const formData = new FormData();
        formData.append('file', file);

        loading.classList.remove('hidden');
        loadingText.textContent = '⏳ Đang xử lý... Vui lòng đợi';
        
        fetch('/detect', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `Server error ${response.status}`);
                }).catch(err => {
                    throw new Error(`Server error ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            loading.classList.add('hidden');
            isProcessing = false;
            
            if (data.error) {
                console.error('Server error:', data.error);
                showError(data.error);
            } else if (data.plate_image) {
                plateImg.src = 'data:image/jpeg;base64,' + data.plate_image;
                plateText.textContent = data.text;
                confidence.textContent = data.confidence;
                result.classList.remove('hidden');
                console.log('✅ Detection success:', data.text);
            } else if (data.result) {
                plateText.textContent = data.result;
                result.classList.remove('hidden');
                console.log('✅ Video processing complete');
            }
        })
        .catch(err => {
            loading.classList.add('hidden');
            isProcessing = false;
            console.error('Request error:', err);
            showError(`❌ Lỗi: ${err.message}`);
        });
    }

    function resetUI() {
        fileInput.value = '';
        fileInfo.textContent = '';
        result.classList.add('hidden');
        errorDiv.classList.add('hidden');
        plateImg.src = '';
        isProcessing = false;
    }

    function showError(message) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        result.classList.add('hidden');
    }
});
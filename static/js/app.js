document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const thumbnailStrip = document.getElementById('thumbnail-strip');
    
    const searchInput = document.getElementById('search-input');
    const resultsArea = document.getElementById('results-area');
    
    const previewModal = document.getElementById('preview-modal');
    const modalBackdrop = document.querySelector('.modal-backdrop');
    const closeModalBtn = document.querySelector('.close-modal-btn');
    const modalImage = document.getElementById('modal-image');
    const modalOcrText = document.getElementById('modal-ocr-text');
    
    // Toast Container Setup
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);

    // Initial Load
    loadLibrary();

    // ---------------------------------
    // 1. Upload Functionality
    // ---------------------------------

    // Browse Button
    browseBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFiles(e.target.files);
        }
    });

    // Drag and Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
    });

    dropArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    });

    async function uploadFiles(files) {
        const formData = new FormData();
        const fileIds = [];

        // Preview spinners
        Array.from(files).forEach((file, index) => {
            const tempId = 'temp-' + Date.now() + '-' + index;
            fileIds.push(tempId);
            formData.append('files', file);
            
            // Create loading thumbnail
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = function(e) {
                createThumbnail(tempId, e.target.result, true);
            };
        });

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            // Handle errors
            if (data.errors && data.errors.length > 0) {
                data.errors.forEach(err => showToast(err, 'error'));
            }

            // Replace temp thumbnails with real ones or remove if failed
            if (data.uploaded && data.uploaded.length > 0) {
                showToast(`Successfully uploaded ${data.uploaded.length} image(s)`, 'success');
                // Remove temp thumbs
                fileIds.forEach(id => {
                    const el = document.getElementById(`thumb-${id}`);
                    if (el) el.remove();
                });
                
                // Add actual uploaded items
                data.uploaded.forEach(item => {
                    addThumbnailToStrip(item);
                });
            } else {
                // If nothing uploaded, remove temp thumbs
                fileIds.forEach(id => {
                    const el = document.getElementById(`thumb-${id}`);
                    if (el) el.remove();
                });
            }
            
            // If search is active, we might want to re-search
            if (searchInput.value.trim().length >= 2) {
                performSearch(searchInput.value.trim());
            }

        } catch (error) {
            console.error('Upload error:', error);
            showToast('Upload failed due to network error.', 'error');
            fileIds.forEach(id => {
                const el = document.getElementById(`thumb-${id}`);
                if (el) el.remove();
            });
        }
        
        fileInput.value = ''; // Reset
    }

    function createThumbnail(id, src, isLoading = false) {
        const div = document.createElement('div');
        div.className = 'thumbnail-item';
        div.id = `thumb-${id}`;
        
        const img = document.createElement('img');
        img.src = src;
        
        const statusDiv = document.createElement('div');
        statusDiv.className = 'thumbnail-status';
        
        if (isLoading) {
            statusDiv.innerHTML = '<i class="fa-solid fa-spinner status-loading"></i>';
        } else {
            statusDiv.innerHTML = '<i class="fa-solid fa-check status-success"></i>';
        }
        
        div.appendChild(img);
        div.appendChild(statusDiv);
        
        // Prepend so newest is first
        thumbnailStrip.insertBefore(div, thumbnailStrip.firstChild);
        return div;
    }

    function addThumbnailToStrip(item) {
        const div = document.createElement('div');
        div.className = 'thumbnail-item';
        div.id = `thumb-${item.id || item.image_id}`;
        
        const img = document.createElement('img');
        img.src = item.thumbnail_url;
        img.alt = item.original_name;
        
        // Delete btn
        const delBtn = document.createElement('div');
        delBtn.className = 'thumbnail-delete';
        delBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        delBtn.onclick = (e) => {
            e.stopPropagation();
            deleteImage(item.id || item.image_id);
        };
        
        // Status indicator
        const statusDiv = document.createElement('div');
        statusDiv.className = 'thumbnail-status';
        
        const hasText = item.has_ocr_text !== undefined ? item.has_ocr_text : (item.ocr_preview && item.ocr_preview.length > 0);
        
        if (hasText) {
            statusDiv.innerHTML = '<i class="fa-solid fa-check status-success"></i>';
        } else {
            statusDiv.innerHTML = '<i class="fa-solid fa-triangle-exclamation status-warning" title="No text found"></i>';
            statusDiv.style.color = 'var(--warning)';
        }
        
        div.appendChild(img);
        div.appendChild(delBtn);
        div.appendChild(statusDiv);
        
        // Click to preview
        div.addEventListener('click', () => openPreview(item.id || item.image_id));
        
        thumbnailStrip.insertBefore(div, thumbnailStrip.firstChild);
    }

    async function loadLibrary() {
        try {
            const response = await fetch('/api/library');
            const data = await response.json();
            
            thumbnailStrip.innerHTML = '';
            
            // Append sequentially. They are ordered by newest first from backend.
            data.forEach(item => {
                const div = document.createElement('div');
                div.className = 'thumbnail-item';
                div.id = `thumb-${item.id}`;
                
                const img = document.createElement('img');
                img.src = item.thumbnail_url;
                img.alt = item.original_name;
                
                const delBtn = document.createElement('div');
                delBtn.className = 'thumbnail-delete';
                delBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
                delBtn.onclick = (e) => {
                    e.stopPropagation();
                    deleteImage(item.id);
                };
                
                const statusDiv = document.createElement('div');
                statusDiv.className = 'thumbnail-status';
                if (item.has_ocr_text) {
                    statusDiv.innerHTML = '<i class="fa-solid fa-check status-success"></i>';
                } else {
                    statusDiv.innerHTML = '<i class="fa-solid fa-triangle-exclamation status-warning" title="No text found"></i>';
                    statusDiv.style.color = 'var(--warning)';
                }
                
                div.appendChild(img);
                div.appendChild(delBtn);
                div.appendChild(statusDiv);
                
                div.addEventListener('click', () => openPreview(item.id));
                
                thumbnailStrip.appendChild(div);
            });
        } catch (error) {
            console.error('Failed to load library:', error);
        }
    }

    async function deleteImage(id) {
        if (!confirm('Are you sure you want to delete this image?')) return;
        
        try {
            const response = await fetch(`/api/images/${id}`, { method: 'DELETE' });
            if (response.ok) {
                const el = document.getElementById(`thumb-${id}`);
                if (el) el.remove();
                showToast('Image deleted successfully.', 'success');
                
                // Refresh search if active
                if (searchInput.value.trim().length >= 2) {
                    performSearch(searchInput.value.trim());
                }
            } else {
                showToast('Failed to delete image.', 'error');
            }
        } catch (error) {
            console.error(error);
            showToast('Network error during deletion.', 'error');
        }
    }

    // ---------------------------------
    // 2. Search Functionality
    // ---------------------------------
    
    let searchTimeout = null;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        clearTimeout(searchTimeout);
        
        if (query.length === 0) {
            showEmptyState('Start searching to see results', 'fa-magnifying-glass-chart');
            return;
        }
        
        if (query.length < 2) {
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    async function performSearch(query) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                renderResults(data.results, query);
            } else {
                showEmptyState(data.message || 'No documents matched your search.', 'fa-ghost');
            }
        } catch (error) {
            console.error('Search failed:', error);
            showEmptyState('Search failed due to an error.', 'fa-triangle-exclamation');
        }
    }

    function renderResults(results, query) {
        resultsArea.innerHTML = '';
        
        results.forEach((result, index) => {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.style.animationDelay = `${index * 0.05}s`;
            
            const thumb = document.createElement('img');
            thumb.className = 'result-thumb';
            thumb.src = result.thumbnail_url;
            
            const content = document.createElement('div');
            content.className = 'result-content';
            
            const snippet = document.createElement('p');
            snippet.className = 'result-snippet';
            
            if (result.highlight_ranges && result.highlight_ranges.length > 0) {
                let lastIdx = 0;
                let html = '';
                
                const ranges = [...result.highlight_ranges].sort((a,b) => a[0] - b[0]);
                const merged = [];
                if (ranges.length > 0) {
                    let current = [...ranges[0]];
                    for(let i=1; i<ranges.length; i++) {
                        if (ranges[i][0] <= current[1]) {
                            current[1] = Math.max(current[1], ranges[i][1]);
                        } else {
                            merged.push(current);
                            current = [...ranges[i]];
                        }
                    }
                    merged.push(current);
                }
                
                merged.forEach(range => {
                    const [start, end] = range;
                    html += escapeHtml(result.snippet.substring(lastIdx, start));
                    html += '<mark>' + escapeHtml(result.snippet.substring(start, end)) + '</mark>';
                    lastIdx = end;
                });
                
                html += escapeHtml(result.snippet.substring(lastIdx));
                snippet.innerHTML = html;
            } else {
                snippet.textContent = result.snippet;
            }
            
            const score = document.createElement('div');
            score.className = 'result-score';
            const percentage = Math.round(result.score * 100);
            score.innerHTML = `<i class="fa-solid fa-bolt"></i> ${percentage}% match`;
            
            content.appendChild(snippet);
            content.appendChild(score);
            
            card.appendChild(thumb);
            card.appendChild(content);
            
            card.addEventListener('click', () => openPreview(result.image_id));
            
            resultsArea.appendChild(card);
        });
    }

    function showEmptyState(message, iconClass) {
        resultsArea.innerHTML = `
            <div id="empty-state" class="empty-state">
                <div class="empty-state-icon">
                    <i class="fa-solid ${iconClass}"></i>
                </div>
                <p>${message}</p>
            </div>
        `;
    }

    function escapeHtml(unsafe) {
        return (unsafe || '').toString()
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    // ---------------------------------
    // 3. Preview Modal
    // ---------------------------------

    async function openPreview(imageId) {
        modalImage.src = '';
        modalOcrText.textContent = 'Loading...';
        previewModal.classList.add('active');
        
        modalImage.src = `/api/images/${imageId}`;
        
        try {
            const response = await fetch(`/api/images/${imageId}/ocr`);
            if (response.ok) {
                const data = await response.json();
                modalOcrText.textContent = data.ocr_text || 'No text extracted.';
            } else {
                modalOcrText.textContent = 'Failed to load text.';
            }
        } catch (e) {
            modalOcrText.textContent = 'Error loading text.';
        }
    }

    function closePreview() {
        previewModal.classList.remove('active');
        setTimeout(() => {
            modalImage.src = '';
            modalOcrText.textContent = '';
        }, 300); // wait for transition
    }

    closeModalBtn.addEventListener('click', closePreview);
    modalBackdrop.addEventListener('click', closePreview);
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && previewModal.classList.contains('active')) {
            closePreview();
        }
    });

    // ---------------------------------
    // Utilities
    // ---------------------------------
    
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? 'fa-check-circle' : 'fa-circle-exclamation';
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
        
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    // Session Identification & Persistence:
    // 1. URL parameter ?session_id=... (enables cross-device sync & link restoration)
    const urlParams = new URLSearchParams(window.location.search);
    let sessionId = urlParams.get('session_id');

    // 2. Persistent localStorage (survives page refreshes, tab close, and browser restarts)
    if (!sessionId) {
        sessionId = localStorage.getItem('ocr_session_id');
    }

    // 3. Server-injected meta tag (only for first-time visitors with empty localStorage)
    if (!sessionId) {
        const metaSession = document.querySelector('meta[name="session-id"]');
        sessionId = metaSession ? metaSession.getAttribute('content') : null;
    }

    // 4. Client-side fallback generator
    if (!sessionId) {
        sessionId = 'sess_' + (window.crypto && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
    }

    // Lock into localStorage for future refreshes
    localStorage.setItem('ocr_session_id', sessionId);

    function getSessionHeaders(customHeaders = {}) {
        return {
            'X-Session-ID': sessionId,
            ...customHeaders
        };
    }

    // DOM Elements
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const thumbnailStrip = document.getElementById('thumbnail-strip');
    const libraryCount = document.getElementById('library-count');
    const loadSampleBtn = document.getElementById('load-sample-btn');
    const newSessionBtn = document.getElementById('new-session-btn');
    const copySessionBtn = document.getElementById('copy-session-btn');
    const sessionMenuToggle = document.getElementById('session-menu-toggle');
    const sessionMenuDropdown = document.getElementById('session-menu-dropdown');
    
    // Session menu toggle
    if (sessionMenuToggle && sessionMenuDropdown) {
        sessionMenuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = !sessionMenuDropdown.classList.contains('hidden');
            sessionMenuDropdown.classList.toggle('hidden');
            sessionMenuToggle.setAttribute('aria-expanded', !isOpen);
        });
        document.addEventListener('click', () => {
            sessionMenuDropdown.classList.add('hidden');
            sessionMenuToggle.setAttribute('aria-expanded', 'false');
        });
        sessionMenuDropdown.addEventListener('click', () => {
            sessionMenuDropdown.classList.add('hidden');
            sessionMenuToggle.setAttribute('aria-expanded', 'false');
        });
    }
    
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
    // 1. Session Management
    // ---------------------------------

    if (copySessionBtn) {
        copySessionBtn.addEventListener('click', async () => {
            const shareUrl = `${window.location.origin}${window.location.pathname}?session_id=${encodeURIComponent(sessionId)}`;
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(shareUrl);
                } else {
                    const tempInput = document.createElement('textarea');
                    tempInput.value = shareUrl;
                    document.body.appendChild(tempInput);
                    tempInput.select();
                    document.execCommand('copy');
                    document.body.removeChild(tempInput);
                }
                showToast('Session link copied! Open on another device or tab to access this library.', 'success');
            } catch (err) {
                console.error('Clipboard copy failed:', err);
                prompt('Copy this link to access your session on another device:', shareUrl);
            }
        });
    }

    if (newSessionBtn) {
        newSessionBtn.addEventListener('click', async () => {
            if (!confirm('Start a fresh session? This creates a new private workspace for your documents.')) return;
            try {
                const response = await fetch('/api/session/reset', { 
                    method: 'POST', 
                    credentials: 'same-origin' 
                });
                const data = await response.json();
                if (data.session_id) {
                    sessionId = data.session_id;
                    localStorage.setItem('ocr_session_id', sessionId);
                    // Clean URL query param if present
                    if (window.history && window.history.replaceState) {
                        window.history.replaceState({}, document.title, window.location.pathname);
                    }
                    showToast('New session started!', 'success');
                    searchInput.value = '';
                    showEmptyState('Start searching to see results', 'fa-magnifying-glass-chart');
                    loadLibrary();
                }
            } catch (e) {
                console.error('Session reset failed:', e);
                showToast('Failed to reset session.', 'error');
            }
        });
    }

    if (loadSampleBtn) {
        loadSampleBtn.addEventListener('click', async () => {
            loadSampleBtn.disabled = true;
            loadSampleBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
            try {
                const response = await fetch('/api/load-samples', {
                    method: 'POST',
                    headers: getSessionHeaders(),
                    credentials: 'same-origin'
                });
                const data = await response.json();
                showToast(data.message || 'Sample documents loaded.', 'success');
                loadLibrary();
            } catch (e) {
                console.error('Sample loading failed:', e);
                showToast('Failed to load sample documents.', 'error');
            } finally {
                loadSampleBtn.disabled = false;
                loadSampleBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Load Sample Docs';
            }
        });
    }

    // ---------------------------------
    // 2. Upload Functionality
    // ---------------------------------

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
                headers: getSessionHeaders(),
                body: formData,
                credentials: 'same-origin'
            });
            const data = await response.json();

            // Handle errors
            if (data.errors && data.errors.length > 0) {
                data.errors.forEach(err => showToast(err, 'error'));
            }

            // Clean up temp thumbs
            fileIds.forEach(id => {
                const el = document.getElementById(`thumb-${id}`);
                if (el) el.remove();
            });

            // Replace temp thumbnails with real ones or remove if failed
            if (data.uploaded && data.uploaded.length > 0) {
                showToast(`Successfully uploaded ${data.uploaded.length} image(s)`, 'success');
                loadLibrary(); // Reload library to keep order, count, and status in sync
            }
            
            // If search is active, re-search
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
        // Clear empty state message if present
        const emptyEl = thumbnailStrip.querySelector('.library-empty');
        if (emptyEl) emptyEl.remove();

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
        
        thumbnailStrip.insertBefore(div, thumbnailStrip.firstChild);
        return div;
    }

    async function loadLibrary() {
        try {
            const response = await fetch('/api/library', {
                headers: getSessionHeaders(),
                credentials: 'same-origin'
            });
            const data = await response.json();
            
            thumbnailStrip.innerHTML = '';
            
            if (libraryCount) {
                libraryCount.textContent = data.length;
            }

            if (!data || data.length === 0) {
                thumbnailStrip.innerHTML = '<div class="library-empty">Your library is empty. Upload images above or click "Load Sample Docs" to test.</div>';
                return;
            }
            
            data.forEach(item => {
                const div = document.createElement('div');
                div.className = 'thumbnail-item';
                div.id = `thumb-${item.id}`;
                
                const img = document.createElement('img');
                img.src = `${item.thumbnail_url}?session_id=${encodeURIComponent(sessionId)}`;
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
            const response = await fetch(`/api/images/${id}`, { 
                method: 'DELETE',
                headers: getSessionHeaders(),
                credentials: 'same-origin'
            });
            if (response.ok) {
                const el = document.getElementById(`thumb-${id}`);
                if (el) el.remove();
                showToast('Image deleted successfully.', 'success');
                loadLibrary();
                
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
    // 3. Search Functionality
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

    document.querySelectorAll('.hint-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            if (query && searchInput) {
                searchInput.value = query;
                searchInput.focus();
                performSearch(query);
            }
        });
    });

    async function performSearch(query) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, {
                headers: getSessionHeaders(),
                credentials: 'same-origin'
            });
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
            thumb.src = `${result.thumbnail_url}?session_id=${encodeURIComponent(sessionId)}`;
            thumb.alt = 'Document thumbnail';
            
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
    // 4. Preview Modal
    // ---------------------------------

    async function openPreview(imageId) {
        modalImage.src = '';
        modalOcrText.textContent = 'Loading...';
        previewModal.classList.add('active');
        
        modalImage.src = `/api/images/${imageId}?session_id=${encodeURIComponent(sessionId)}`;
        
        try {
            const response = await fetch(`/api/images/${imageId}/ocr`, {
                headers: getSessionHeaders(),
                credentials: 'same-origin'
            });
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
        }, 300);
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


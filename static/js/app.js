/* ═══════════════════════════════════════════════════════════
   Photos — Document Search Prototype
   Frontend logic: upload, library, search, results, preview
   ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    // ─── Session Identification & Persistence ───
    const urlParams = new URLSearchParams(window.location.search);
    let sessionId = urlParams.get('session_id');

    if (!sessionId) {
        sessionId = localStorage.getItem('ocr_session_id');
    }
    if (!sessionId) {
        const metaSession = document.querySelector('meta[name="session-id"]');
        sessionId = metaSession ? metaSession.getAttribute('content') : null;
    }
    if (!sessionId) {
        sessionId = 'sess_' + (window.crypto && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
    }

    localStorage.setItem('ocr_session_id', sessionId);

    function getSessionHeaders(customHeaders = {}) {
        return { 'X-Session-ID': sessionId, ...customHeaders };
    }


    // ─── DOM References ───
    const dropArea       = document.getElementById('drop-area');
    const fileInput      = document.getElementById('file-input');
    const browseBtn      = document.getElementById('browse-btn');
    const photoGrid      = document.getElementById('photo-grid');
    const libraryCount   = document.getElementById('library-count');
    const loadSampleBtn  = document.getElementById('load-sample-btn');
    const newSessionBtn  = document.getElementById('new-session-btn');
    const copySessionBtn = document.getElementById('copy-session-btn');
    const sessionMenuToggle  = document.getElementById('session-menu-toggle');
    const sessionMenuDropdown = document.getElementById('session-menu-dropdown');
    const searchInput    = document.getElementById('search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const resultsArea    = document.getElementById('results-area');
    const previewModal   = document.getElementById('preview-modal');
    const modalBackdrop  = document.querySelector('.modal-backdrop');
    const closeModalBtn  = document.querySelector('.close-modal-btn');
    const modalImage     = document.getElementById('modal-image');
    const modalOcrText   = document.getElementById('modal-ocr-text');
    const uploadZone     = document.getElementById('upload-zone');
    const librarySection = document.getElementById('library-section');

    // Toast Container
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);

    // Initial load
    loadLibrary();


    // ═════════════════════════════════════════════
    // 1. SESSION MENU
    // ═════════════════════════════════════════════

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
        sessionMenuDropdown.addEventListener('click', (e) => {
            e.stopPropagation();
            sessionMenuDropdown.classList.add('hidden');
            sessionMenuToggle.setAttribute('aria-expanded', 'false');
        });
    }

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
                showToast('Link copied — open on another device to access this library', 'success');
            } catch (err) {
                console.error('Clipboard copy failed:', err);
                prompt('Copy this link to access your session:', shareUrl);
            }
        });
    }

    if (newSessionBtn) {
        newSessionBtn.addEventListener('click', async () => {
            if (!confirm('Start a fresh session? Your current documents will remain in the previous session.')) return;
            try {
                const response = await fetch('/api/session/reset', { method: 'POST', credentials: 'same-origin' });
                const data = await response.json();
                if (data.session_id) {
                    sessionId = data.session_id;
                    localStorage.setItem('ocr_session_id', sessionId);
                    if (window.history && window.history.replaceState) {
                        window.history.replaceState({}, document.title, window.location.pathname);
                    }
                    showToast('New session started', 'success');
                    searchInput.value = '';
                    hideResults();
                    loadLibrary();
                }
            } catch (e) {
                console.error('Session reset failed:', e);
                showToast('Failed to reset session', 'error');
            }
        });
    }

    if (loadSampleBtn) {
        loadSampleBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            loadSampleBtn.disabled = true;
            const originalHTML = loadSampleBtn.innerHTML;
            loadSampleBtn.innerHTML = '<span class="material-symbols-rounded" style="animation:spin 1s linear infinite">progress_activity</span>Loading…';
            try {
                const response = await fetch('/api/load-samples', {
                    method: 'POST',
                    headers: getSessionHeaders(),
                    credentials: 'same-origin'
                });
                const data = await response.json();
                showToast(data.message || 'Sample documents loaded', 'success');
                loadLibrary();
            } catch (e) {
                console.error('Sample loading failed:', e);
                showToast('Failed to load sample documents', 'error');
            } finally {
                loadSampleBtn.disabled = false;
                loadSampleBtn.innerHTML = originalHTML;
            }
        });
    }


    // ═════════════════════════════════════════════
    // 2. UPLOAD FUNCTIONALITY
    // ═════════════════════════════════════════════

    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    dropArea.addEventListener('click', () => {
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
        if (dt.files.length > 0) {
            uploadFiles(dt.files);
        }
    });

    async function uploadFiles(files) {
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });

        // Show indexing state in the library immediately
        showIndexingState(files.length);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: getSessionHeaders(),
                body: formData,
                credentials: 'same-origin'
            });
            const data = await response.json();

            if (data.errors && data.errors.length > 0) {
                data.errors.forEach(err => showToast(err, 'error'));
            }

            if (data.uploaded && data.uploaded.length > 0) {
                showToast(`${data.uploaded.length} photo${data.uploaded.length > 1 ? 's' : ''} added`, 'success');
                loadLibrary();
            } else {
                loadLibrary(); // Reload to clear indexing state
            }

            // Re-search if active
            if (searchInput.value.trim().length >= 2) {
                performSearch(searchInput.value.trim());
            }

        } catch (error) {
            console.error('Upload error:', error);
            showToast('Upload failed — check your connection', 'error');
            loadLibrary();
        }

        fileInput.value = '';
    }

    function showIndexingState(count) {
        // Temporarily show a polished indexing indicator in the grid
        const indexingEl = document.createElement('div');
        indexingEl.className = 'library-empty';
        indexingEl.id = 'indexing-indicator';
        indexingEl.innerHTML = `
            <span class="material-symbols-rounded" style="font-size:40px;color:var(--accent);animation:pulseStatus 2s ease-in-out infinite;display:block;margin:0 auto 12px">document_scanner</span>
            <div style="font-size:15px;font-weight:500;color:var(--text-primary);margin-bottom:4px">Understanding your documents…</div>
            <div style="font-size:13px;color:var(--text-secondary)">Extracting text · Indexing searchable content</div>
        `;
        // Prepend to grid
        if (photoGrid.firstChild) {
            photoGrid.insertBefore(indexingEl, photoGrid.firstChild);
        } else {
            photoGrid.appendChild(indexingEl);
        }
    }


    // ═════════════════════════════════════════════
    // 3. PHOTO LIBRARY
    // ═════════════════════════════════════════════

    let pollInterval = null;

    function startPolling() {
        if (!pollInterval) {
            pollInterval = setInterval(pollProcessingImages, 2500);
        }
    }

    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    async function pollProcessingImages() {
        const processingItems = Array.from(photoGrid.querySelectorAll('.photo-card[data-status="processing"]'));
        if (processingItems.length === 0) {
            stopPolling();
            return;
        }

        const ids = processingItems.map(item => item.dataset.docId);

        try {
            const response = await fetch('/api/ocr-status-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...getSessionHeaders() },
                body: JSON.stringify({ ids }),
                credentials: 'same-origin'
            });
            const data = await response.json();

            let anyUpdated = false;
            for (const [id, info] of Object.entries(data)) {
                if (info.status !== 'processing') {
                    anyUpdated = true;
                    const card = photoGrid.querySelector(`.photo-card[data-doc-id="${id}"]`);
                    if (card) {
                        card.dataset.status = info.status;
                        const statusEl = card.querySelector('.photo-card-status');
                        if (info.status === 'error') {
                            statusEl.className = 'photo-card-status status-error-badge';
                            statusEl.innerHTML = '<span class="material-symbols-rounded">warning</span>';
                            statusEl.title = info.error_message || 'Could not extract text';
                        } else if (info.has_ocr_text) {
                            statusEl.className = 'photo-card-status status-ready';
                            statusEl.innerHTML = '<span class="material-symbols-rounded">check_circle</span>';
                            // Fade out status after 3s
                            setTimeout(() => { statusEl.style.opacity = '0'; statusEl.style.transition = 'opacity 0.5s'; }, 3000);
                        } else {
                            statusEl.className = 'photo-card-status status-error-badge';
                            statusEl.innerHTML = '<span class="material-symbols-rounded">warning</span>';
                            statusEl.title = 'No text found in this image';
                        }
                    }
                }
            }
            if (anyUpdated && searchInput.value.trim().length >= 2) {
                performSearch(searchInput.value.trim());
            }
        } catch (error) {
            console.error('Failed to poll status:', error);
        }
    }

    async function loadLibrary() {
        try {
            const response = await fetch('/api/library', {
                headers: getSessionHeaders(),
                credentials: 'same-origin'
            });
            const data = await response.json();

            photoGrid.innerHTML = '';

            if (libraryCount) {
                libraryCount.textContent = data.length;
            }

            if (!data || data.length === 0) {
                photoGrid.innerHTML = `
                    <div class="library-empty">
                        <span class="material-symbols-rounded">photo_library</span>
                        <div>No photos yet</div>
                        <div style="font-size:13px;margin-top:4px">Upload documents above or load sample docs to get started</div>
                    </div>
                `;
                return;
            }

            let hasProcessing = false;

            data.forEach((item, index) => {
                const card = document.createElement('div');
                card.className = 'photo-card';
                card.dataset.docId = item.id;
                card.dataset.status = item.status;
                card.style.animationDelay = `${index * 30}ms`;

                const img = document.createElement('img');
                img.src = `${item.thumbnail_url}?session_id=${encodeURIComponent(sessionId)}`;
                img.alt = item.original_name;
                img.loading = 'lazy';

                // Overlay with label + delete
                const overlay = document.createElement('div');
                overlay.className = 'photo-card-overlay';

                const label = document.createElement('span');
                label.className = 'photo-card-label';
                // Show a brief OCR preview or filename
                label.textContent = item.ocr_preview
                    ? item.ocr_preview.substring(0, 40) + (item.ocr_preview.length > 40 ? '…' : '')
                    : item.original_name.replace(/^mock_/, '').replace(/\.[^.]+$/, '');

                const delBtn = document.createElement('button');
                delBtn.className = 'photo-card-delete';
                delBtn.innerHTML = '<span class="material-symbols-rounded">delete</span>';
                delBtn.title = 'Remove';
                delBtn.onclick = (e) => {
                    e.stopPropagation();
                    deleteImage(item.id);
                };

                overlay.appendChild(label);
                overlay.appendChild(delBtn);

                // Status indicator
                const statusEl = document.createElement('div');
                statusEl.className = 'photo-card-status';

                if (item.status === 'processing') {
                    hasProcessing = true;
                    statusEl.classList.add('status-processing');
                    statusEl.innerHTML = '<span class="material-symbols-rounded">progress_activity</span>';
                } else if (item.status === 'error') {
                    statusEl.classList.add('status-error-badge');
                    statusEl.innerHTML = '<span class="material-symbols-rounded">warning</span>';
                    statusEl.title = item.error_message || 'Could not extract text';
                } else if (item.has_ocr_text) {
                    statusEl.classList.add('status-ready');
                    statusEl.innerHTML = '<span class="material-symbols-rounded">check_circle</span>';
                    // Don't show the check for already-ready items
                    statusEl.style.display = 'none';
                } else {
                    statusEl.classList.add('status-error-badge');
                    statusEl.innerHTML = '<span class="material-symbols-rounded">warning</span>';
                    statusEl.title = 'No text found';
                }

                card.appendChild(img);
                card.appendChild(overlay);
                card.appendChild(statusEl);

                card.addEventListener('click', () => openPreview(item.id));

                photoGrid.appendChild(card);
            });

            if (hasProcessing) {
                startPolling();
            }
        } catch (error) {
            console.error('Failed to load library:', error);
        }
    }

    async function deleteImage(id) {
        if (!confirm('Remove this photo?')) return;

        try {
            const response = await fetch(`/api/images/${id}`, {
                method: 'DELETE',
                headers: getSessionHeaders(),
                credentials: 'same-origin'
            });
            if (response.ok) {
                showToast('Photo removed', 'success');
                loadLibrary();
                if (searchInput.value.trim().length >= 2) {
                    performSearch(searchInput.value.trim());
                }
            } else {
                showToast('Failed to remove photo', 'error');
            }
        } catch (error) {
            console.error(error);
            showToast('Network error', 'error');
        }
    }


    // ═════════════════════════════════════════════
    // 4. SEARCH FUNCTIONALITY
    // ═════════════════════════════════════════════

    let searchTimeout = null;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(searchTimeout);

        // Toggle clear button
        searchClearBtn.classList.toggle('hidden', query.length === 0);

        if (query.length === 0) {
            hideResults();
            return;
        }

        if (query.length < 2) return;

        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    searchClearBtn.addEventListener('click', () => {
        searchInput.value = '';
        searchClearBtn.classList.add('hidden');
        hideResults();
        searchInput.focus();
    });

    // Suggestion chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            if (query && searchInput) {
                searchInput.value = query;
                searchInput.focus();
                searchClearBtn.classList.remove('hidden');
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
                showNoResults(query);
            }
        } catch (error) {
            console.error('Search failed:', error);
            showResultsMessage('Search failed — please try again', 'error');
        }
    }

    function renderResults(results, query) {
        resultsArea.classList.remove('hidden');
        resultsArea.innerHTML = '';

        // Results heading
        const heading = document.createElement('div');
        heading.className = 'results-heading';
        heading.textContent = `${results.length} result${results.length !== 1 ? 's' : ''} for "${query}"`;
        resultsArea.appendChild(heading);

        results.forEach((result, index) => {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.style.animationDelay = `${index * 60}ms`;

            // Thumbnail
            const thumb = document.createElement('img');
            thumb.className = 'result-thumb';
            thumb.src = `${result.thumbnail_url}?session_id=${encodeURIComponent(sessionId)}`;
            thumb.alt = 'Document';
            thumb.loading = 'lazy';

            // Body
            const body = document.createElement('div');
            body.className = 'result-body';

            // Snippet with highlights
            const snippet = document.createElement('p');
            snippet.className = 'result-snippet';

            if (result.highlight_ranges && result.highlight_ranges.length > 0) {
                let lastIdx = 0;
                let html = '';

                const ranges = [...result.highlight_ranges].sort((a, b) => a[0] - b[0]);
                const merged = [];
                if (ranges.length > 0) {
                    let current = [...ranges[0]];
                    for (let i = 1; i < ranges.length; i++) {
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
                snippet.textContent = result.snippet || 'No preview available';
            }

            // "Why this matched" section
            const matchReason = document.createElement('div');
            matchReason.className = 'result-match-reason';

            const matchLabel = document.createElement('span');
            matchLabel.className = 'match-label';
            matchLabel.textContent = 'Matched:';
            matchReason.appendChild(matchLabel);

            const matchedTerms = result.matched_terms && result.matched_terms.length > 0
                ? result.matched_terms
                : query.split(/\s+/).filter(t => t.length >= 2);

            matchedTerms.forEach(term => {
                const termEl = document.createElement('span');
                termEl.className = 'match-term';
                // Format numbers with ₹ if digit-only
                const displayTerm = /^\d+$/.test(term) ? `₹${Number(term).toLocaleString('en-IN')}` : capitalize(term);
                termEl.innerHTML = `<span class="material-symbols-rounded">check</span>${escapeHtml(displayTerm)}`;
                matchReason.appendChild(termEl);
            });

            // Confidence indicator (non-technical)
            const confidence = document.createElement('div');
            confidence.className = 'result-confidence';
            const pct = Math.round(result.score * 100);
            let level, dotClass;
            if (pct >= 85) { level = 'Strong match'; dotClass = 'confidence-high'; }
            else if (pct >= 50) { level = 'Partial match'; dotClass = 'confidence-medium'; }
            else { level = 'Weak match'; dotClass = 'confidence-low'; }
            confidence.innerHTML = `<span class="confidence-dot ${dotClass}"></span>${level}`;

            body.appendChild(snippet);
            body.appendChild(matchReason);
            body.appendChild(confidence);

            card.appendChild(thumb);
            card.appendChild(body);

            card.addEventListener('click', () => openPreview(result.image_id));

            resultsArea.appendChild(card);
        });

        // Scroll results into view
        resultsArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function showNoResults(query) {
        resultsArea.classList.remove('hidden');
        resultsArea.innerHTML = `
            <div class="empty-state">
                <span class="material-symbols-rounded empty-state-icon">image_search</span>
                <div class="empty-state-title">No matching photos found</div>
                <div class="empty-state-message">
                    We couldn't find a document containing<br>
                    <strong>"${escapeHtml(query)}"</strong>
                </div>
                <ul class="empty-state-suggestions">
                    <li>Try a person's name</li>
                    <li>Try an exact word from the document</li>
                    <li>Try a month (September, March)</li>
                    <li>Try an amount (6500, 2340)</li>
                    <li>Try a merchant or medicine name</li>
                </ul>
            </div>
        `;
    }

    function showResultsMessage(message, type) {
        resultsArea.classList.remove('hidden');
        const iconName = type === 'error' ? 'error' : 'search';
        resultsArea.innerHTML = `
            <div class="empty-state">
                <span class="material-symbols-rounded empty-state-icon">${iconName}</span>
                <div class="empty-state-title">${escapeHtml(message)}</div>
            </div>
        `;
    }

    function hideResults() {
        resultsArea.classList.add('hidden');
        resultsArea.innerHTML = '';
    }


    // ═════════════════════════════════════════════
    // 5. PREVIEW MODAL
    // ═════════════════════════════════════════════

    async function openPreview(imageId) {
        modalImage.src = '';
        modalOcrText.textContent = 'Loading…';
        previewModal.classList.remove('hidden');
        previewModal.classList.add('active');

        modalImage.src = `/api/images/${imageId}?session_id=${encodeURIComponent(sessionId)}`;

        try {
            const response = await fetch(`/api/images/${imageId}/ocr`, {
                headers: getSessionHeaders(),
                credentials: 'same-origin'
            });
            if (response.ok) {
                const data = await response.json();
                modalOcrText.textContent = data.ocr_text || 'No text extracted from this photo.';
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
            previewModal.classList.add('hidden');
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


    // ═════════════════════════════════════════════
    // UTILITIES
    // ═════════════════════════════════════════════

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const iconName = type === 'success' ? 'check_circle' : 'error';
        toast.innerHTML = `<span class="material-symbols-rounded">${iconName}</span><span>${escapeHtml(message)}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    function escapeHtml(unsafe) {
        return (unsafe || '').toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

});

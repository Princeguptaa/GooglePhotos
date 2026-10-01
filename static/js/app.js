document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const thumbStrip = document.getElementById('thumbnail-strip');
    const searchInput = document.getElementById('search-input');
    const resultsGrid = document.getElementById('results-grid');
    const emptyState = document.getElementById('empty-state');
    const emptyMessage = document.getElementById('empty-message');
    
    // Modal
    const modal = document.getElementById('preview-modal');
    const modalImg = document.getElementById('modal-image');
    const modalText = document.getElementById('modal-ocr-text');
    const closeBtn = document.getElementById('close-modal');

    // State
    let searchTimeout = null;

    // Load library on start
    fetchLibrary();

    // --- Upload Logic ---
    browseBtn.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', (e) => {
        if(e.target.files.length > 0) uploadFiles(e.target.files);
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add('drag-over'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('drag-over'), false);
    });

    dropArea.addEventListener('drop', (e) => {
        let dt = e.dataTransfer;
        let files = dt.files;
        if(files.length > 0) uploadFiles(files);
    });

    async function uploadFiles(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.errors && data.errors.length > 0) {
                alert("Upload issues:\n" + data.errors.join("\n"));
            }
            
            // Refresh library
            fetchLibrary();
            
        } catch (err) {
            alert('Upload failed: ' + err.message);
        }
    }

    async function fetchLibrary() {
        try {
            const res = await fetch('/api/library');
            const data = await res.json();
            
            if (data.length > 0) {
                thumbStrip.classList.remove('hidden');
                thumbStrip.innerHTML = '';
                data.forEach(doc => {
                    const el = document.createElement('div');
                    el.className = 'thumb-card';
                    el.innerHTML = `
                        <img src="${doc.thumbnail_url}" alt="${doc.original_name}">
                        <button class="thumb-delete" data-id="${doc.image_id}">×</button>
                        <span class="thumb-status">${doc.has_ocr_text ? '✅' : '⚠️'}</span>
                    `;
                    thumbStrip.appendChild(el);
                });
                
                // Add delete listeners
                document.querySelectorAll('.thumb-delete').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const id = e.target.getAttribute('data-id');
                        if (confirm('Delete this document?')) {
                            await fetch(`/api/images/${id}`, { method: 'DELETE' });
                            fetchLibrary();
                            if(searchInput.value.trim().length >= 2) performSearch(searchInput.value.trim());
                        }
                    });
                });
            } else {
                thumbStrip.classList.add('hidden');
            }
        } catch(e) {
            console.error("Failed to fetch library", e);
        }
    }

    // --- Search Logic ---
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(searchTimeout);
        
        if (query.length < 2) {
            resultsGrid.classList.add('hidden');
            emptyState.classList.remove('hidden');
            emptyMessage.textContent = "Upload documents and search to see results here.";
            return;
        }

        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    async function performSearch(query) {
        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            
            if (res.status === 400 || !data.results || data.results.length === 0) {
                resultsGrid.classList.add('hidden');
                emptyState.classList.remove('hidden');
                emptyMessage.textContent = data.message || "No documents matched your search.";
                return;
            }

            emptyState.classList.add('hidden');
            resultsGrid.classList.remove('hidden');
            resultsGrid.innerHTML = '';

            data.results.forEach((result, idx) => {
                const card = document.createElement('div');
                card.className = 'result-card glass-card';
                card.style.animationDelay = `${idx * 0.1}s`;
                card.onclick = () => openPreview(result.image_id);
                
                // Construct snippet with <mark> tags safely
                let snippetHTML = result.snippet;
                // Work backwards through highlight ranges to insert tags without messing up indices
                const ranges = [...result.highlight_ranges].sort((a,b) => b[0] - a[0]);
                ranges.forEach(range => {
                    const start = range[0];
                    const end = range[1];
                    snippetHTML = snippetHTML.substring(0, start) + 
                                  '<mark>' + snippetHTML.substring(start, end) + '</mark>' + 
                                  snippetHTML.substring(end);
                });

                card.innerHTML = `
                    <img class="result-thumb" src="${result.thumbnail_url}" alt="${result.original_name}">
                    <div class="result-info">
                        <div class="result-header">
                            <span class="result-title">${result.original_name}</span>
                            <span class="result-score">${result.score}% match</span>
                        </div>
                        <p class="result-snippet">${snippetHTML}</p>
                    </div>
                `;
                resultsGrid.appendChild(card);
            });
        } catch(e) {
            console.error("Search failed", e);
        }
    }

    // --- Modal Logic ---
    async function openPreview(id) {
        modal.classList.remove('hidden');
        modalImg.src = `/api/images/${id}`;
        modalText.textContent = "Loading OCR text...";
        
        try {
            const res = await fetch(`/api/images/${id}/ocr`);
            const data = await res.json();
            modalText.textContent = data.ocr_text || "No text extracted.";
        } catch (e) {
            modalText.textContent = "Error loading text.";
        }
    }

    function closeModal() {
        modal.classList.add('hidden');
        modalImg.src = '';
    }

    closeBtn.addEventListener('click', closeModal);
    modal.querySelector('.modal-backdrop').addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
        if(e.key === 'Escape') closeModal();
    });
});

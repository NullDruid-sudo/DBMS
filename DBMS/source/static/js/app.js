/* ═══════════════════════════════════════════════════════════════════════════
   DigiLocker — Frontend Interactivity
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initUploadZone();
    initModals();
    initFlashMessages();
    initSearch();
});

/* ── Mobile Menu ─────────────────────────────────────────────────────────── */

function initMobileMenu() {
    const toggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');

    if (!toggle || !sidebar) return;

    toggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    // Close sidebar on outside click
    document.addEventListener('click', (e) => {
        if (sidebar.classList.contains('open') &&
            !sidebar.contains(e.target) &&
            !toggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });
}

/* ── Upload Zone (Drag & Drop) ───────────────────────────────────────────── */

function initUploadZone() {
    const zone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');

    if (!zone) return;

    ['dragenter', 'dragover'].forEach(evt => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
        });
    });

    zone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0 && fileInput) {
            fileInput.files = files;
            updateFileLabel(files[0], fileLabel);
        }
    });

    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                updateFileLabel(fileInput.files[0], fileLabel);
            }
        });
    }
}

function updateFileLabel(file, label) {
    if (!label) return;
    const size = formatSize(file.size);
    label.innerHTML = `<strong>📄 ${file.name}</strong><br><span class="text-muted">${size}</span>`;
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/* ── Modals ──────────────────────────────────────────────────────────────── */

function initModals() {
    // Close modal on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(m => {
                m.classList.remove('active');
            });
        }
    });
}

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('active');
}

/* ── Share Document ──────────────────────────────────────────────────────── */

function shareDocument(docId) {
    fetch(`/share/${docId}`, { method: 'POST' })
        .then(resp => resp.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }
            const urlInput = document.getElementById('shareUrl');
            const modal = document.getElementById('shareModal');
            if (urlInput) urlInput.value = data.url;
            if (modal) modal.classList.add('active');
        })
        .catch(() => showToast('Failed to create share link', 'error'));
}

function copyShareUrl() {
    const input = document.getElementById('shareUrl');
    if (!input) return;
    input.select();
    navigator.clipboard.writeText(input.value);
    showToast('Link copied to clipboard!', 'success');
}

/* ── Search ──────────────────────────────────────────────────────────────── */

function initSearch() {
    const input = document.getElementById('docSearch');
    if (!input) return;

    let timeout;
    input.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            const query = input.value.trim();
            const url = new URL(window.location);
            if (query) {
                url.searchParams.set('search', query);
            } else {
                url.searchParams.delete('search');
            }
            window.location.href = url.toString();
        }, 600);
    });
}

/* ── Flash / Toast Messages ──────────────────────────────────────────────── */

function initFlashMessages() {
    const container = document.querySelector('.flash-container');
    if (!container) return;

    // Auto-dismiss after animation
    container.querySelectorAll('.flash-message').forEach(msg => {
        setTimeout(() => {
            msg.style.display = 'none';
        }, 4400);
    });
}

function showToast(message, type = 'info') {
    let container = document.querySelector('.flash-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-container';
        document.body.appendChild(container);
    }

    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };

    const toast = document.createElement('div');
    toast.className = `flash-message ${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span> ${message}`;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 4500);
}

/* ── Delete Confirmation ─────────────────────────────────────────────────── */

function confirmDelete(docId, fileName) {
    const modal = document.getElementById('deleteModal');
    const form = document.getElementById('deleteForm');
    const nameEl = document.getElementById('deleteFileName');

    if (form) form.action = `/delete/${docId}`;
    if (nameEl) nameEl.textContent = fileName;
    if (modal) modal.classList.add('active');
}

// --- Global State ---
let allBooks = [];
let filteredBooks = [];
let epubBook = null;
let epubRendition = null;
let readerCurrentBookId = null;
let readerDarkTheme = true;
let activeProfileId = 1; // Default profile id that always exists

let currentView = 'gallery';
let currentFilter = 'kindle';
let currentFormatFilter = 'all';
let sortOrder = 'desc'; // 'asc' or 'desc'
let selectedIds = new Set();
let lastConnectedState = false;
let maintenanceMode = false;
const KINDLE_FORMATS = ['.epub', '.mobi', '.azw3', '.azw', '.kfx'];
let booksRendered = 0; // Count of rendered books
const BOOKS_PER_PAGE = 50; // Books to load per scroll
let observer = null;

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    renderSkeleton(); // Show skeleton immediately
    loadBooks(); // Load books directly since profiles are disabled
    checkDeviceStatus(true);
    setInterval(() => checkDeviceStatus(true), 3000);

    // Sync manual input with hidden input
    document.getElementById('manualKindlePathInput').value = document.getElementById('kindlePath').value;

    setupObserver();
    setupSSE();
});

function initTheme() {
    const savedTheme = localStorage.getItem('calibreTheme') || 'dark';
    const selector = document.getElementById('themeSelector');
    if (selector) selector.value = savedTheme;
    applyTheme(savedTheme);
}

function applyTheme(themeName) {
    localStorage.setItem('calibreTheme', themeName);
    document.documentElement.setAttribute('data-theme', themeName);
    if (themeName === 'light' || themeName === 'pink') {
        document.documentElement.classList.remove('dark');
    } else {
        document.documentElement.classList.add('dark');
    }
}

function setupSSE() {
    const evtSource = new EventSource('/api/v1/events');
    evtSource.onmessage = function (event) {
        if (event.data === 'new_book' || event.data === 'refresh') {
            console.log("Novo e-book detectado pelo servidor, recarregando...");
            loadBooks();
            showToast("New book added to library!", "success");
        }
    };
    evtSource.onerror = function (err) {
        console.error("SSE Connection Error:", err);
    };
}

function setupObserver() {
    const options = {
        root: null,
        rootMargin: '100px',
        threshold: 0.1
    };

    observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                renderMoreBooks();
            }
        });
    }, options);
}

// --- Core UI Functions ---

function renderSkeleton() {
    const grid = document.getElementById('galleryGrid');
    grid.innerHTML = '';
    for (let i = 0; i < 12; i++) {
        grid.innerHTML += `
        <div class="bg-darkcard border border-darkborder rounded-lg p-3 animate-pulse">
            <div class="w-full aspect-[2/3] bg-gray-800 rounded mb-3"></div>
            <div class="h-4 bg-gray-800 rounded w-3/4 mb-2"></div>
            <div class="h-3 bg-gray-800 rounded w-1/2"></div>
        </div>`;
    }
}

function getFormatBadgeColor(ext) {
    const e = ext.toLowerCase();
    if (e === '.pdf') return 'bg-red-500/10 text-red-400 border-red-500/20';
    if (e === '.epub') return 'bg-green-500/10 text-green-400 border-green-500/20';
    if (e === '.mobi' || e === '.azw3') return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
    if (['.cbz', '.cbr'].includes(e)) return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    return 'bg-gray-700/30 text-gray-400 border-gray-600/30';
}

function toggleSortOrder() {
    sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    document.getElementById('sortOrderIcon').innerText = sortOrder === 'asc' ? '⬆️' : '⬇️';
    applyFilters();
}

function sortBooksArray(booksArray) {
    const sortBy = document.getElementById('sortOption').value;

    return booksArray.sort((a, b) => {
        let valA = a[sortBy];
        let valB = b[sortBy];

        // Tratar added_date que pode ser null, fallback pra string vazia
        if (sortBy === 'added_date') {
            valA = valA || "";
            valB = valB || "";
        } else {
            valA = (valA || "").toString().toLowerCase();
            valB = (valB || "").toString().toLowerCase();
        }

        let comparison = 0;
        if (valA < valB) {
            comparison = -1;
        } else if (valA > valB) {
            comparison = 1;
        }

        return sortOrder === 'asc' ? comparison : -comparison;
    });
}

// --- Logic ---

async function loadBooks() {
    try {
        const response = await fetch('/api/v1/books');
        allBooks = await response.json();
        applyFilters(); // Render comes from here
    } catch (error) {
        showToast("Error loading library", "error");
    }
}

function renderBooks() {
    const tbody = document.getElementById('booksTable');
    const grid = document.getElementById('galleryGrid');
    const emptyState = document.getElementById('emptyState');
    const listView = document.getElementById('listViewContainer');
    const galleryView = document.getElementById('galleryViewContainer');

    // Toggle Containers
    if (filteredBooks.length === 0) {
        listView.classList.add('hidden');
        galleryView.classList.add('hidden');
        emptyState.classList.remove('hidden');
        return;
    } else {
        emptyState.classList.add('hidden');
        if (currentView === 'list') {
            listView.classList.remove('hidden');
            galleryView.classList.add('hidden');
        } else {
            listView.classList.add('hidden');
            galleryView.classList.remove('hidden');
        }
    }

    // Render content
    // Setup initial render state
    booksRendered = 0;
    tbody.innerHTML = '';
    grid.innerHTML = '';

    // Render first batch
    renderMoreBooks();
}

function renderMoreBooks() {
    if (booksRendered >= filteredBooks.length) return;

    const tbody = document.getElementById('booksTable');
    const grid = document.getElementById('galleryGrid');
    const listObserverTarget = document.getElementById('listObserverTarget');
    const gridObserverTarget = document.getElementById('gridObserverTarget');

    // Pega o spinner correto baseado na view atual
    const loadingSpinner = currentView === 'list'
        ? document.getElementById('loadingSpinnerList')
        : document.getElementById('loadingSpinnerGrid');

    // Unobserve before rendering changes to prevent multiple triggers
    if (observer && listObserverTarget) observer.unobserve(listObserverTarget);
    if (observer && gridObserverTarget) observer.unobserve(gridObserverTarget);

    if (loadingSpinner) loadingSpinner.classList.remove('hidden');

    const endIndex = Math.min(booksRendered + BOOKS_PER_PAGE, filteredBooks.length);
    const batch = filteredBooks.slice(booksRendered, endIndex);

    batch.forEach(book => {
        const isSelected = selectedIds.has(book.id);
        const formatClass = getFormatBadgeColor(book.file_type);
        const formatLabel = book.file_type.replace('.', '').toUpperCase();
        const coverUrl = book.cover_path && book.cover_path.trim() !== '' ? book.cover_path : null;
        const placeholderCover = `data:image/svg+xml;base64,${btoa('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="300" viewBox="0 0 200 300"><rect width="200" height="300" rx="0" fill="#1e2a3a"/><g transform="translate(100,120)" opacity="0.7"><path d="M-40,25 L-40,-20 C-40,-25 -35,-30 -30,-30 L-5,-25 L-5,30 L-30,25 C-35,25 -40,22 -40,18Z" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linejoin="round"/><path d="M40,25 L40,-20 C40,-25 35,-30 30,-30 L5,-25 L5,30 L30,25 C35,25 40,22 40,18Z" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linejoin="round"/><line x1="-5" y1="-25" x2="-5" y2="30" stroke="#3b82f6" stroke-width="2"/><line x1="5" y1="-25" x2="5" y2="30" stroke="#3b82f6" stroke-width="2"/><path d="M0,-30 L0,32" stroke="#3b82f6" stroke-width="1.5" opacity="0.4"/><text x="0" y="-10" fill="#3b82f6" text-anchor="middle" font-size="28" font-family="serif" opacity="0.5">?</text></g><text x="100" y="210" fill="#5a7a9a" text-anchor="middle" font-size="13" font-family="system-ui,sans-serif" font-weight="500" letter-spacing="1">SEM CAPA</text></svg>')}`;

        // Gallery Card
        const card = document.createElement('div');
        card.id = `book-card-${book.id}`;
        card.className = `group relative bg-[#252527] border ${isSelected ? 'border-blue-500 ring-1 ring-blue-500' : 'border-[#333] hover:border-[#555]'} rounded-2xl overflow-hidden transition-all duration-200 hover:-translate-y-1 shadow-lg hover:shadow-xl cursor-pointer`;
        card.onclick = () => toggleSelection(book.id);
        card.innerHTML = `
            <div class="book-cover-container w-full bg-[#1a1a1a] relative">
                <img src="${coverUrl || placeholderCover}" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" loading="lazy" onerror="this.onerror=null;this.src='${placeholderCover}'">
                
                <!-- Format Badge -->
                <div class="absolute top-2.5 left-2.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${formatClass} backdrop-blur-sm">
                    ${formatLabel}
                </div>

                <!-- Checkbox (when selected) -->
                <div class="selection-indicator absolute top-2.5 right-2.5 w-6 h-6 rounded-full border-2 ${isSelected ? 'bg-blue-500 border-blue-500' : 'border-white/20 bg-black/30 opacity-0 group-hover:opacity-100'} flex items-center justify-center transition-all">
                    ${isSelected ? '<svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>' : ''}
                </div>

                <!-- Contextual Menu Button (three dots) -->
                <button onclick="toggleCardMenu(${book.id}, event)" class="absolute bottom-2.5 right-2.5 w-7 h-7 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-all">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="6" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="18" r="1.5"/></svg>
                </button>

                <!-- Context Menu Dropdown -->
                <div id="card-menu-${book.id}" class="card-context-menu hidden absolute bottom-12 right-2 w-44 bg-[#1e1e1e] border border-[#333] rounded-xl shadow-2xl z-50 overflow-hidden py-1">
                    ${['.epub', '.mobi', '.azw3', '.pdf', '.fb2', '.cbz'].includes(book.file_type.toLowerCase()) ? `<button onclick="openReader(${book.id}, event)" class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-300 hover:bg-[#2a2a2a] hover:text-white transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>${t('btn_read')}</button>` : ''}
                    <button onclick="sendToKindle(${book.id}, this, event)" class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-300 hover:bg-[#2a2a2a] hover:text-white transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>${t('btn_send_kindle')}</button>
                    <div class="border-t border-[#333] my-1"></div>
                    <button onclick="openEditModal(${book.id}, event)" class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-300 hover:bg-[#2a2a2a] hover:text-white transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>${t('btn_edit_metadata')}</button>
                    <a href="/api/v1/books/${book.id}/download" onclick="event.stopPropagation()" class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-300 hover:bg-[#2a2a2a] hover:text-white transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>${t('btn_download')}</a>
                    <div class="border-t border-[#333] my-1"></div>
                    <button onclick="selectedIds.clear(); selectedIds.add(${book.id}); openDeleteModal(); event.stopPropagation();" class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>${t('btn_delete')}</button>
                </div>
            </div>
            <div class="p-3">
                ${book.series ? `<p class="text-[10px] font-bold text-blue-400/70 uppercase tracking-wider mb-0.5">${book.series}${book.volume ? ' - Vol. ' + book.volume : ''}</p>` : ''}
                <h3 class="text-sm font-semibold text-gray-200 line-clamp-2 leading-snug mb-1" title="${book.title}">${book.title}</h3>
                <p class="text-xs text-gray-500 truncate">${book.author}</p>
            </div>
        `;
        grid.appendChild(card);

        // List Row
        const tr = document.createElement('tr');
        tr.id = `book-row-${book.id}`;
        tr.className = `border-b border-darkborder transition-colors cursor-pointer ${isSelected ? 'bg-kindle/5 hover:bg-kindle/10' : 'hover:bg-[#222]'}`;
        tr.onclick = () => toggleSelection(book.id);
        tr.innerHTML = `
            <td class="py-3 px-6 text-center">
                <label class="inline-flex items-center cursor-pointer pointer-events-none">
                    <input type="checkbox" class="selection-indicator-cb w-4 h-4 rounded appearance-none border border-gray-500 bg-transparent checked:bg-kindle checked:border-kindle transition-colors relative after:content-[''] after:absolute after:hidden checked:after:block after:left-[5px] after:top-[2px] after:w-[5px] after:h-[9px] after:border-r-2 after:border-b-2 after:border-white after:rotate-45" ${isSelected ? 'checked' : ''}>
                </label>
            </td>
            <td class="py-2 px-6">
                <img src="${coverUrl}" class="w-8 h-12 object-cover rounded shadow-sm">
            </td>
            <td class="py-3 px-6">
                <p class="font-medium text-gray-200 truncate max-w-xs">${book.title}</p>
                ${book.series ? `<p class="text-[10px] font-bold text-kindle/70 uppercase tracking-wider mt-0.5">${book.series}${book.volume ? ' - Vol. ' + book.volume : ''}</p>` : ''}
            </td>
            <td class="py-3 px-6 text-gray-400">${book.author}</td>
            <td class="py-3 px-6 text-center">
                <span class="px-2 py-1 rounded text-[10px] font-bold uppercase border ${formatClass}">${formatLabel}</span>
            </td>
            <td class="py-3 px-6 text-right">
                 ${maintenanceMode ?
                `<button onclick="openEditModal(${book.id}, event)" class="text-gray-500 hover:text-white mr-3">${t('btn_edit_metadata')}</button>` :
                `${['.epub', '.mobi', '.azw3', '.pdf', '.fb2', '.cbz'].includes(book.file_type.toLowerCase()) ? `<button onclick="openReader(${book.id}, event)" class="text-kindle hover:text-white font-medium text-xs mr-3">${t('btn_read')}</button>` : ''}
                <button onclick="sendToKindle(${book.id}, this, event)" class="text-kindle hover:text-white font-medium text-xs">${t('btn_send_kindle')}</button>`
            }
            </td>
        `;
        tbody.appendChild(tr);
    });

    booksRendered = endIndex;

    // Re-observe if there's more to load
    if (booksRendered < filteredBooks.length) {
        if (observer && listObserverTarget && currentView === 'list') {
            console.log('Observing list target');
            observer.observe(listObserverTarget);
        } else if (observer && gridObserverTarget && currentView !== 'list') {
            console.log('Observing grid target');
            observer.observe(gridObserverTarget);
        }
    } else {
        console.log('Finished loading all books');
    }
    if (loadingSpinner) loadingSpinner.classList.add('hidden');
}

// --- Selection & Action Bar ---
function toggleSelection(id) {
    if (selectedIds.has(id)) selectedIds.delete(id);
    else selectedIds.add(id);
    updateSelectionVisuals(id);
    updateActionBar();
}

function toggleSelectAll() {
    const allSelected = selectedIds.size === filteredBooks.length;
    if (allSelected) {
        selectedIds.clear();
    } else {
        filteredBooks.forEach(b => selectedIds.add(b.id));
    }
    updateActionBar();
    filteredBooks.forEach(b => updateSelectionVisuals(b.id));
}

function clearSelection() {
    const idsToClear = Array.from(selectedIds);
    selectedIds.clear();
    updateActionBar();
    idsToClear.forEach(id => updateSelectionVisuals(id));
}

function updateSelectionVisuals(id) {
    const isSelected = selectedIds.has(id);
    const svgIcon = '<svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';

    // Update Card
    const card = document.getElementById(`book-card-${id}`);
    if (card) {
        if (isSelected) {
            card.classList.add('border-kindle', 'ring-1', 'ring-kindle');
            card.classList.remove('border-darkborder', 'hover:border-gray-500');
            const checkbox = card.querySelector('.selection-indicator');
            if (checkbox) {
                checkbox.classList.add('bg-kindle', 'border-kindle');
                checkbox.classList.remove('border-white/30', 'bg-black/40');
                checkbox.innerHTML = svgIcon;
            }
        } else {
            card.classList.remove('border-kindle', 'ring-1', 'ring-kindle');
            card.classList.add('border-darkborder', 'hover:border-gray-500');
            const checkbox = card.querySelector('.selection-indicator');
            if (checkbox) {
                checkbox.classList.remove('bg-kindle', 'border-kindle');
                checkbox.classList.add('border-white/30', 'bg-black/40');
                checkbox.innerHTML = '';
            }
        }
    }

    // Update Row
    const row = document.getElementById(`book-row-${id}`);
    if (row) {
        if (isSelected) {
            row.classList.add('bg-kindle/5', 'hover:bg-kindle/10');
            row.classList.remove('hover:bg-[#222]');
            const checkbox = row.querySelector('.selection-indicator-cb');
            if (checkbox) checkbox.checked = true;
        } else {
            row.classList.remove('bg-kindle/5', 'hover:bg-kindle/10');
            row.classList.add('hover:bg-[#222]');
            const checkbox = row.querySelector('.selection-indicator-cb');
            if (checkbox) checkbox.checked = false;
        }
    }
}

function updateActionBar() {
    const bar = document.getElementById('selectionBar');
    const count = selectedIds.size;
    document.getElementById('selectedCountBadge').innerText = count;

    // Update Select-All checkbox state if it exists
    const selectAllCb = document.getElementById('selectAllCheckbox');
    if (selectAllCb) {
        selectAllCb.checked = count > 0 && count === filteredBooks.length;
        selectAllCb.indeterminate = count > 0 && count < filteredBooks.length;
    }

    const btnSend = document.getElementById('btnActionBarSend');
    const btnConfirm = document.getElementById('btnConfirmDelete');

    // Action Button Context
    if (maintenanceMode) {
        btnSend.innerHTML = `<span>Delete Selected</span>`;
        btnSend.className = "flex items-center gap-2 px-5 py-2 bg-red-600 hover:bg-red-500 text-white font-semibold rounded-xl shadow-lg shadow-red-900/20 transition-all";
        btnSend.onclick = openDeleteModal;
    } else {
        btnSend.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg><span>Send to Device</span>`;
        btnSend.className = "flex items-center gap-2 px-5 py-2 bg-kindle hover:bg-kindlehover text-white font-semibold rounded-xl shadow-lg shadow-kindle/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed";
        btnSend.onclick = sendSelectedBatch;
        btnSend.disabled = !lastConnectedState;
    }

    if (count > 0) {
        bar.classList.remove('translate-y-32');
    } else {
        bar.classList.add('translate-y-32');
    }
}

// --- Filters & View ---
function applyFilters() {
    const term = document.getElementById('searchInput').value.toLowerCase();

    if (currentFilter === 'kindle') {
        filteredBooks = allBooks.filter(b => KINDLE_FORMATS.includes(b.file_type.toLowerCase()));
    } else {
        filteredBooks = [...allBooks];
    }

    if (currentFormatFilter !== 'all') {
        filteredBooks = filteredBooks.filter(b => b.file_type.toLowerCase() === currentFormatFilter);
    }

    if (term) {
        filteredBooks = filteredBooks.filter(b =>
            b.title.toLowerCase().includes(term) ||
            b.author.toLowerCase().includes(term)
        );
    }

    filteredBooks = sortBooksArray(filteredBooks);
    renderBooks();
}

function setFormatFilter(format) {
    currentFormatFilter = format;

    // Update UI
    const buttons = document.querySelectorAll('.format-btn');
    buttons.forEach(btn => {
        if (btn.dataset.format === format) {
            btn.className = "format-btn px-4 py-1.5 rounded-full text-sm font-medium transition-all bg-blue-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.4)]";
        } else {
            btn.className = "format-btn px-4 py-1.5 rounded-full text-sm font-medium transition-all bg-[#252527] text-gray-400 hover:text-white border border-[#333]";
        }
    });

    applyFilters();
}

function setDeviceFilter(mode) {
    currentFilter = mode;
    const btnK = document.getElementById('btnKindleFilter');
    const btnKO = document.getElementById('btnKOReaderFilter');
    const btnPDF = document.getElementById('filterBtnPDF');
    const btnCBZ = document.getElementById('filterBtnCBZ');

    const kPath = document.getElementById('detectedKindlePath').value;
    const koPath = document.getElementById('detectedKOReaderPath').value;
    const activePathInput = document.getElementById('kindlePath');

    const activeClasses = "px-4 py-1 rounded-full text-xs font-medium flex items-center gap-2 transition-all device-active";
    const inactiveClasses = "px-4 py-1 rounded-full text-xs font-medium flex items-center gap-2 transition-all device-inactive text-gray-500 hover:text-gray-300";

    if (mode === 'kindle') {
        btnK.className = activeClasses;
        btnKO.className = inactiveClasses;

        if (btnPDF) btnPDF.classList.add('hidden');
        if (btnCBZ) btnCBZ.classList.add('hidden');

        if (kPath) activePathInput.value = kPath;

        if (currentFormatFilter === '.pdf' || currentFormatFilter === '.cbz') {
            setFormatFilter('all');
        }
    } else {
        btnKO.className = activeClasses;
        btnK.className = inactiveClasses;

        if (btnPDF) btnPDF.classList.remove('hidden');
        if (btnCBZ) btnCBZ.classList.remove('hidden');

        if (koPath) activePathInput.value = koPath;
    }
    applyFilters();
}

function setViewMode(mode) {
    currentView = mode;
    const btnList = document.getElementById('btnListView');
    const btnGallery = document.getElementById('btnGalleryView');

    if (mode === 'list') {
        btnList.className = "p-1.5 rounded text-white bg-[#252527] border border-[#333] transition-colors";
        btnGallery.className = "p-1.5 rounded text-gray-500 hover:text-white transition-colors";
    } else {
        btnGallery.className = "p-1.5 rounded text-gray-400 hover:text-white bg-[#252527] border border-[#333] transition-colors";
        btnList.className = "p-1.5 rounded text-gray-500 hover:text-white transition-colors";
    }
    applyFilters();
}

function toggleMaintenanceMode() {
    maintenanceMode = !maintenanceMode;
    const btn = document.getElementById('btnMaintenance');
    const header = document.getElementById('mainHeader');

    if (maintenanceMode) {
        btn.classList.add('bg-orange-500/10', 'text-orange-400', 'border', 'border-orange-500/20');
        btn.classList.remove('text-gray-500', 'border-transparent');

        // Add header glow
        header.classList.add('border-b-2', 'border-orange-500', 'shadow-orange-500/10', 'bg-orange-900/10');
        header.classList.remove('border-darkborder');

        document.getElementById('editModeBanner').classList.remove('hidden');
        document.body.style.backgroundColor = '#1a1410';
    } else {
        btn.classList.remove('bg-orange-500/10', 'text-orange-400', 'border', 'border-orange-500/20');
        btn.classList.add('text-gray-500', 'border-transparent');

        // Remove header glow
        header.classList.remove('border-b-2', 'border-orange-500', 'shadow-orange-500/10', 'bg-orange-900/10');
        header.classList.add('border-darkborder');

        document.getElementById('editModeBanner').classList.add('hidden');
        document.body.style.backgroundColor = '';
    }
    updateActionBar();
    renderBooks();

    // Show/hide maintenance tools bar
    const toolsBar = document.getElementById('maintenanceTools');
    if (toolsBar) toolsBar.classList.toggle('hidden', !maintenanceMode);
}

// --- Card Context Menu ---
function toggleCardMenu(bookId, event) {
    event.stopPropagation();
    // Close all other menus first
    document.querySelectorAll('.card-context-menu').forEach(m => {
        if (m.id !== `card-menu-${bookId}`) m.classList.add('hidden');
    });
    const menu = document.getElementById(`card-menu-${bookId}`);
    if (menu) menu.classList.toggle('hidden');
}

// Close card menus on outside click
document.addEventListener('click', () => {
    document.querySelectorAll('.card-context-menu').forEach(m => m.classList.add('hidden'));
});

// --- Connection Logic ---
async function checkDeviceStatus(silent = false) {
    const statusDot = document.getElementById('usbStatusDot');
    const statusText = document.getElementById('usbStatusText');
    const badge = document.getElementById('usbStatusBadge');

    try {
        const res = await fetch('/api/v1/detect-device');
        const data = await res.json();

        if (badge) badge.classList.remove('hidden'); // Show badge once checked

        if (data.connected) {
            const wasAlreadyConnected = lastConnectedState;
            lastConnectedState = true;

            if (statusDot) {
                statusDot.classList.remove('bg-gray-500', 'animate-pulse', 'shadow-[0_0_8px_rgba(107,114,128,0.6)]');
                statusDot.classList.add('bg-green-500', 'shadow-[0_0_8px_rgba(34,197,94,0.6)]');
            }
            if (statusText) statusText.innerText = "KINDLE LOCAL";
            if (badge) badge.classList.add('border-green-500/30', 'bg-green-500/5');

            // If it wasn't connected before, prompt or assign paths
            if (!wasAlreadyConnected) {
                if (data.has_koreader) {
                    document.getElementById('detectedKOReaderPath').value = data.koreader_path;
                    document.getElementById('detectedKindlePath').value = data.kindle_path;
                    openModal('koreaderDetectModal');
                } else {
                    // If just a normal kindle, set the path automatically
                    document.getElementById('kindlePath').value = data.kindle_path;
                    setDeviceFilter('kindle');

                    // Apenas exibe a notificação de sincronizado se for a transição (não no carregamento inicial)
                    if (!silent) showToast("Dispositivo sincronizado!", "success");
                }
            }
        } else {
            lastConnectedState = false;

            if (statusDot) {
                statusDot.classList.remove('bg-green-500', 'shadow-[0_0_8px_rgba(34,197,94,0.6)]');
                statusDot.classList.add('bg-gray-500', 'animate-pulse', 'shadow-[0_0_8px_rgba(107,114,128,0.6)]');
            }
            if (statusText) statusText.innerText = "BUSCANDO USB";
            if (badge) badge.classList.remove('border-green-500/30', 'bg-green-500/5');
        }
        updateActionBar(); // Update button disabled state
    } catch (e) { console.log(e); }
}

function handleConnectionClick() {
    if (lastConnectedState) {
        showToast("Dispositivo conectado em: " + document.getElementById('kindlePath').value, "success");
    } else {
        openSettingsModal();
    }
}

// --- Modals & Popups ---
function openModal(id) {
    const m = document.getElementById(id);
    m.classList.remove('pointer-events-none', 'opacity-0');
    m.firstElementChild.nextElementSibling.classList.remove('scale-95');
}
function closeModal(id) {
    const m = document.getElementById(id);
    m.classList.add('pointer-events-none', 'opacity-0');
    m.firstElementChild.nextElementSibling.classList.add('scale-95');
}

function openSettingsModal() {
    // Load settings
    fetch('/api/v1/settings').then(r => r.json()).then(d => {
        document.getElementById('cfgBooksFolder').value = d.books_folder;
        document.getElementById('cfgScannerThreads').value = d.scanner_threads || 2;
    });
    openModal('settingsModal');
}
function closeSettingsModal() { closeModal('settingsModal'); }

function openEditModal(id, e) {
    if (e) e.stopPropagation();
    const book = allBooks.find(b => b.id === id);
    if (!book) return;

    document.getElementById('editBookId').value = book.id;
    document.getElementById('editTitle').value = book.title || '';
    document.getElementById('editAuthor').value = book.author || '';
    document.getElementById('editSeries').value = book.series || '';
    document.getElementById('editVolume').value = book.volume !== null ? book.volume : '';
    document.getElementById('editPublisher').value = book.publisher || '';
    document.getElementById('editPublishYear').value = book.publish_year || '';
    document.getElementById('editSynopsis').value = book.synopsis || '';
    document.getElementById('editCoverUrl').value = '';

    // Populate cover preview
    const coverPreview = document.getElementById('editCoverPreview');
    const coverPlaceholder = coverPreview.nextElementSibling;
    if (book.cover_path && book.cover_path.trim() !== '') {
        coverPreview.src = book.cover_path;
        coverPreview.style.display = '';
        coverPlaceholder.style.display = 'none';
    } else {
        coverPreview.src = '';
        coverPreview.style.display = 'none';
        coverPlaceholder.style.display = 'flex';
    }

    // Populate search input with title
    const searchInput = document.getElementById('editSearchQuery');
    if (searchInput) searchInput.value = book.title || '';

    // Reset tags
    const tagsContainer = document.getElementById('editTagsContainer');
    if (tagsContainer) tagsContainer.innerHTML = '';
    const tagsInput = document.getElementById('editTagsInput');
    if (tagsInput) tagsInput.value = '';

    // Populate tags if book has them
    if (book.tags && Array.isArray(book.tags)) {
        book.tags.forEach(tag => addTagChip(tag));
    }

    // Set language
    const langSelect = document.getElementById('editLanguage');
    if (langSelect) langSelect.value = book.language || '';

    // hide search results
    document.getElementById('metaSearchResults').innerHTML = '';
    document.getElementById('metaSearchResults').classList.add('hidden');

    openModal('editModal');
}
function closeEditModal() { closeModal('editModal'); }

let currentSearchMode = 'title';
function setSearchMode(mode) {
    currentSearchMode = mode;
    const btnISBN = document.getElementById('searchModeISBN');
    const btnTitle = document.getElementById('searchModeTitle');
    const searchLabel = document.querySelector('#editSearchQuery')?.previousElementSibling || document.querySelector('label[for=editSearchQuery]');

    const label = document.getElementById('searchLabel');
    if (mode === 'isbn') {
        btnISBN.className = "px-5 py-1.5 rounded-full text-xs font-medium transition-all bg-blue-600 text-white";
        btnTitle.className = "px-5 py-1.5 rounded-full text-xs font-medium transition-all text-gray-500 hover:text-gray-300";
        document.getElementById('editSearchQuery').placeholder = 'Ex: 9780804139021';
        if (label) label.textContent = 'Search by ISBN';
    } else {
        btnTitle.className = "px-5 py-1.5 rounded-full text-xs font-medium transition-all bg-blue-600 text-white";
        btnISBN.className = "px-5 py-1.5 rounded-full text-xs font-medium transition-all text-gray-500 hover:text-gray-300";
        document.getElementById('editSearchQuery').placeholder = 'Enter book title';
        if (label) label.textContent = 'Search by Title';
    }
}

let editTags = [];
function handleTagInput(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const input = event.target;
        const tag = input.value.trim();
        if (tag && !editTags.includes(tag)) {
            addTagChip(tag);
        }
        input.value = '';
    }
}

function addTagChip(tag) {
    editTags.push(tag);
    const container = document.getElementById('editTagsContainer');
    const chip = document.createElement('span');
    chip.className = "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-600/20 text-blue-400 border border-blue-500/30";
    chip.innerHTML = `${tag}<button onclick="removeTag('${tag}', this)" class="ml-0.5 text-blue-400 hover:text-white">&times;</button>`;
    container.appendChild(chip);
}

function removeTag(tag, btn) {
    editTags = editTags.filter(t => t !== tag);
    btn.parentElement.remove();
}

function handleCoverFileUpload(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (e) {
        const preview = document.getElementById('editCoverPreview');
        preview.src = e.target.result;
        preview.style.display = '';
        preview.nextElementSibling.style.display = 'none';
        // Store as data URL for upload
        document.getElementById('editCoverUrl').value = 'local:' + e.target.result;
    };
    reader.readAsDataURL(file);
}

function deleteCurrentBook() {
    const bookId = document.getElementById('editBookId').value;
    if (!bookId) return;
    closeEditModal();
    selectedIds.clear();
    selectedIds.add(parseInt(bookId));
    openDeleteModal();
}

function openDeleteModal() { openModal('deleteModal'); }
function closeDeleteModal() { closeModal('deleteModal'); }

function closeKOReaderDetectModal() { closeModal('koreaderDetectModal'); }

function selectAutoDetectMode(mode) {
    closeKOReaderDetectModal();
    setDeviceFilter(mode);
    if (mode === 'koreader') {
        const p = document.getElementById('detectedKOReaderPath').value;
        if (p) document.getElementById('kindlePath').value = p;
        showToast("Modo KOReader Ativado", "success");
    } else {
        showToast("Modo Kindle Nativo Ativado", "success");
    }
}

// --- API Actions ---

async function sendSelectedBatch() {
    if (!lastConnectedState) return showToast("No device connected.", "error");

    const btn = document.getElementById('btnActionBarSend');
    const originalText = btn.innerHTML;
    btn.disabled = true;

    const kindlePath = document.getElementById('kindlePath').value;
    const ids = Array.from(selectedIds);
    let success = 0;

    for (let i = 0; i < ids.length; i++) {
        const id = ids[i];
        try {
            btn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Enviando ${i + 1}/${ids.length}...`;
            btn.style.background = `linear-gradient(to right, #16a34a 0%, transparent 0%)`;

            const res = await fetch('/api/v1/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, kindle_path: kindlePath })
            });

            if (res.ok && res.body) {
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // Keep incomplete line

                    for (const line of lines) {
                        if (line.trim()) {
                            try {
                                const data = JSON.parse(line);
                                if (data.status === 'progress' || data.status === 'success') {
                                    const pct = data.progress || 0;
                                    btn.style.background = `linear-gradient(to right, #16a34a ${pct}%, #2a2a2a ${pct}%)`;
                                }
                            } catch (err) { }
                        }
                    }
                }
                success++;
            } else {
                throw new Error('Falha no envio');
            }
        } catch (e) {
            console.error(e);
        }
    }

    // Cleanup button style
    btn.style.background = '';
    btn.disabled = false;
    btn.innerHTML = originalText;

    if (success === ids.length) {
        showToast(`${success} books sent successfully!`, "success");
        clearSelection();
    } else {
        showToast(`Sent: ${success}. Errors: ${ids.length - success}`, "warning");
    }
}

async function sendToKindle(id, btn, e) {
    if (e) e.stopPropagation();
    selectedIds.clear();
    selectedIds.add(id);
    await sendSelectedBatch();
}

async function saveEditBook() {
    const id = document.getElementById('editBookId').value;
    const title = document.getElementById('editTitle').value;
    const author = document.getElementById('editAuthor').value;
    const series = document.getElementById('editSeries').value || null;
    const volumeStr = document.getElementById('editVolume').value;
    const volume = volumeStr ? parseFloat(volumeStr) : null;
    const publisher = document.getElementById('editPublisher').value || null;
    const publishYearStr = document.getElementById('editPublishYear').value;
    const publish_year = publishYearStr ? parseInt(publishYearStr) : null;
    const synopsis = document.getElementById('editSynopsis').value || null;
    const coverUrl = document.getElementById('editCoverUrl').value;

    const btn = document.getElementById('btnSaveEdit');
    btn.innerHTML = 'Salvando...';
    btn.disabled = true;

    try {
        // Update text metadata
        await fetch(`/api/v1/books/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title, author, series, volume, publisher, publish_year, synopsis
            })
        });

        // If a new cover was selected, download it
        if (coverUrl) {
            await fetch(`/api/v1/books/${id}/download-cover`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: coverUrl })
            });
        }

        closeEditModal();
        loadBooks();
        showToast("Book updated successfully.", "success");
    } catch (e) {
        showToast("Error saving", "error");
    } finally {
        btn.innerHTML = 'Save Changes';
        btn.disabled = false;
    }
}

async function searchMetadata() {
    const searchInput = document.getElementById('editSearchQuery');
    const q = searchInput ? searchInput.value.trim() : '';
    if (!q) return showToast("Digite um título antes.", "error");

    const btn = document.getElementById('btnSearchMeta');
    const originalIcon = btn.innerHTML;
    btn.innerHTML = '<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
    btn.disabled = true;

    const resultsContainer = document.getElementById('metaSearchResults');

    try {
        const res = await fetch(`/api/v1/metadata/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();

        if (data.status === 'error') {
            showToast(data.message || "Error returned by Google API.", "error");
        } else if (data.status === 'success' && data.results.length > 0) {
            resultsContainer.innerHTML = '';
            resultsContainer.classList.remove('hidden');

            data.results.forEach((r, idx) => {
                const safeCover = r.cover_url ? r.cover_url.replace(/'/g, "\\'") : '';
                const safeTitle = r.title ? r.title.replace(/'/g, "\\'") : '';
                const safeAuthor = r.author ? r.author.replace(/'/g, "\\'") : '';
                const safeSeries = r.series ? r.series.replace(/'/g, "\\'") : '';
                const safePub = r.publisher ? r.publisher.replace(/'/g, "\\'") : '';
                const safeSynop = r.synopsis ? encodeURIComponent(r.synopsis) : '';

                const row = document.createElement('div');
                row.className = "flex items-center gap-3 px-3 py-2.5 cursor-pointer hover:bg-[#252528] transition-colors border-b border-[#2a2a2a] last:border-b-0";
                row.onclick = () => applyMetadataResult(safeTitle, safeAuthor, r.publish_year || '', safePub, safeSynop, safeCover, row);

                const imgHtml = r.cover_url
                    ? `<img src="${r.cover_url}" class="w-8 h-12 object-cover rounded shadow-sm shrink-0">`
                    : `<div class="w-8 h-12 bg-[#252527] rounded shadow-sm flex items-center justify-center shrink-0"><svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg></div>`;

                row.innerHTML = `
                    ${imgHtml}
                    <div class="flex-1 min-w-0">
                        <h4 class="text-sm font-medium text-gray-200 truncate">${r.title}</h4>
                        <p class="text-xs text-gray-500 truncate">${r.author || 'Unknown'}</p>
                    </div>
                    <span class="text-[10px] text-gray-600 shrink-0">${r.source || 'Google Books'}</span>
                `;
                resultsContainer.appendChild(row);
            });

        } else {
            showToast("No results found in Google Books.", "warning");
        }
    } catch (e) {
        showToast("Metadata search error.", "error");
    } finally {
        btn.innerHTML = originalIcon;
        btn.disabled = false;
    }
}

function applyMetadataResult(title, author, year, publisher, encodedSynop, coverUrl, element) {
    if (title) document.getElementById('editTitle').value = title;
    if (author) document.getElementById('editAuthor').value = author;
    if (year) document.getElementById('editPublishYear').value = year;
    if (publisher) document.getElementById('editPublisher').value = publisher;
    if (encodedSynop) document.getElementById('editSynopsis').value = decodeURIComponent(encodedSynop);
    if (coverUrl) {
        document.getElementById('editCoverUrl').value = coverUrl;
        // Update cover preview
        const preview = document.getElementById('editCoverPreview');
        if (preview) {
            preview.src = coverUrl;
            preview.style.display = '';
            preview.nextElementSibling.style.display = 'none';
        }
    }

    // Visual feedback: highlight selected row
    const allItems = document.getElementById('metaSearchResults').children;
    for (let i = 0; i < allItems.length; i++) {
        allItems[i].classList.remove('bg-blue-600/10', 'ring-1', 'ring-blue-500/30');
    }
    element.classList.add('bg-blue-600/10', 'ring-1', 'ring-blue-500/30');
    showToast("Dados preenchidos! Clique em Save Changes.", "info");
}

async function confirmDeleteBatch() {
    const ids = Array.from(selectedIds);
    const permanent = document.getElementById('permanentDeleteCheck').checked;

    await fetch('/api/v1/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids, permanent })
    });

    closeDeleteModal();
    selectedIds.clear();
    updateActionBar();
    loadBooks();
    showToast("Books deleted.", "success");
}

async function saveSettings() {
    const folder = document.getElementById('cfgBooksFolder').value;
    const threads = document.getElementById('cfgScannerThreads').value;

    const btn = document.getElementById('btnSaveSettings');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="animate-pulse">Salvando...</span>';
    btn.disabled = true;

    try {
        await fetch('/api/v1/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ books_folder: folder, scanner_threads: parseInt(threads), rescan: false })
        });
        showToast("Configurações salvas!", "success");
        closeSettingsModal();
    } catch (e) {
        showToast("Erro ao salvar.", "error");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function rescanLibrary() {
    const folder = document.getElementById('cfgBooksFolder').value;
    const threads = document.getElementById('cfgScannerThreads').value;

    const btn = document.getElementById('btnRescan');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="animate-pulse">Enviando...</span>';
    btn.disabled = true;

    try {
        await fetch('/api/v1/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ books_folder: folder, scanner_threads: parseInt(threads), rescan: true })
        });
        closeSettingsModal();
        showToast("Escaneando biblioteca...", "info");
        // loadBooks will be automatically triggered later if SSE is configured
        // or we can call it manually, but starting a scan usually sends via SSE
    } catch (e) {
        showToast("Erro ao reenviar rescan.", "error");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// --- Web Folder Browser ---
let fbTargetInputId = null;
let fbCurrentParent = "";

function pickFolderFor(id) {
    fbTargetInputId = id;
    const currentVal = document.getElementById(id).value || "";
    document.getElementById('folderBrowserModal').classList.remove('hidden');
    document.getElementById('folderBrowserModal').classList.add('flex');
    loadFolderBrowser(currentVal);
}

function closeFolderBrowser() {
    document.getElementById('folderBrowserModal').classList.add('hidden');
    document.getElementById('folderBrowserModal').classList.remove('flex');
}

async function loadFolderBrowser(path) {
    const listEl = document.getElementById('fbList');
    const errEl = document.getElementById('fbError');
    const pathEl = document.getElementById('fbCurrentPath');
    const upBtn = document.getElementById('fbUpBtn');
    const extLoading = document.getElementById('fbLoading');

    errEl.classList.add('hidden');
    listEl.innerHTML = '';
    extLoading.classList.remove('hidden');

    try {
        const res = await fetch(`/api/v1/folders?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Erro ao carregar");

        fbCurrentParent = data.parent_path;
        pathEl.textContent = data.current_path || "Este Computador";

        upBtn.disabled = !data.parent_path && data.current_path !== "";
        if (data.current_path === "") upBtn.disabled = true;

        if (!data.folders || data.folders.length === 0) {
            listEl.innerHTML = '<div class="col-span-full text-center text-gray-500 py-4">Pasta vazia ou sem permissão de acesso.</div>';
        } else {
            data.folders.forEach(f => {
                const btn = document.createElement('button');
                btn.className = "flex items-center gap-3 p-3 w-full text-left bg-gray-50 dark:bg-darkcard hover:bg-gray-100 dark:hover:bg-darkbg border border-gray-200 dark:border-darkborder rounded-lg transition-colors group";
                btn.innerHTML = `
                    <svg class="w-6 h-6 text-kindle/70 group-hover:text-kindle flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path>
                    </svg>
                    <span class="truncate font-medium text-gray-700 dark:text-gray-200">${f.name}</span>
                `;
                btn.onclick = () => loadFolderBrowser(f.path);
                listEl.appendChild(btn);
            });
        }
    } catch (e) {
        errEl.textContent = e.message;
        errEl.classList.remove('hidden');
    } finally {
        extLoading.classList.add('hidden');
    }
}

function fbNavigateUp() {
    if (fbCurrentParent !== null) loadFolderBrowser(fbCurrentParent);
}

function fbConfirmSelection() {
    const path = document.getElementById('fbCurrentPath').textContent;
    if (path && path !== "Este Computador" && fbTargetInputId) {
        document.getElementById(fbTargetInputId).value = path;
        closeFolderBrowser();
    }
}

// --- Toast ---
let toastTimeout;
function showToast(msg, type = 'info', sticky = false) {
    const el = document.getElementById('toast');
    const icon = document.getElementById('toastIcon');
    document.getElementById('toastMsg').innerText = msg;

    clearTimeout(toastTimeout);

    el.className = `fixed top-24 left-1/2 -translate-x-1/2 transform transition-all duration-300 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl z-[70] pointer-events-none border backdrop-blur-md ${type === 'error' ? 'bg-red-900/80 border-red-500/50 text-red-100' :
        type === 'success' ? 'bg-green-900/80 border-green-500/50 text-green-100' :
            type === 'warning' ? 'bg-orange-900/80 border-orange-500/50 text-orange-100' : // updated warning colors to orange
                'bg-darkcard/90 border-darkborder text-gray-200'
        }`;

    icon.innerHTML = type === 'success' ?
        '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>' :
        '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';

    el.classList.remove('-translate-y-10', 'opacity-0');

    if (!sticky) {
        toastTimeout = setTimeout(() => {
            el.classList.add('-translate-y-10', 'opacity-0');
        }, 3000);
    }
}

// --- Zoom Logic ---
const ZOOM_LEVELS = [
    { gridW: "110px", listW: "30px", listTitle: "0.8rem", listAuthor: "0.65rem", markerPos: "0%", colsText: "9" },
    { gridW: "135px", listW: "40px", listTitle: "0.85rem", listAuthor: "0.75rem", markerPos: "25%", colsText: "7" },
    { gridW: "160px", listW: "50px", listTitle: "0.95rem", listAuthor: "0.8rem", markerPos: "50%", colsText: "6" }, // Default
    { gridW: "200px", listW: "65px", listTitle: "1.05rem", listAuthor: "0.9rem", markerPos: "75%", colsText: "5" },
    { gridW: "240px", listW: "85px", listTitle: "1.15rem", listAuthor: "1rem", markerPos: "100%", colsText: "4" }
];

function handleZoomSlider() {
    const val = parseInt(document.getElementById('zoomSlider').value);
    applyZoomLevel(val);
}

function adjustZoom(delta) {
    const slider = document.getElementById('zoomSlider');
    let val = parseInt(slider.value) + delta;
    if (val >= 0 && val < ZOOM_LEVELS.length) {
        slider.value = val;
        applyZoomLevel(val);
    }
}

function applyZoomLevel(index) {
    const z = ZOOM_LEVELS[index];
    const doc = document.documentElement;
    doc.style.setProperty('--grid-card-w', z.gridW);
    doc.style.setProperty('--list-cover-w', z.listW);
    doc.style.setProperty('--zoom-title-size', z.listTitle);
    const tooltip = document.getElementById('zoomValueText');
    if (tooltip) {
        tooltip.innerText = z.colsText;
        // Perfect pixel alignment for standard 16px range thumbs
        tooltip.style.left = `calc(${z.markerPos} + (${0.5 - (index / 4)} * 16px))`;
    }
}

// Initialize Zoom Default na montagem da tela
document.addEventListener('DOMContentLoaded', () => {
    applyZoomLevel(2);
    document.getElementById('zoomSlider').value = 2;
});


// --- Web Reader Logic (foliate-js) ---
function openReader(bookId, e) {
    if (e) e.stopPropagation();
    window.open(`/reader?id=${bookId}`, '_blank');
}

function updateReaderProgressBar() {
    if (!epubBook || !epubRendition || !epubBook.locations.length()) return;
    const currentLocation = epubRendition.currentLocation();
    if (currentLocation && currentLocation.start) {
        const percentage = epubBook.locations.percentageFromCfi(currentLocation.start.cfi);
        const pct = Math.round(percentage * 100);
        document.getElementById('readerProgressBar').style.width = pct + "%";
    }
}

function toggleReaderTheme() {
    readerDarkTheme = !readerDarkTheme;
    applyReaderTheme();
}

function applyReaderTheme() {
    if (!epubRendition) return;
    if (readerDarkTheme) {
        epubRendition.themes.register("dark", {
            "body": { "background": "#0f0f0f", "color": "#e5e7eb" },
            "a": { "color": "#00A8E1" }
        });
        epubRendition.themes.select("dark");
    } else {
        epubRendition.themes.register("light", {
            "body": { "background": "#ffffff", "color": "#1f2937" },
            "a": { "color": "#005a7a" }
        });
        epubRendition.themes.select("light");
    }
}

// --- Auto-Rename & Duplicates ---
async function autoRenameAll() {
    const btn = document.getElementById('btnAutoRename');
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-pulse">Renomeando...</span>';

    try {
        const res = await fetch('/api/v1/books/auto-rename', { method: 'POST' });
        const data = await res.json();

        let msg = `✅ ${data.renamed} renomeados, ${data.skipped} já corretos.`;
        if (data.errors.length > 0) {
            msg += ` ⚠️ ${data.errors.length} erro(s).`;
            console.warn('Rename errors:', data.errors);
        }
        showToast(msg, data.errors.length > 0 ? 'warning' : 'success');

        if (data.renamed > 0) loadBooks();
    } catch (e) {
        showToast('Error renaming: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

let dupDeleteSet = new Set();

async function scanDuplicates() {
    const btn = document.getElementById('btnDuplicates');
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-pulse">Scanning...</span>';

    try {
        const res = await fetch('/api/v1/books/duplicates');
        const data = await res.json();

        if (data.total_groups === 0) {
            showToast('No duplicates found! 🎉', 'success');
            return;
        }

        dupDeleteSet.clear();
        const list = document.getElementById('duplicatesList');
        list.innerHTML = '';

        let totalBooks = 0;
        data.groups.forEach(g => totalBooks += g.books.length);
        document.getElementById('dupSummary').textContent = `${data.total_groups} group(s), ${totalBooks} books`;

        data.groups.forEach((group, gi) => {
            const section = document.createElement('div');
            section.className = 'bg-[#1a1a1f] border border-darkborder rounded-xl p-4';

            const badge = group.reason === 'hash'
                ? '<span class="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded-full font-medium">Arquivo Idêntico</span>'
                : '<span class="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full font-medium">Metadados Similares</span>';

            const header = document.createElement('div');
            header.className = 'flex items-center gap-2 mb-3';
            header.innerHTML = `${badge} <span class="text-xs text-gray-500">${group.detail}</span>
                <button onclick="keepOnlyOne(${gi})" class="ml-auto text-[11px] text-green-400 hover:text-green-300 border border-green-500/20 hover:border-green-500/40 px-2 py-0.5 rounded-lg transition-all">✔ Keep 1st, delete rest</button>`;
            section.appendChild(header);

            const grid = document.createElement('div');
            grid.className = 'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3';
            grid.id = `dup-group-${gi}`;

            group.books.forEach((b, bi) => {
                const card = document.createElement('div');
                card.className = 'relative bg-[#121215] rounded-xl p-3 flex flex-col items-center text-center group cursor-pointer transition-all border-2 border-transparent hover:border-gray-600';
                card.id = `dup-card-${b.id}`;
                card.dataset.groupIndex = gi;
                card.dataset.bookIndex = bi;
                card.dataset.bookId = b.id;
                card.onclick = () => toggleDupSelect(b.id, card);

                card.innerHTML = `
                    <div class="absolute top-2 left-2 z-10">
                        <div class="w-5 h-5 rounded border-2 border-gray-600 flex items-center justify-center transition-all dup-check" id="dup-chk-${b.id}">
                        </div>
                    </div>
                    ${bi === 0 ? '<span class="absolute top-2 right-2 text-[9px] bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded font-medium">Original</span>' : ''}
                    ${b.cover_path
                        ? `<img src="${b.cover_path}" class="w-16 h-24 object-cover rounded-lg shadow-lg mb-2 pointer-events-none" onerror="this.style.display='none'">`
                        : `<div class="w-16 h-24 bg-darkborder rounded-lg mb-2 flex items-center justify-center pointer-events-none"><svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg></div>`
                    }
                    <div class="text-xs font-medium text-white truncate w-full pointer-events-none">${b.title}</div>
                    <div class="text-[10px] text-gray-400 truncate w-full pointer-events-none">${b.author}</div>
                    <span class="mt-1 text-[10px] px-1.5 py-0.5 rounded bg-darkborder text-gray-400 pointer-events-none">${b.file_type}</span>
                `;
                grid.appendChild(card);
            });

            section.appendChild(grid);
            list.appendChild(section);
        });

        // Store groups for keepOnlyOne
        window._dupGroups = data.groups;

        updateDupFooter();

        const modal = document.getElementById('duplicatesModal');
        modal.classList.remove('pointer-events-none', 'opacity-0');
        document.getElementById('duplicatesContent').classList.remove('scale-95');

    } catch (e) {
        showToast('Error searching duplicates: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

function toggleDupSelect(id, card) {
    if (dupDeleteSet.has(id)) {
        dupDeleteSet.delete(id);
        card.classList.remove('border-red-500', 'bg-red-500/5');
        card.classList.add('border-transparent');
        const chk = document.getElementById(`dup-chk-${id}`);
        chk.innerHTML = '';
        chk.classList.remove('bg-red-500', 'border-red-500');
        chk.classList.add('border-gray-600');
    } else {
        dupDeleteSet.add(id);
        card.classList.add('border-red-500', 'bg-red-500/5');
        card.classList.remove('border-transparent');
        const chk = document.getElementById(`dup-chk-${id}`);
        chk.innerHTML = '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';
        chk.classList.add('bg-red-500', 'border-red-500');
        chk.classList.remove('border-gray-600');
    }
    updateDupFooter();
}

function keepBestInAll() {
    if (!window._dupGroups) return;
    window._dupGroups.forEach((g, i) => keepOnlyOne(i));
}

function keepOnlyOne(groupIndex) {
    const group = window._dupGroups[groupIndex];
    if (!group) return;
    // Keep first, mark rest for deletion
    group.books.forEach((b, i) => {
        const card = document.getElementById(`dup-card-${b.id}`);
        if (!card) return;
        if (i === 0) {
            // Deselect the first one (keep it)
            dupDeleteSet.delete(b.id);
            card.classList.remove('border-red-500', 'bg-red-500/5');
            card.classList.add('border-green-500', 'bg-green-500/5');
            const chk = document.getElementById(`dup-chk-${b.id}`);
            chk.innerHTML = '';
            chk.classList.remove('bg-red-500', 'border-red-500');
            chk.classList.add('border-green-500');
        } else {
            // Select for deletion
            dupDeleteSet.add(b.id);
            card.classList.add('border-red-500', 'bg-red-500/5');
            card.classList.remove('border-transparent', 'border-green-500', 'bg-green-500/5');
            const chk = document.getElementById(`dup-chk-${b.id}`);
            chk.innerHTML = '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';
            chk.classList.add('bg-red-500', 'border-red-500');
            chk.classList.remove('border-gray-600', 'border-green-500');
        }
    });
    updateDupFooter();
}

function updateDupFooter() {
    const footer = document.getElementById('dupFooter');
    const count = dupDeleteSet.size;
    document.getElementById('dupSelectedCount').textContent = count;
    footer.classList.toggle('hidden', count === 0);
}

function closeDuplicatesModal() {
    const modal = document.getElementById('duplicatesModal');
    modal.classList.add('pointer-events-none', 'opacity-0');
    document.getElementById('duplicatesContent').classList.add('scale-95');
    dupDeleteSet.clear();
}

async function deleteSelectedDuplicates() {
    if (dupDeleteSet.size === 0) return;
    if (!confirm(`Delete ${dupDeleteSet.size} book(s)? Files will be moved to trash.`)) return;

    const btn = document.getElementById('btnDeleteSelectedDups');
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-pulse">Deleting...</span>';

    try {
        const res = await fetch('/api/v1/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: [...dupDeleteSet], permanent: false })
        });
        if (res.ok) {
            dupDeleteSet.forEach(id => {
                const card = document.getElementById(`dup-card-${id}`);
                if (card) { card.style.opacity = '0.2'; card.style.pointerEvents = 'none'; }
            });
            showToast(`${dupDeleteSet.size} duplicate(s) deleted!`, 'success');
            dupDeleteSet.clear();
            updateDupFooter();
            loadBooks();
        }
    } catch (e) {
        showToast('Erro: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg> Delete Marked';
    }
}


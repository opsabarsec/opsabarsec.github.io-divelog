const API_BASE_URL = 'http://localhost:8000';
let USER_NAME = 'Diver';
let USER_ID = 'default_user';

document.addEventListener('DOMContentLoaded', async () => {
    if (sessionStorage.getItem('authenticated') === 'true') {
        initApp();
    }
});

async function initApp() {
    document.getElementById('login-overlay').style.display = 'none';
    document.getElementById('main-app').style.display = 'block';
    await loadConfig();
    setupNavigation();
    await loadDiveStats();
    await loadLatestDive();
}

async function loadConfig() {
    try {
        const response = await fetch('config.json');
        if (response.ok) {
            const config = await response.json();
            USER_NAME = config.user_name || 'Diver';
            USER_ID = config.user_id || 'default_user';
            document.getElementById('user-name').textContent = USER_NAME;
        }
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

function setupNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
        });
    });
}

function switchView(viewId) {
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(`${viewId}-view`).classList.add('active');
    document.querySelector(`[data-view="${viewId}"]`).classList.add('active');

    if (viewId === 'home') loadLatestDive();
    if (viewId === 'dives') loadAllDives();
    if (viewId === 'certifications') loadCertifications();
}

// --- FISH IDENTIFICATION LOGIC ---

async function identifyFishFromInput() {
    const photoInput = document.getElementById('dive-photos');
    const resultsContainer = document.getElementById('fish-results');
    const notesField = document.getElementById('dive-notes');
    
    if (photoInput.files.length === 0) {
        showToast('Please select at least one photo first', 'error');
        return;
    }

    const file = photoInput.files[0]; // Analyze the first photo in the selection
    const formData = new FormData();
    formData.append('file', file);

    resultsContainer.innerHTML = '<span class="loading-inline">Analyzing with Fishial AI...</span>';

    try {
        const response = await fetch(`${API_BASE_URL}/identify-fish`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success && result.species && result.species.length > 0) {
            resultsContainer.innerHTML = '';
            let speciesNames = [];

            result.species.forEach(fish => {
                const badge = document.createElement('span');
                badge.className = 'fish-badge';
                const confidence = (fish.accuracy * 100).toFixed(0);
                badge.textContent = `${fish.name} (${confidence}%)`;
                resultsContainer.appendChild(badge);
                speciesNames.push(fish.name);
            });

            // Auto-append to notes
            const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            notesField.value += `\n[AI Sightings @ ${timestamp}: ${speciesNames.join(', ')}]`;
            showToast('Fish identified!');
        } else {
            resultsContainer.innerHTML = '<span>No fish recognized in this photo.</span>';
        }
    } catch (error) {
        console.error('Fish ID Error:', error);
        resultsContainer.innerHTML = '<span>Error connecting to AI service.</span>';
    }
}

// --- DIVE MANAGEMENT ---

async function handleDiveSubmit(event) {
    event.preventDefault();
    const photoInput = document.getElementById('dive-photos');
    let photoStorageIds = [];

    // 1. Upload Photos first if any
    if (photoInput.files.length > 0) {
        const formData = new FormData();
        for (let i = 0; i < photoInput.files.length; i++) {
            formData.append('files', photoInput.files[i]);
        }

        try {
            const uploadRes = await fetch(`${API_BASE_URL}/upload-photos`, {
                method: 'POST',
                body: formData
            });
            const uploadData = await uploadRes.json();
            photoStorageIds = uploadData.photo_storage_ids;
        } catch (error) {
            console.error('Photo upload failed:', error);
            showToast('Photo upload failed, saving dive without photos', 'error');
        }
    }

    // 2. Prepare Dive Data
    const diveData = {
        user_id: USER_ID,
        dive_number: parseInt(document.getElementById('dive-number').value),
        dive_date: new Date(document.getElementById('dive-date').value).getTime(),
        location: document.getElementById('dive-location').value,
        site: document.getElementById('dive-site').value,
        max_depth: parseFloat(document.getElementById('dive-depth').value),
        duration: parseFloat(document.getElementById('dive-duration').value),
        club_name: document.getElementById('dive-club').value,
        instructor_name: document.getElementById('dive-instructor').value,
        notes: document.getElementById('dive-notes').value,
        photo_storage_ids: photoStorageIds
    };

    // 3. Save to Backend
    try {
        const response = await fetch(`${API_BASE_URL}/dives`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(diveData)
        });

        if (response.ok) {
            showToast('Dive log saved!');
            closeDiveModal();
            loadDiveStats();
            loadLatestDive();
        }
    } catch (error) {
        showToast('Error saving dive', 'error');
    }
}

function renderDiveCard(dive) {
    const date = new Date(dive.dive_date).toLocaleDateString();
    
    // Create photo HTML if IDs exist
    let photosHtml = '';
    if (dive.photo_storage_ids && dive.photo_storage_ids.length > 0) {
        photosHtml = `<div class="dive-card-photos">
            ${dive.photo_storage_ids.map(id => `
                <img src="${API_BASE_URL}/download-photo/${id}" class="dive-photo" alt="Dive Photo" onclick="window.open(this.src)">
            `).join('')}
        </div>`;
    }

    return `
        <div class="dive-card">
            <div class="dive-card-header">
                <div class="dive-info">
                    <div class="dive-number">DIVE #${dive.dive_number}</div>
                    <div class="dive-location">${dive.location}</div>
                    <div class="dive-site">${dive.site || 'Unnamed Site'}</div>
                </div>
                <div class="dive-date">${date}</div>
            </div>
            
            <div class="dive-card-stats">
                <div class="stat-item">
                    <div class="stat-value">${dive.max_depth}m</div>
                    <div class="stat-label">Depth</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${dive.duration}</div>
                    <div class="stat-label">Min</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">--</div>
                    <div class="stat-label">Temp</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">--</div>
                    <div class="stat-label">Bar</div>
                </div>
            </div>

            ${photosHtml}

            <div class="dive-card-details">
                <div class="detail-item">
                    <span class="detail-label">Dive Club</span>
                    <span class="detail-value">${dive.club_name || 'Personal'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Instructor/Buddy</span>
                    <span class="detail-value">${dive.instructor_name || 'N/A'}</span>
                </div>
            </div>

            <div class="dive-card-notes">
                <p class="notes-text">${dive.notes || 'No notes added.'}</p>
            </div>

            <div class="dive-card-actions">
                <button class="btn-icon danger" onclick="confirmDeleteDive('${dive._id}')">🗑️</button>
            </div>
        </div>
    `;
}

// --- UI HELPERS ---

function openDiveModal() {
    document.getElementById('dive-form').reset();
    document.getElementById('fish-results').innerHTML = '';
    document.getElementById('dive-modal').classList.add('active');
}

function closeDiveModal() {
    document.getElementById('dive-modal').classList.remove('active');
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// --- AUTH ---

async function handleLogin(event) {
    event.preventDefault();
    const password = document.getElementById('password-input').value;

    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });

        if (response.ok) {
            sessionStorage.setItem('authenticated', 'true');
            initApp();
        } else {
            showToast('Invalid Password', 'error');
        }
    } catch (e) {
        showToast('Server connection failed', 'error');
    }
}

// Remaining generic functions (loadLatestDive, loadAllDives, etc.) 
// follow the same pattern as renderDiveCard.
async function loadLatestDive() {
    const container = document.getElementById('latest-dive-container');
    try {
        const response = await fetch(`${API_BASE_URL}/dives?user_id=${USER_ID}`);
        const dives = await response.json();
        if (dives.length > 0) {
            const latest = dives.sort((a, b) => b.dive_number - a.dive_number)[0];
            container.innerHTML = renderDiveCard(latest);
        } else {
            container.innerHTML = '<div class="empty-state">No dives logged yet.</div>';
        }
    } catch (e) {
        container.innerHTML = 'Error loading dive.';
    }
}

async function loadAllDives() {
    const grid = document.getElementById('dives-grid');
    try {
        const response = await fetch(`${API_BASE_URL}/dives?user_id=${USER_ID}`);
        const dives = await response.json();
        grid.innerHTML = dives.map(d => renderDiveCard(d)).join('');
    } catch (e) {
        grid.innerHTML = 'Error loading dives.';
    }
}

async function loadDiveStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/dives?user_id=${USER_ID}`);
        if (response.ok) {
            const dives = await response.json();
            document.getElementById('total-dives').textContent = `${dives.length} dives`;
        }
    } catch (e) {}
}

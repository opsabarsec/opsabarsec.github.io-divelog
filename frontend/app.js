const API_BASE_URL = 'http://localhost:8000';
let USER_NAME = 'Diver';
let USER_ID = 'default_user';

document.addEventListener('DOMContentLoaded', async () => {
    // Check if user is already authenticated
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

// Load dive statistics for profile section
async function loadDiveStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/dives?user_id=${USER_ID}`);
        if (response.ok) {
            const dives = await response.json();
            const totalDives = dives.length;
            document.getElementById('total-dives').textContent = `${totalDives} dive${totalDives !== 1 ? 's' : ''}`;
        }
    } catch (error) {
        console.error('Failed to load dive stats:', error);
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const password = document.getElementById('password-input').value;

    try {
        // You need to implement this endpoint on your server
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });

        if (response.ok) {
            sessionStorage.setItem('authenticated', 'true');
            initApp();
        } else {
            alert('Invalid password');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Could not connect to server.');
    }
}

// Load configuration from backend
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/config`);
        if (response.ok) {
            const config = await response.json();
            USER_NAME = config.name_surname || 'Diver';
            USER_ID = USER_NAME.toLowerCase().replace(/\s+/g, '_');
            document.getElementById('user-name').textContent = USER_NAME;
            document.getElementById('profile-name').textContent = USER_NAME;
            document.title = `Divelog ${USER_NAME}`;

            // Load profile photo
            if (config.profile_photo) {
                document.getElementById('profile-photo').src = `${API_BASE_URL}/profile-photo`;
            }
        }
    } catch (error) {
        console.error('Failed to load config:', error);
        document.getElementById('user-name').textContent = USER_NAME;
    }
}

// Navigation
function setupNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
        });
    });
}

function switchView(viewName) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    // Update views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`${viewName}-view`).classList.add('active');

    // Load data for the view
    if (viewName === 'home') {
        loadLatestDive();
    } else if (viewName === 'dives') {
        loadAllDives();
    } else if (viewName === 'certifications') {
        loadCertifications();
    }
}

// Format date
function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Format date for input
function formatDateForInput(timestamp) {
    const date = new Date(timestamp);
    return date.toISOString().split('T')[0];
}

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// =====================
// LATEST DIVE
// =====================

async function loadLatestDive() {
    const container = document.getElementById('latest-dive-container');
    container.innerHTML = '<div class="loading">Loading latest dive...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/dives/latest?user_id=${USER_ID}`);

        if (response.status === 404) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No dives logged yet</h3>
                    <p>Start by logging your first dive!</p>
                </div>
            `;
            return;
        }

        if (!response.ok) throw new Error('Failed to load dive');

        const dive = await response.json();
        container.innerHTML = renderDiveCard(dive, true);
    } catch (error) {
        console.error('Error loading latest dive:', error);
        container.innerHTML = `
            <div class="empty-state">
                <h3>Could not load dive</h3>
                <p>Make sure the backend server is running on port 8000</p>
            </div>
        `;
    }
}

function renderDiveCard(dive, showActions = true) {
    const photoHtml = dive.photo_storage_ids && dive.photo_storage_ids.length > 0
        ? `<div class="dive-card-photos">
            ${dive.photo_storage_ids.map(id =>
                `<img src="${API_BASE_URL}/download-photo/${id}" alt="Dive photo" class="dive-photo" onerror="this.style.display='none'">`
            ).join('')}
           </div>`
        : '';

    const osmLinkHtml = dive.osm_link
        ? `<a href="${dive.osm_link}" target="_blank" class="osm-link">View on Map</a>`
        : '';

    const actionsHtml = showActions
        ? `<div class="dive-card-actions">
            <button class="btn btn-secondary btn-sm" onclick="editDive('${dive._id}')">Edit</button>
            <button class="btn btn-danger btn-sm" onclick="confirmDeleteDive('${dive._id}')">Delete</button>
           </div>`
        : '';

    return `
        <div class="dive-card">
            <div class="dive-card-header">
                <div class="dive-info">
                    <div class="dive-number">Dive #${dive.dive_number}</div>
                    <div class="dive-location">${dive.location}</div>
                    ${dive.site ? `<div class="dive-site">${dive.site}</div>` : ''}
                    ${osmLinkHtml}
                </div>
                <div class="dive-date">${formatDate(dive.dive_date)}</div>
            </div>

            <div class="dive-card-stats">
                <div class="stat-item">
                    <div class="stat-value">${dive.max_depth}m</div>
                    <div class="stat-label">Max Depth</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${dive.duration}min</div>
                    <div class="stat-label">Duration</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${dive.temperature ? dive.temperature + 'C' : '-'}</div>
                    <div class="stat-label">Temp</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${dive.visibility ? dive.visibility + 'm' : '-'}</div>
                    <div class="stat-label">Visibility</div>
                </div>
            </div>

            ${photoHtml}

            <div class="dive-card-details">
                <div class="detail-item">
                    <span class="detail-label">Club</span>
                    <span class="detail-value">${dive.club_name}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Instructor</span>
                    <span class="detail-value">${dive.instructor_name}</span>
                </div>
                ${dive.weather ? `
                <div class="detail-item">
                    <span class="detail-label">Weather</span>
                    <span class="detail-value">${dive.weather}</span>
                </div>` : ''}
                ${dive.suit_thickness ? `
                <div class="detail-item">
                    <span class="detail-label">Suit</span>
                    <span class="detail-value">${dive.suit_thickness}mm</span>
                </div>` : ''}
                ${dive.lead_weights ? `
                <div class="detail-item">
                    <span class="detail-label">Weights</span>
                    <span class="detail-value">${dive.lead_weights}kg</span>
                </div>` : ''}
            </div>

            ${dive.notes ? `
            <div class="dive-card-notes">
                <div class="notes-text">${dive.notes}</div>
            </div>` : ''}

            ${actionsHtml}
        </div>
    `;
}

// =====================
// ALL DIVES
// =====================

async function loadAllDives() {
    const container = document.getElementById('dives-list');
    container.innerHTML = '<div class="loading">Loading dives...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/dives?user_id=${USER_ID}`);
        if (!response.ok) throw new Error('Failed to load dives');

        const dives = await response.json();

        if (dives.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No dives logged yet</h3>
                    <p>Start by logging your first dive!</p>
                    <button class="btn btn-primary" onclick="showAddDiveModal()">Log New Dive</button>
                </div>
            `;
            return;
        }

        container.innerHTML = dives.map(dive => renderDiveMiniCard(dive)).join('');
    } catch (error) {
        console.error('Error loading dives:', error);
        container.innerHTML = `
            <div class="empty-state">
                <h3>Could not load dives</h3>
                <p>Make sure the backend server is running</p>
            </div>
        `;
    }
}

function renderDiveMiniCard(dive) {
    return `
        <div class="dive-card-mini">
            <div class="dive-card-mini-header">
                <div>
                    <div class="dive-number">Dive #${dive.dive_number}</div>
                    <div class="dive-location">${dive.location}</div>
                    ${dive.site ? `<div class="dive-site">${dive.site}</div>` : ''}
                </div>
                <div class="dive-date">${formatDate(dive.dive_date)}</div>
            </div>

            <div class="dive-card-mini-stats">
                <div class="mini-stat">
                    <span class="mini-stat-value">${dive.max_depth}m</span>
                    <span class="mini-stat-label">Depth</span>
                </div>
                <div class="mini-stat">
                    <span class="mini-stat-value">${dive.duration}min</span>
                    <span class="mini-stat-label">Duration</span>
                </div>
                ${dive.temperature ? `
                <div class="mini-stat">
                    <span class="mini-stat-value">${dive.temperature}C</span>
                    <span class="mini-stat-label">Temp</span>
                </div>` : ''}
            </div>

            <div class="dive-card-mini-footer">
                <span style="color: var(--text-muted); font-size: 0.85rem;">${dive.club_name}</span>
                <div>
                    <button class="btn-icon" onclick="editDive('${dive._id}')" title="Edit">&#9998;</button>
                    <button class="btn-icon danger" onclick="confirmDeleteDive('${dive._id}')" title="Delete">&#128465;</button>
                </div>
            </div>
        </div>
    `;
}

// =====================
// CERTIFICATIONS
// =====================

async function loadCertifications() {
    const container = document.getElementById('certifications-list');
    container.innerHTML = '<div class="loading">Loading certifications...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/certifications?user_id=${USER_ID}`);
        if (!response.ok) throw new Error('Failed to load certifications');

        const certs = await response.json();

        if (certs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No certifications added yet</h3>
                    <p>Add your diving certifications to keep track of your progress!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = certs.map(cert => renderCertCard(cert)).join('');
    } catch (error) {
        console.error('Error loading certifications:', error);
        container.innerHTML = `
            <div class="empty-state">
                <h3>Could not load certifications</h3>
                <p>Make sure the backend server is running</p>
            </div>
        `;
    }
}

function renderCertCard(cert) {
    return `
        <div class="cert-card">
            <span class="cert-agency">${cert.agency}</span>
            <h3 class="cert-name">${cert.name}</h3>

            <div class="cert-details">
                <div class="cert-detail">
                    <span class="cert-detail-label">Date</span>
                    <span class="cert-detail-value">${formatDate(cert.certification_date)}</span>
                </div>
                ${cert.certification_number ? `
                <div class="cert-detail">
                    <span class="cert-detail-label">Number</span>
                    <span class="cert-detail-value">${cert.certification_number}</span>
                </div>` : ''}
                ${cert.instructor_name ? `
                <div class="cert-detail">
                    <span class="cert-detail-label">Instructor</span>
                    <span class="cert-detail-value">${cert.instructor_name}</span>
                </div>` : ''}
                ${cert.dive_center ? `
                <div class="cert-detail">
                    <span class="cert-detail-label">Dive Center</span>
                    <span class="cert-detail-value">${cert.dive_center}</span>
                </div>` : ''}
            </div>

            <div class="cert-actions">
                <button class="btn-icon danger" onclick="confirmDeleteCert('${cert._id}')" title="Delete">&#128465;</button>
            </div>
        </div>
    `;
}

// =====================
// DIVE MODAL
// =====================

let currentEditDiveId = null;

function showAddDiveModal() {
    currentEditDiveId = null;
    document.getElementById('dive-modal-title').textContent = 'Log New Dive';
    document.getElementById('dive-submit-btn').textContent = 'Save Dive';
    document.getElementById('dive-form').reset();
    document.getElementById('dive-id').value = '';
    document.getElementById('dive-buddy-check').checked = true;
    document.getElementById('dive-briefed').checked = true;
    document.getElementById('dive-modal').classList.add('active');
}

async function editDive(diveId) {
    currentEditDiveId = diveId;
    document.getElementById('dive-modal-title').textContent = 'Edit Dive';
    document.getElementById('dive-submit-btn').textContent = 'Update Dive';

    try {
        const response = await fetch(`${API_BASE_URL}/dives/${diveId}`);
        if (!response.ok) throw new Error('Failed to load dive');

        const dive = await response.json();

        document.getElementById('dive-id').value = dive._id;
        document.getElementById('dive-number').value = dive.dive_number;
        document.getElementById('dive-date').value = formatDateForInput(dive.dive_date);
        document.getElementById('dive-location').value = dive.location;
        document.getElementById('dive-site').value = dive.site || '';
        document.getElementById('dive-duration').value = dive.duration;
        document.getElementById('dive-max-depth').value = dive.max_depth;
        document.getElementById('dive-temperature').value = dive.temperature || '';
        document.getElementById('dive-visibility').value = dive.visibility || '';
        document.getElementById('dive-weather').value = dive.weather || '';
        document.getElementById('dive-suit').value = dive.suit_thickness || '';
        document.getElementById('dive-weights').value = dive.lead_weights || '';
        document.getElementById('dive-club').value = dive.club_name;
        document.getElementById('dive-instructor').value = dive.instructor_name;
        document.getElementById('dive-notes').value = dive.notes || '';
        document.getElementById('dive-buddy-check').checked = dive.Buddy_check;
        document.getElementById('dive-briefed').checked = dive.Briefed;

        document.getElementById('dive-modal').classList.add('active');
    } catch (error) {
        console.error('Error loading dive:', error);
        showToast('Failed to load dive data', 'error');
    }
}

function closeDiveModal() {
    document.getElementById('dive-modal').classList.remove('active');
    document.getElementById('dive-form').reset();
    currentEditDiveId = null;
}

async function submitDive(event) {
    event.preventDefault();

    const submitBtn = document.getElementById('dive-submit-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';

    try {
        // Upload photos first if any
        const photoInput = document.getElementById('dive-photos');
        let photoStorageIds = [];

        if (photoInput.files.length > 0) {
            const formData = new FormData();
            for (const file of photoInput.files) {
                formData.append('files', file);
            }

            const uploadResponse = await fetch(`${API_BASE_URL}/upload-photos`, {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('Failed to upload photos');
            }

            const uploadResult = await uploadResponse.json();
            photoStorageIds = uploadResult.photo_storage_ids;
        }

        // Build dive data
        const diveDate = new Date(document.getElementById('dive-date').value);
        const diveData = {
            user_id: USER_ID,
            dive_number: parseInt(document.getElementById('dive-number').value),
            dive_date: diveDate.getTime(),
            location: document.getElementById('dive-location').value,
            duration: parseFloat(document.getElementById('dive-duration').value),
            max_depth: parseFloat(document.getElementById('dive-max-depth').value),
            club_name: document.getElementById('dive-club').value,
            instructor_name: document.getElementById('dive-instructor').value,
            photo_storage_ids: photoStorageIds,
            buddy_check: document.getElementById('dive-buddy-check').checked,
            briefed: document.getElementById('dive-briefed').checked
        };

        // Optional fields
        const site = document.getElementById('dive-site').value;
        if (site) diveData.site = site;

        const temp = document.getElementById('dive-temperature').value;
        if (temp) diveData.temperature = parseFloat(temp);

        const vis = document.getElementById('dive-visibility').value;
        if (vis) diveData.visibility = parseFloat(vis);

        const weather = document.getElementById('dive-weather').value;
        if (weather) diveData.weather = weather;

        const suit = document.getElementById('dive-suit').value;
        if (suit) diveData.suit_thickness = parseFloat(suit);

        const weights = document.getElementById('dive-weights').value;
        if (weights) diveData.lead_weights = parseFloat(weights);

        const notes = document.getElementById('dive-notes').value;
        if (notes) diveData.notes = notes;

        // Submit to API
        const response = await fetch(`${API_BASE_URL}/dives/upsert`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(diveData)
        });

        if (!response.ok) {
            throw new Error('Failed to save dive');
        }

        const result = await response.json();
        showToast(`Dive ${result.action === 'inserted' ? 'logged' : 'updated'} successfully!`);
        closeDiveModal();

        // Refresh the current view
        const activeView = document.querySelector('.nav-btn.active').dataset.view;
        if (activeView === 'home') {
            loadLatestDive();
        } else if (activeView === 'dives') {
            loadAllDives();
        }
    } catch (error) {
        console.error('Error saving dive:', error);
        showToast('Failed to save dive', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = currentEditDiveId ? 'Update Dive' : 'Save Dive';
    }
}

// =====================
// CERTIFICATION MODAL
// =====================

function showAddCertModal() {
    document.getElementById('cert-form').reset();
    document.getElementById('cert-modal').classList.add('active');
}

function closeCertModal() {
    document.getElementById('cert-modal').classList.remove('active');
    document.getElementById('cert-form').reset();
}

async function submitCertification(event) {
    event.preventDefault();

    const certDate = new Date(document.getElementById('cert-date').value);
    const certData = {
        user_id: USER_ID,
        name: document.getElementById('cert-name').value,
        agency: document.getElementById('cert-agency').value,
        certification_date: certDate.getTime()
    };

    // Optional fields
    const certNumber = document.getElementById('cert-number').value;
    if (certNumber) certData.certification_number = certNumber;

    const instructor = document.getElementById('cert-instructor').value;
    if (instructor) certData.instructor_name = instructor;

    const center = document.getElementById('cert-center').value;
    if (center) certData.dive_center = center;

    try {
        const response = await fetch(`${API_BASE_URL}/certifications`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(certData)
        });

        if (!response.ok) {
            throw new Error('Failed to save certification');
        }

        showToast('Certification added successfully!');
        closeCertModal();
        loadCertifications();
    } catch (error) {
        console.error('Error saving certification:', error);
        showToast('Failed to save certification', 'error');
    }
}

// =====================
// DELETE CONFIRMATION
// =====================

let deleteCallback = null;

function confirmDeleteDive(diveId) {
    document.getElementById('confirm-message').textContent = 'Are you sure you want to delete this dive? This action cannot be undone.';
    document.getElementById('confirm-delete-btn').onclick = () => deleteDive(diveId);
    document.getElementById('confirm-modal').classList.add('active');
}

function confirmDeleteCert(certId) {
    document.getElementById('confirm-message').textContent = 'Are you sure you want to delete this certification?';
    document.getElementById('confirm-delete-btn').onclick = () => deleteCertification(certId);
    document.getElementById('confirm-modal').classList.add('active');
}

function closeConfirmModal() {
    document.getElementById('confirm-modal').classList.remove('active');
}

async function deleteDive(diveId) {
    try {
        const response = await fetch(`${API_BASE_URL}/dives/${diveId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete dive');
        }

        showToast('Dive deleted successfully');
        closeConfirmModal();

        // Refresh the current view
        const activeView = document.querySelector('.nav-btn.active').dataset.view;
        if (activeView === 'home') {
            loadLatestDive();
        } else if (activeView === 'dives') {
            loadAllDives();
        }
    } catch (error) {
        console.error('Error deleting dive:', error);
        showToast('Failed to delete dive', 'error');
    }
}

async function deleteCertification(certId) {
    try {
        const response = await fetch(`${API_BASE_URL}/certifications/${certId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete certification');
        }

        showToast('Certification deleted successfully');
        closeConfirmModal();
        loadCertifications();
    } catch (error) {
        console.error('Error deleting certification:', error);
        showToast('Failed to delete certification', 'error');
    }
}

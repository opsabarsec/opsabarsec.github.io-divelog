// ✅ Final production API URLs (your deployment)
const VERCEL_BASE = "https://opsabarsec-github-io-divelog.vercel.app";

// All endpoints are served from the root by api/main.py
const DIVES_API = VERCEL_BASE;
const CERTS_API = VERCEL_BASE;

let USER_NAME = 'Diver';
let USER_ID = 'default_user';

// Restore session if returning user
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

/* -------------------------------------------------
   LOGIN
--------------------------------------------------*/
async function handleLogin(event) {
  event.preventDefault();
  const password = document.getElementById('password-input').value;

  try {
    const response = await fetch(`${DIVES_API}/login`, {
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

/* -------------------------------------------------
   CONFIG
--------------------------------------------------*/
async function loadConfig() {
  try {
    const response = await fetch(`${DIVES_API}/config`);
    if (response.ok) {
      const config = await response.json();
      USER_NAME = config.name_surname ?? 'Diver';
      USER_ID = USER_NAME.toLowerCase().replace(/\s+/g, '_');

      document.getElementById('user-name').textContent = USER_NAME;
      document.getElementById('profile-name').textContent = USER_NAME;
      document.title = `Divelog ${USER_NAME}`;

    }
  } catch (error) {
    console.error('Failed to load config:', error);
  }
}

/* -------------------------------------------------
   DIVE STATS
--------------------------------------------------*/
async function loadDiveStats() {
  try {
    const response = await fetch(`${DIVES_API}/dives?user_id=${USER_ID}`);
    if (response.ok) {
      const dives = await response.json();
      const total = dives.length;
      document.getElementById('total-dives').textContent =
        `${total} dive${total !== 1 ? 's' : ''}`;
    }
  } catch (error) {
    console.error('Failed to load dive stats:', error);
  }
}

/* -------------------------------------------------
   LATEST DIVE
--------------------------------------------------*/
async function loadLatestDive() {
  const container = document.getElementById('latest-dive-container');
  container.innerHTML = '<div class="loading">Loading latest dive...</div>';

  try {
    const response = await fetch(`${DIVES_API}/dives/latest?user_id=${USER_ID}`);

    if (response.status === 404) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No dives logged yet</h3>
          <p>Start by logging your first dive!</p>
        </div>`;
      return;
    }

    if (!response.ok) throw new Error();
    const dive = await response.json();
    container.innerHTML = renderDiveCard(dive, true);

  } catch (error) {
    container.innerHTML = `
      <div class="empty-state">
        <h3>Could not load dive</h3>
        <p>Backend might be unavailable</p>
      </div>`;
  }
}

/* -------------------------------------------------
   RENDER DIVE CARD
--------------------------------------------------*/
function renderDiveCard(dive, showActions = true) {
  const photoHtml = dive.photo_storage_ids && dive.photo_storage_ids.length > 0
    ? `<div class="dive-card-photos">
        ${dive.photo_storage_ids.map(id =>
          `<img src="${DIVES_API}/download-photo/${id}" alt="Dive photo" class="dive-photo" onerror="this.style.display='none'">`
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
        <div class="stat-item"><div class="stat-value">${dive.max_depth}m</div><div class="stat-label">Max Depth</div></div>
        <div class="stat-item"><div class="stat-value">${dive.duration}min</div><div class="stat-label">Duration</div></div>
        <div class="stat-item"><div class="stat-value">${dive.temperature ?? '-'}°C</div><div class="stat-label">Temp</div></div>
        <div class="stat-item"><div class="stat-value">${dive.suit_thickness != null ? dive.suit_thickness + 'mm' : '-'}</div><div class="stat-label">Suit</div></div>
      </div>

      ${photoHtml}

      <div class="dive-card-details">
        <div class="detail-item"><span class="detail-label">Club</span><span class="detail-value">${dive.club_name}</span></div>
        <div class="detail-item"><span class="detail-label">Instructor</span><span class="detail-value">${dive.instructor_name}</span></div>
        <div class="detail-item"><span class="detail-label">Weights</span><span class="detail-value">${dive.lead_weights != null ? dive.lead_weights + ' kg' : '-'}</span></div>
      </div>

      ${dive.notes ? `<div class="dive-card-notes"><div class="notes-label" style="font-size:0.8rem;color:var(--text-muted);margin-bottom:5px;">Comments</div><div class="notes-text">${dive.notes}</div></div>` : ''}

      ${actionsHtml}
    </div>
  `;
}

/* -------------------------------------------------
   ALL DIVES
--------------------------------------------------*/
async function loadAllDives() {
  const container = document.getElementById('dives-list');
  container.innerHTML = '<div class="loading">Loading dives...</div>';

  try {
    const response = await fetch(`${DIVES_API}/dives?user_id=${USER_ID}`);
    if (!response.ok) throw new Error();

    const dives = await response.json();
    if (dives.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No dives logged yet</h3>
          <button class="btn btn-primary" onclick="showAddDiveModal()">Log New Dive</button>
        </div>`;
      return;
    }

    container.innerHTML = dives.map(d => renderDiveMiniCard(d)).join('');

  } catch (error) {
    container.innerHTML = `
      <div class="empty-state">
        <h3>Error loading dives</h3>
        <p>Backend unreachable.</p>
      </div>`;
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
        <div class="mini-stat"><span class="mini-stat-value">${dive.max_depth}m</span><span class="mini-stat-label">Depth</span></div>
        <div class="mini-stat"><span class="mini-stat-value">${dive.duration}min</span><span class="mini-stat-label">Duration</span></div>
      </div>

      <div class="dive-card-mini-footer">
        <span style="color: var(--text-muted); font-size: 0.85rem;">${dive.club_name}</span>
        <div>
          <button class="btn-icon" onclick="editDive('${dive._id}')" title="Edit">✎</button>
          <button class="btn-icon danger" onclick="confirmDeleteDive('${dive._id}')" title="Delete">🗑</button>
        </div>
      </div>
    </div>
  `;
}

/* -------------------------------------------------
   CERTIFICATIONS
--------------------------------------------------*/
async function loadCertifications() {
  const container = document.getElementById('certifications-list');
  container.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const response = await fetch(`${CERTS_API}/certifications?user_id=${USER_ID}`);
    if (!response.ok) throw new Error();

    const certs = await response.json();

    if (certs.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No certifications</h3>
        </div>`;
      return;
    }

    container.innerHTML = certs.map(renderCertCard).join('');

  } catch (error) {
    console.error(error);
    container.innerHTML = '<div>Error loading certifications</div>';
  }
}

function renderCertCard(cert) {
  return `
    <div class="cert-card">
      <span class="cert-agency">${cert.agency}</span>
      <h3 class="cert-name">${cert.name}</h3>
      <div class="cert-details">
        <div class="cert-detail"><span class="cert-detail-label">Date</span><span class="cert-detail-value">${formatDate(cert.certification_date)}</span></div>
        ${cert.certification_number ? `<div class="cert-detail"><span class="cert-detail-label">Number</span><span class="cert-detail-value">${cert.certification_number}</span></div>` : ''}
        ${cert.instructor_name ? `<div class="cert-detail"><span class="cert-detail-label">Instructor</span><span class="cert-detail-value">${cert.instructor_name}</span></div>` : ''}
      </div>
      <div class="cert-actions">
        <button class="btn-icon danger" onclick="confirmDeleteCert('${cert._id}')" title="Delete">🗑</button>
      </div>
    </div>
  `;
}

/* -------------------------------------------------
   CHECKLISTS
--------------------------------------------------*/
async function loadChecklists() {
  const container = document.getElementById('checklists-list');
  container.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const response = await fetch(`${CERTS_API}/checklists`);
    if (!response.ok) throw new Error();

    const checklists = await response.json();

    if (checklists.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>No checklists</h3>
        </div>`;
      return;
    }

    container.innerHTML = checklists.map(renderChecklistItem).join('');

  } catch (error) {
    console.error(error);
    container.innerHTML = '<div>Error loading checklists</div>';
  }
}

function renderChecklistItem(item) {
  return `
    <div class="checklist-item">
      <span class="checklist-name">${item.name}</span>
      <a href="${item.link}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm">Open</a>
    </div>
  `;
}

/* -------------------------------------------------
   DATE HELPERS
--------------------------------------------------*/
function formatDate(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

function formatDateForInput(timestamp) {
  const date = new Date(timestamp);
  return date.toISOString().split('T')[0];
}

/* -------------------------------------------------
   NAVIGATION
--------------------------------------------------*/
function setupNavigation() {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      switchView(view);
    });
  });
}

function switchView(viewName) {
  document.querySelectorAll('.nav-btn').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.view === viewName)
  );

  document.querySelectorAll('.view').forEach(view =>
    view.classList.remove('active')
  );

  document.getElementById(`${viewName}-view`).classList.add('active');

  if (viewName === 'home') loadLatestDive();
  else if (viewName === 'dives') loadAllDives();
  else if (viewName === 'certifications') loadCertifications();
  else if (viewName === 'checklists') loadChecklists();
}

/* -------------------------------------------------
   DELETE CONFIRMATION
--------------------------------------------------*/
function confirmDeleteDive(id) {
  document.getElementById('confirm-message').textContent =
    'Are you sure you want to delete this dive?';
  document.getElementById('confirm-delete-btn').onclick =
    () => deleteDive(id);
  document.getElementById('confirm-modal').classList.add('active');
}

async function deleteDive(id) {
  try {
    const response = await fetch(`${DIVES_API}/dives/${id}`, {
      method: 'DELETE'
    });

    if (!response.ok) throw new Error();
    showToast('Dive deleted successfully');
    closeConfirmModal();
    loadAllDives();
  } catch (error) {
    showToast('Failed to delete dive', 'error');
  }
}

function confirmDeleteCert(id) {
  document.getElementById('confirm-message').textContent =
    'Are you sure you want to delete this certification?';
  document.getElementById('confirm-delete-btn').onclick =
    () => deleteCertification(id);
  document.getElementById('confirm-modal').classList.add('active');
}

async function deleteCertification(id) {
  try {
    const response = await fetch(`${CERTS_API}/certifications/${id}`, {
      method: 'DELETE'
    });

    if (!response.ok) throw new Error();
    showToast('Certification deleted successfully');
    closeConfirmModal();
    loadCertifications();
  } catch (error) {
    showToast('Failed to delete certification', 'error');
  }
}

function closeConfirmModal() {
  document.getElementById('confirm-modal').classList.remove('active');
}

/* -------------------------------------------------
   TOAST NOTIFICATIONS
--------------------------------------------------*/
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}
``
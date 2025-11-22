// Admin dashboard JS: sidebar toggling + flash auto-hide
document.addEventListener('DOMContentLoaded', function(){
    const links = document.querySelectorAll('.sidebar-link');
    const sections = document.querySelectorAll('.admin-section');

    function showSection(id){
        sections.forEach(s => s.style.display = 'none');
        const target = document.getElementById(id);
        if(target) target.style.display = '';
        links.forEach(l => l.classList.remove('active'));
        const active = Array.from(links).find(l => l.dataset.target === id);
        if(active) active.classList.add('active');

        // If opening activity section, load and start auto-refresh. Otherwise stop it.
        if(id === 'section-activity'){
            // load immediately and start polling
            loadRecentActivity();
            if(typeof startActivityAutoRefresh === 'function') startActivityAutoRefresh();
        } else if(id === 'section-services'){
            // load services when the services section is shown
            if(typeof loadServices === 'function') loadServices();
        } else {
            if(typeof stopActivityAutoRefresh === 'function') stopActivityAutoRefresh();
        }
    }

    links.forEach(l => {
        const tgt = l.dataset.target;
        if(!tgt) return;
        l.addEventListener('click', function(e){
            e.preventDefault();
            showSection(tgt);
        });
    });

    // Initial state: show list by default
    showSection('section-list');
});

// Flash messages auto-hide
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => {
                msg.style.display = 'none';
            }, 500);
        }, 5000);
    });
});

// Fetch recent activity from API when activity section is shown
function renderActivity(list) {
    const container = document.querySelector('#section-activity .recent-activity');
    if(!container) return;
    container.innerHTML = '';
    if(!list || list.length === 0) {
        container.innerHTML = `
            <div class="activity-item">
                <div class="activity-icon">ℹ️</div>
                <div class="activity-content"><div class="activity-title">Aucune activité récente</div></div>
            </div>`;
        return;
    }
    list.forEach(item => {
        const node = document.createElement('div');
        node.className = 'activity-item';
        node.innerHTML = `
            <div class="activity-icon">${item.icon || 'ℹ️'}</div>
            <div class="activity-content">
                <div class="activity-title">${item.title || ''}</div>
                <div class="activity-time">${item.time || ''}</div>
            </div>`;
        container.appendChild(node);
    });
}

async function loadRecentActivity() {
    try {
        const resp = await fetch('/api/admin/recent-activity', { credentials: 'same-origin' });
        if(!resp.ok) {
            console.warn('Could not fetch activity, status', resp.status);
            return;
        }
        const data = await resp.json();
        renderActivity(data.recent_activity || []);
    } catch (e) {
        console.warn('Error fetching recent activity', e);
    }
}

// Enhance showSection to automatically load activity when needed
document.addEventListener('DOMContentLoaded', function(){
    const links = document.querySelectorAll('.sidebar-link');
    links.forEach(l => {
        if(l.dataset.target === 'section-activity'){
            l.addEventListener('click', function(){
                // load latest activity from API
                loadRecentActivity();
            });
        }
    });
    // If the hash has #activity, open it and load
    if(window.location.hash === '#activity'){
        const actLink = Array.from(links).find(l => l.dataset.target === 'section-activity');
        if(actLink){ actLink.click(); }
    }
        // If the hash is #services open services
        if(window.location.hash === '#services'){
            const svcLink = Array.from(links).find(l => l.dataset.target === 'section-services');
            if(svcLink){ svcLink.click(); }
        }
});

// Patients table filter by doctor
document.addEventListener('DOMContentLoaded', function(){
    const filter = document.getElementById('patient-doctor-filter');
    if(!filter) return;
    const table = document.getElementById('patients-table');
    const rows = table ? Array.from(table.querySelectorAll('tbody tr')) : [];

    function applyFilter() {
        const v = filter.value.trim();
        rows.forEach(r => {
            const doctor = (r.dataset.doctor || '').trim();
            if(!v || doctor === v) {
                r.style.display = '';
            } else {
                r.style.display = 'none';
            }
        });
    }

    filter.addEventListener('change', applyFilter);
});

let activityInterval = null;
function startActivityAutoRefresh() {
  if(activityInterval) return;
  activityInterval = setInterval(() => {
    // only load if section visible
    const section = document.getElementById('section-activity');
    if(section && section.style.display !== 'none') loadRecentActivity();
  }, 30000); // 30s
}
function stopActivityAutoRefresh() {
  if(activityInterval) { clearInterval(activityInterval); activityInterval = null; }
}
// call startActivityAutoRefresh() when activity section is shown

// Services: load and render service cards, handle add-service
async function loadServices() {
    try {
        const resp = await fetch('/api/admin/services', {credentials: 'same-origin'});
        if(!resp.ok) { console.warn('Could not fetch services', resp.status); return; }
        const data = await resp.json();
        renderServices(data.services || []);
    } catch (e) {
        console.warn('Error fetching services', e);
    }
}

function renderServices(list) {
    const grid = document.getElementById('services-grid');
    if(!grid) return;
    grid.innerHTML = '';
    if(!list || list.length === 0) {
        grid.innerHTML = '<p>Aucun service défini pour le moment.</p>';
        return;
    }
    // Deduplicate by id or by normalized name (preserve first occurrence)
    const seen = new Set();
    const unique = [];
    list.forEach(s => {
        if(!s || typeof s !== 'object') return;
        const key = (s.id && String(s.id)) || (s.name && String(s.name).trim().toLowerCase());
        if(!key) return;
        if(seen.has(key)) return;
        seen.add(key);
        unique.push(s);
    });

    unique.forEach(s => {
        const card = document.createElement('div');
        card.className = 'action-card';
        card.innerHTML = `
            <div class="action-title">${s.name || ''}</div>
            <div style="margin:8px 0;color:var(--text-light);">${s.code ? ('Code: '+s.code) : ''}</div>
            <div style="font-size:14px;color:#444;margin-bottom:12px;">${s.description || ''}</div>
            <div style="margin-top:auto;display:flex;gap:8px;">
                <button class="btn btn-primary btn-edit" data-id="${s.id}">Modifier</button>
                <button class="btn btn-danger btn-delete" data-id="${s.id}">Supprimer</button>
            </div>`;
        grid.appendChild(card);
    });

    // wire delete/edit buttons (delete will call API)
    grid.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', async function(){
            const id = this.dataset.id;
            if(!confirm('Supprimer ce service ?')) return;
            try {
                const r = await fetch('/admin/delete-service', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id})});
                if(r.ok) { loadServices(); }
                else alert('Suppression échouée');
            } catch(e){ console.warn(e); alert('Erreur suppression'); }
        });
    });
}

// Handle add-service form via AJAX (enhances UX but form still works by POST)
document.addEventListener('DOMContentLoaded', function(){
    const form = document.getElementById('add-service-form');
    if(!form) return;
    form.addEventListener('submit', async function(e){
        e.preventDefault();
        const formData = new FormData(form);
        const payload = {};
        formData.forEach((v,k) => payload[k]=v);
        try {
            const resp = await fetch(form.action, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
            if(resp.ok){
                // clear form
                form.reset();
                // reload services
                loadServices();
                alert('Service ajouté');
            } else {
                const txt = await resp.text();
                alert('Erreur: ' + txt);
            }
        } catch (err){ console.warn(err); alert('Erreur réseau'); }
    });
});

// Reload services from disease mapping button
document.addEventListener('DOMContentLoaded', function(){
    const btn = document.getElementById('reload-services-btn');
    if(!btn) return;
    btn.addEventListener('click', async function(){
        if(!confirm('Recharger la liste des services depuis le mapping des maladies ? Cela remplacera la liste actuelle.')) return;
        try {
            const resp = await fetch('/admin/reload-services-from-mapping', {method: 'POST', credentials: 'same-origin'});
            if(resp.ok) {
                await loadServices();
                alert('Services rechargés depuis le mapping.');
            } else {
                const txt = await resp.text();
                alert('Échec du rechargement: ' + txt);
            }
        } catch (e) {
            console.warn('Error reloading services', e);
            alert('Erreur réseau lors du rechargement.');
        }
    });
});
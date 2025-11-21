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
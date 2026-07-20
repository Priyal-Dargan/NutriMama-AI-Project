/**
 * nav.js — injects the shared sidebar nav into any authenticated page and
 * guards the page behind a login check. Include after api.js.
 *
 * Usage: <div id="app-shell"></div><script>NutriMamaNav.mount('dashboard');</script>
 */

const NAV_ITEMS = [
  { key: 'dashboard', href: 'dashboard.html', label: 'Dashboard', icon: 'grid' },
  { key: 'chat', href: 'chat.html', label: 'AI Chat', icon: 'chat' },
  { key: 'mealplanner', href: 'mealplanner.html', label: 'Meal Planner', icon: 'bowl' },
  { key: 'tracker', href: 'tracker.html', label: 'Nutrition Tracker', icon: 'chart' },
  { key: 'foodsafety', href: 'foodsafety.html', label: 'Food Safety', icon: 'shield' },
  { key: 'reports', href: 'reports.html', label: 'Reports', icon: 'doc' },
  { key: 'reminders', href: 'reminders.html', label: 'Reminders', icon: 'bell' },
  { key: 'resources', href: 'resources.html', label: 'Medical Resources', icon: 'book' },
  { key: 'settings', href: 'settings.html', label: 'Settings', icon: 'gear' },
];

const NAV_ICONS = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  chat: '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
  bowl: '<path d="M3 11h18a9 9 0 0 1-18 0z"/><path d="M12 11V3"/><path d="M8 6l4-3 4 3"/>',
  chart: '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  doc: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
  admin: '<path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/>',
};

function svgIcon(name, size = 18) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${NAV_ICONS[name] || ''}</svg>`;
}

function ringLogoSvg() {
  return `<svg class="ring-mini" viewBox="0 0 32 32" fill="none">
    <circle cx="16" cy="16" r="13" stroke="var(--color-border)" stroke-width="3"/>
    <path d="M16 3 A13 13 0 0 1 27.25 21.5" stroke="var(--color-primary)" stroke-width="3" stroke-linecap="round"/>
    <path d="M27.25 21.5 A13 13 0 0 1 16 29" stroke="var(--color-secondary)" stroke-width="3" stroke-linecap="round"/>
  </svg>`;
}

const NutriMamaNav = {
  async mount(activeKey) {
    Auth.requireAuth();

    const shell = document.getElementById('app-shell');
    if (!shell) return;
    shell.className = 'app-shell';

    const navLinks = NAV_ITEMS.map(item => `
      <a class="nav-link-app ${item.key === activeKey ? 'active' : ''}" href="${item.href}">
        ${svgIcon(item.icon)}<span>${item.label}</span>
      </a>
    `).join('');

    shell.innerHTML = `
      <aside class="app-sidebar">
        <a href="dashboard.html" class="brand" style="text-decoration:none;">${ringLogoSvg()}<span>NutriMama AI</span></a>
        ${navLinks}
        <div id="admin-nav-slot"></div>
        <div class="nav-divider"></div>
        <a href="#" class="nav-link-app" id="logout-link">${svgIcon('logout')}<span>Logout</span></a>
      </aside>
      <main class="app-main" id="app-main-content"></main>
    `;

    document.getElementById('logout-link').addEventListener('click', async (e) => {
      e.preventDefault();
      try { await Api.logout(); } catch (err) { /* ignore — clearing tokens client-side regardless */ }
      Auth.clear();
      window.location.href = 'login.html';
    });

    // Show Admin link only for admin users.
    try {
      const user = await Api.me();
      if (user.is_admin) {
        document.getElementById('admin-nav-slot').innerHTML = `
          <a class="nav-link-app ${activeKey === 'admin' ? 'active' : ''}" href="admin.html">
            ${svgIcon('admin')}<span>Admin Panel</span>
          </a>`;
      }
    } catch (err) { /* non-fatal — nav still works without the admin check */ }
  },
};

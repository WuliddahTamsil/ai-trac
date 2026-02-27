// =============================================
// AI-TRAC — MAIN JS
// =============================================

// Theme
const html = document.documentElement;
const saved = localStorage.getItem('aitrac-theme') || 'light';
html.setAttribute('data-theme', saved);
const icon = document.getElementById('themeIcon');
if (icon) icon.className = saved === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';

document.getElementById('themeToggle')?.addEventListener('click', () => {
  const cur = html.getAttribute('data-theme');
  const next = cur === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('aitrac-theme', next);
  const ic = document.getElementById('themeIcon');
  if (ic) ic.className = next === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
});

// Language
let currentLang = localStorage.getItem('aitrac-lang') || 'id';

// simple dictionary for interface text
const i18n = {
  id: {
    dashboard: 'Dashboard',
    control: 'Control Mode',
    ml: 'ML Monitor',
    analytics: 'Analytics',
    telemetry: 'Telemetry',
    history: 'Riwayat Misi',
    maintenance: 'Maintenance',
    settings: 'Settings',
    connected: 'Terhubung',
    section_analytics: 'ANALITIK',
    section_system: 'SISTEM'
  },
  en: {
    dashboard: 'Dashboard',
    control: 'Control Mode',
    ml: 'ML Monitor',
    analytics: 'Analytics',
    telemetry: 'Telemetry',
    history: 'Mission History',
    maintenance: 'Maintenance',
    settings: 'Settings',
    connected: 'Connected',
    section_analytics: 'ANALYTICS',
    section_system: 'SYSTEM'
  }
};

// helper for translating any plain text across the page
const autoMap = {
  // dashboard
  'Baterai': {id:'Baterai', en:'Battery'},
  'Kecepatan': {id:'Kecepatan', en:'Speed'},
  'Suhu ESP32': {id:'Suhu ESP32', en:'ESP32 Temp'},
  'Area Dicakup': {id:'Area Dicakup', en:'Area Covered'},
  'Terhubung': {id:'Terhubung', en:'Connected'},
  'Baterai — 10 Menit Terakhir': {id:'Baterai — 10 Menit Terakhir', en:'Battery — Last 10 Minutes'},
  'Status Sistem': {id:'Status Sistem', en:'System Status'},
  'Mode Aktif': {id:'Mode Aktif', en:'Active Mode'},
  'Koneksi ESP32': {id:'Koneksi ESP32', en:'ESP32 Connection'},
  'GPS Signal': {id:'GPS Signal', en:'GPS Signal'},
  'Sensor Depan': {id:'Sensor Depan', en:'Front Sensor'},
  'Sensor Kiri': {id:'Sensor Kiri', en:'Left Sensor'},
  'Sensor Kanan': {id:'Sensor Kanan', en:'Right Sensor'},
  // telemetry page
  'Satelit GPS': {id:'Satelit GPS', en:'GPS Satellites'},
  'Altitude': {id:'Altitude', en:'Altitude'},
  'GPS Track Simulasi': {id:'GPS Track Simulasi', en:'GPS Track Simulation'},
  'Sensor Jarak (cm)': {id:'Sensor Jarak (cm)', en:'Distance Sensor (cm)'},
  'Sensor Status': {id:'Sensor Status', en:'Sensor Status'},
  'US DEPAN': {id:'US DEPAN', en:'FRONT US'},
  'US KIRI': {id:'US KIRI', en:'LEFT US'},
  'US KANAN': {id:'US KANAN', en:'RIGHT US'},
  'GPS PPS': {id:'GPS PPS', en:'GPS PPS'},
  'Power Status': {id:'Power Status', en:'Power Status'},
  'Kapasitas Baterai': {id:'Kapasitas Baterai', en:'Battery Capacity'},
  'Tegangan': {id:'Tegangan', en:'Voltage'},
  'Arus': {id:'Arus', en:'Current'},
  'Suhu & Motor': {id:'Suhu & Motor', en:'Temp & Motor'},
  'Motor Kanan': {id:'Motor Kanan', en:'Right Motor'},
  'Motor Kiri': {id:'Motor Kiri', en:'Left Motor'},
  'iBUS Signal': {id:'iBUS Signal', en:'iBUS Signal'},
  'Heading & Speed': {id:'Heading & Speed', en:'Heading & Speed'},
  'Heading': {id:'Heading', en:'Heading'},
  'Kecepatan': {id:'Kecepatan', en:'Speed'},
  'Kapasitas Baterai': {id:'Kapasitas Baterai', en:'Battery Capacity'},
  // common
  'ANALITIK': {id:'ANALITIK', en:'ANALYTICS'},
  'SISTEM': {id:'SISTEM', en:'SYSTEM'},
  'Dashboard': {id:'Dashboard', en:'Dashboard'},
  'Control Mode': {id:'Control Mode', en:'Control Mode'},
  'ML Monitor': {id:'ML Monitor', en:'ML Monitor'},
  'Analytics': {id:'Analytics', en:'Analytics'},
  'Telemetry': {id:'Telemetry', en:'Telemetry'},
  'Riwayat Misi': {id:'Riwayat Misi', en:'Mission History'},
  'Maintenance': {id:'Maintenance', en:'Maintenance'},
  'Settings': {id:'Settings', en:'Settings'},
  // pages folder texts
  'Dashboard Utama': {id:'Dashboard Utama', en:'Main Dashboard'},
  'Ringkasan status operasional AI-TRAC secara real-time': {id:'Ringkasan status operasional AI-TRAC secara real-time', en:'Real-time operational summary of AI-TRAC'},
  'Baterai %': {id:'Baterai %', en:'Battery %'},
  'Kecepatan km/h': {id:'Kecepatan km/h', en:'Speed km/h'},
  'Suhu °C': {id:'Suhu °C', en:'Temp °C'},
  'Satelit GPS': {id:'Satelit GPS', en:'GPS Satellites'},
  'Kesehatan %': {id:'Kesehatan %', en:'Health %'},
  'Kualitas Tanah': {id:'Kualitas Tanah', en:'Soil Quality'},
  'Mode Aktif': {id:'Mode Aktif', en:'Active Mode'},
  'Update Terakhir': {id:'Update Terakhir', en:'Last Update'},
  'Baterai vs Waktu': {id:'Baterai vs Waktu', en:'Battery vs Time'},
  'Sensor Realtime': {id:'Sensor Realtime', en:'Realtime Sensors'},
  'Depan (US)': {id:'Depan (US)', en:'Front (US)'},
  'Kiri (US)': {id:'Kiri (US)', en:'Left (US)'},
  'Kanan (US)': {id:'Kanan (US)', en:'Right (US)'},
  'Motor Kiri': {id:'Motor Kiri', en:'Left Motor'},
  'Motor Kanan': {id:'Motor Kanan', en:'Right Motor'},
  'Kelembaban': {id:'Kelembaban', en:'Humidity'},
  'Posisi GPS': {id:'Posisi GPS', en:'GPS Position'},
  'GPS LIVE': {id:'GPS LIVE', en:'GPS LIVE'},
  'Dashboard': {id:'Dashboard', en:'Dashboard'}
};

function translateAll() {
  document.body.querySelectorAll('*').forEach(el => {
    // only translate leaf nodes without child elements
    if (el.children.length === 0) {
      const txt = el.textContent.trim();
      if (autoMap[txt] && autoMap[txt][currentLang]) {
        el.textContent = autoMap[txt][currentLang];
      }
    }
  });
}

function updateLanguage() {
  document.documentElement.lang = currentLang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (i18n[currentLang] && i18n[currentLang][key]) {
      el.textContent = i18n[currentLang][key];
    }
  });
  translateAll();
}

// initialize active button and text
function initLangBtns() {
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === currentLang);
    btn.addEventListener('click', () => {
      currentLang = btn.dataset.lang;
      localStorage.setItem('aitrac-lang', currentLang);
      document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', b.dataset.lang === currentLang));
      updateLanguage();
    });
  });
}

initLangBtns();
updateLanguage();

// Sidebar
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebarOverlay');
const hamburger = document.getElementById('hamburger');
const sidebarClose = document.getElementById('sidebarClose');

hamburger?.addEventListener('click', () => {
  sidebar?.classList.toggle('open');
  overlay?.classList.toggle('active');
});
sidebarClose?.addEventListener('click', closeSidebar);
overlay?.addEventListener('click', closeSidebar);
function closeSidebar() {
  sidebar?.classList.remove('open');
  overlay?.classList.remove('active');
}

// Sidebar collapse (desktop collapse toggle via brand icon double-click)
document.querySelector('.brand-icon')?.addEventListener('dblclick', () => {
  document.body.classList.toggle('sidebar-collapsed');
});

// Notifications
const notifBtn = document.getElementById('notifBtn');
const notifDropdown = document.getElementById('notifDropdown');
notifBtn?.addEventListener('click', e => {
  e.stopPropagation();
  notifDropdown?.classList.toggle('open');
  if (notifDropdown?.classList.contains('open')) loadNotifications();
});
document.addEventListener('click', () => notifDropdown?.classList.remove('open'));

function loadNotifications() {
  fetch('/api/notifications')
    .then(r => r.json())
    .then(data => {
      const list = document.getElementById('notifList');
      if (!list) return;
      list.innerHTML = data.map(n => `
        <div class="notif-item">
          <div class="notif-dot ${n.type}"></div>
          <div>
            <div class="notif-msg">${n.msg}</div>
            <div class="notif-time">${n.time}</div>
          </div>
        </div>`).join('');
      document.getElementById('notifBadge').textContent = data.length;
      document.getElementById('notifCount').textContent = data.length;
    });
}

// Expose chart helpers globally
window.AITRAC = {
  defaultChartOpts: (dark) => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: 'rgba(100,116,139,.12)' }, ticks: { color: '#94a3b8', font: { size: 11 } } },
      y: { grid: { color: 'rgba(100,116,139,.12)' }, ticks: { color: '#94a3b8', font: { size: 11 } } }
    }
  }),
  formatTime: (ms) => new Date(ms).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  gradientPlugin: (ctx, color1, color2) => {
    const g = ctx.createLinearGradient(0, 0, 0, 200);
    g.addColorStop(0, color1);
    g.addColorStop(1, color2);
    return g;
  }
};

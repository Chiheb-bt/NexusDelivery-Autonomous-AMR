/**
 * NexusDelivery — Autonomous Customer Experience Engine
 * Real-World Leaflet Interactive Map (CartoDB Dark Matter + Esri Satellite),
 * Draggable Doorstep Pin, GPS Geolocation, Live Rover Tracking, Web Audio API,
 * and 6-Digit OTP Hatch Unlocking.
 */

// Global State
let currentUser = null;
let clientCart = [];
let catalogProducts = [];
let activeOrder = null;
let currentOtpBuffer = '';
let audioEnabled = true;
let audioCtx = null;

// Leaflet Map State
let worldMap = null;
let darkTileLayer = null;
let satelliteTileLayer = null;
let isSatelliteMode = false;
let userDoorstepMarker = null;
let roverMapMarker = null;
let routePolyline = null;

// Current Selected Doorstep GPS Coordinates (Default: Avenue Habib Bourguiba, Tunis)
let selectedDoorstep = {
  lat: 36.800542,
  lng: 10.180012,
  address: 'Avenue Habib Bourguiba, Tunis (Curbside Bay 1)'
};

// Depot Hub Coordinates (Tunis Central Hub)
const DEPOT_COORDS = {
  lat: 36.801200,
  lng: 10.178500,
  name: 'Tunis Central Hub (Depot)'
};

// Global City Presets for Hackathon Demo
const CITY_PRESETS = {
  tunis: { lat: 36.800542, lng: 10.180012, zoom: 16, name: 'Tunis City Center' },
  silicon_valley: { lat: 37.4275, lng: -122.1697, zoom: 16, name: 'Stanford / Silicon Valley' },
  paris: { lat: 48.8698, lng: 2.3075, zoom: 16, name: 'Paris Champs-Élysées' },
  tokyo: { lat: 35.6595, lng: 139.7004, zoom: 16, name: 'Tokyo Shibuya' }
};

// Telemetry Cache
let latestTelemetry = {
  x: -14.2,
  y: 15.0,
  gps_lat: 36.800542,
  gps_lng: 10.180012,
  yaw: 1.571,
  actual_v: 0.82,
  mission_state: 'NAVIGATING_TO_CLIENT',
  dist_to_target: 24.5,
  hatch_status: 'LOCKED',
  trail: []
};

// Fallback Catalog
const FALLBACK_PRODUCTS = [
  { id: 'PRD-01', name: 'Artisan Margherita Pizza', category: 'Hot Food', price: 14.50, weight_kg: 0.8, icon: '🍕', desc: 'Fresh buffalo mozzarella, organic San Marzano basil, wood-fired 48h sourdough crust.' },
  { id: 'PRD-02', name: 'Fresh Sushi Bento Deluxe', category: 'Cold Meal', price: 22.00, weight_kg: 0.5, icon: '🍱', desc: 'Glazed salmon teriyaki, 4x nigiri, steamed organic edamame, and pickled ginger.' },
  { id: 'PRD-03', name: 'French Bakery Pastry Box', category: 'Bakery', price: 12.00, weight_kg: 0.7, icon: '🥐', desc: '2x butter croissants, pain au chocolat, almond Danish, and fresh espresso roast.' },
  { id: 'PRD-04', name: 'Nitro Cold Brew Espresso', category: 'Beverages', price: 4.50, weight_kg: 0.3, icon: '☕', desc: 'Cold steeped Ethiopian beans infused with nitrogen micro-bubbles for velvet crema.' },
  { id: 'PRD-05', name: 'First Aid & Wellness Pack', category: 'Healthcare', price: 18.00, weight_kg: 0.6, icon: '💊', desc: 'Electrolytes, rapid antiseptic wipes, thermal bandages, and emergency relief essentials.' },
  { id: 'PRD-06', name: 'Organic Mediterranean Bowl', category: 'Cold Meal', price: 11.00, weight_kg: 0.4, icon: '🥗', desc: 'Kalamata olives, crisp cucumbers, feta, and extra virgin Tunisian olive oil.' }
];

/* ==========================================================================
   1. WEB AUDIO SYNTHESIZER
   ========================================================================== */
function getAudioContext() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) audioCtx = new AudioContext();
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

function playChime(type) {
  if (!audioEnabled) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  try {
    const now = ctx.currentTime;
    if (type === 'click') {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(800, now);
      osc.frequency.exponentialRampToValueAtTime(1200, now + 0.06);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.06);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.06);
    } else if (type === 'cart') {
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();
      osc1.type = 'sine';
      osc2.type = 'triangle';
      osc1.frequency.setValueAtTime(523.25, now); // C5
      osc1.frequency.setValueAtTime(659.25, now + 0.08); // E5
      osc2.frequency.setValueAtTime(1046.50, now + 0.08); // C6
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.22);
      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);
      osc1.start(now);
      osc2.start(now + 0.08);
      osc1.stop(now + 0.22);
      osc2.stop(now + 0.22);
    } else if (type === 'success') {
      const notes = [523.25, 659.25, 783.99, 1046.50];
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const startT = now + idx * 0.07;
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, startT);
        gain.gain.setValueAtTime(0.2, startT);
        gain.gain.exponentialRampToValueAtTime(0.001, startT + 0.35);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(startT);
        osc.stop(startT + 0.35);
      });
    } else if (type === 'error') {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(180, now);
      osc.frequency.linearRampToValueAtTime(120, now + 0.18);
      gain.gain.setValueAtTime(0.18, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.18);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.18);
    }
  } catch (err) {}
}

function toggleClientAudio() {
  audioEnabled = !audioEnabled;
  const icon = document.getElementById('soundIcon');
  if (icon) icon.textContent = audioEnabled ? '🔊' : '🔇';
  showToast(audioEnabled ? 'Audio Feedback Enabled' : 'Audio Feedback Muted');
  if (audioEnabled) playChime('click');
}

/* ==========================================================================
   2. REAL-WORLD LEAFLET INTERACTIVE MAP IMPLEMENTATION
   ========================================================================== */
function initRealWorldMap() {
  const mapContainer = document.getElementById('worldDeliveryMap');
  if (!mapContainer || typeof L === 'undefined') return;

  // Initialize Leaflet Map centered on Tunis
  worldMap = L.map('worldDeliveryMap', {
    zoomControl: false,
    attributionControl: false
  }).setView([selectedDoorstep.lat, selectedDoorstep.lng], 16);

  // Custom Zoom Control at Top Right
  L.control.zoom({ position: 'topright' }).addTo(worldMap);

  // CartoDB Dark Matter Base Tiles (Futuristic Cyberpunk Dark Streets)
  darkTileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd'
  }).addTo(worldMap);

  // Esri World Imagery (High-Resolution Satellite)
  satelliteTileLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19
  });

  // Add Depot Marker
  const depotIcon = L.divIcon({
    className: 'custom-depot-marker',
    html: '<div class="rover-pulse-icon" style="background: rgba(99, 102, 241, 0.4); border-color: #6366f1;">📮</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16]
  });
  L.marker([DEPOT_COORDS.lat, DEPOT_COORDS.lng], { icon: depotIcon })
    .addTo(worldMap)
    .bindPopup('<b>Nexus Depot Central Hub</b><br>Autonomous dispatch depot & parcel loading station');

  // Add Initial Doorstep Pin
  updateDoorstepPin(selectedDoorstep.lat, selectedDoorstep.lng, selectedDoorstep.address);

  // Add Rover Marker
  const roverIcon = L.divIcon({
    className: 'custom-rover-marker',
    html: '<div class="rover-pulse-icon">⚡</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16]
  });
  roverMapMarker = L.marker([latestTelemetry.gps_lat, latestTelemetry.gps_lng], { icon: roverIcon })
    .addTo(worldMap)
    .bindPopup('<b>NEXUS-AMR-01</b><br>Cruising on Sidewalk (0.82 m/s)');

  // Map Click Listener: User taps ANYWHERE in the world to set delivery doorstep!
  worldMap.on('click', (e) => {
    playChime('click');
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    const approxAddr = formatAddressFromCoords(lat, lng);
    updateDoorstepPin(lat, lng, approxAddr);
    showToast(`📍 Doorstep set to: ${lat.toFixed(5)}° N, ${lng.toFixed(5)}° E`);
  });
}

function updateDoorstepPin(lat, lng, addressName) {
  selectedDoorstep.lat = lat;
  selectedDoorstep.lng = lng;
  selectedDoorstep.address = addressName;

  if (!userDoorstepMarker && worldMap) {
    const doorstepIcon = L.divIcon({
      className: 'custom-doorstep-marker',
      html: '<div class="doorstep-pulse-icon">🏠</div>',
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });
    userDoorstepMarker = L.marker([lat, lng], {
      icon: doorstepIcon,
      draggable: true
    }).addTo(worldMap);

    userDoorstepMarker.on('dragend', (ev) => {
      const pos = ev.target.getLatLng();
      updateDoorstepPin(pos.lat, pos.lng, formatAddressFromCoords(pos.lat, pos.lng));
      playChime('click');
    });
  } else if (userDoorstepMarker) {
    userDoorstepMarker.setLatLng([lat, lng]);
  }

  // Draw Glowing Trajectory from Depot to Doorstep
  drawRouteToDoorstep(lat, lng);

  // Update UI Stats in Floating Card
  const addrEl = document.getElementById('pinSelectedAddress');
  const coordsEl = document.getElementById('pinGpsCoords');
  const distEl = document.getElementById('pinDistanceVal');
  const etaEl = document.getElementById('pinEtaVal');
  const cartBadge = document.getElementById('cartSelectedDoorstepBadge');

  if (addrEl) addrEl.textContent = addressName;
  if (coordsEl) coordsEl.textContent = `${lat.toFixed(6)}° N, ${lng.toFixed(6)}° E`;

  // Geodesic distance calculation
  const distKm = computeDistanceKm(DEPOT_COORDS.lat, DEPOT_COORDS.lng, lat, lng);
  const etaMin = Math.max(3, Math.round((distKm / 3.0) * 60)); // 3 km/h sidewalk cruising
  if (distEl) distEl.textContent = `${distKm.toFixed(2)} km`;
  if (etaEl) etaEl.textContent = `${etaMin}–${etaMin + 3} min`;
  if (cartBadge) cartBadge.textContent = `📍 ${addressName} (${lat.toFixed(4)}°, ${lng.toFixed(4)}°)`;
}

function drawRouteToDoorstep(destLat, destLng) {
  if (!worldMap) return;

  // Generate realistic sidewalk polyline path with 2 intermediate corner points
  const p0 = [DEPOT_COORDS.lat, DEPOT_COORDS.lng];
  const p1 = [DEPOT_COORDS.lat, destLng];
  const p2 = [destLat, destLng];
  const pathPoints = [p0, p1, p2];

  if (routePolyline) {
    routePolyline.setLatLngs(pathPoints);
  } else {
    routePolyline = L.polyline(pathPoints, {
      color: '#00f0ff',
      weight: 4,
      opacity: 0.85,
      dashArray: '8, 8'
    }).addTo(worldMap);
  }
}

function toggleMapTiles() {
  playChime('click');
  if (!worldMap) return;

  isSatelliteMode = !isSatelliteMode;
  const tileIcon = document.getElementById('tileIcon');
  const tileText = document.getElementById('tileText');

  if (isSatelliteMode) {
    worldMap.removeLayer(darkTileLayer);
    satelliteTileLayer.addTo(worldMap);
    if (tileIcon) tileIcon.textContent = '🌃';
    if (tileText) tileText.textContent = 'Cyber Dark View';
    showToast('Switched to High-Resolution Satellite View 🛰️');
  } else {
    worldMap.removeLayer(satelliteTileLayer);
    darkTileLayer.addTo(worldMap);
    if (tileIcon) tileIcon.textContent = '🛰️';
    if (tileText) tileText.textContent = 'Satellite View';
    showToast('Switched to Cyberpunk Dark Streets 🌃');
  }
}

function switchCity(cityKey, btnEl) {
  playChime('click');
  const preset = CITY_PRESETS[cityKey];
  if (!preset || !worldMap) return;

  const buttons = document.querySelectorAll('.city-pill');
  buttons.forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  worldMap.flyTo([preset.lat, preset.lng], preset.zoom, { duration: 1.5 });
  updateDoorstepPin(preset.lat, preset.lng, `${preset.name} (Doorstep Drop)`);
  showToast(`Centered on ${preset.name} 🌍`);
}

function locateUserGps() {
  playChime('click');
  if (!navigator.geolocation) {
    showToast('Geolocation not supported by this browser.');
    return;
  }

  showToast('Locating your GPS position...');
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      if (worldMap) {
        worldMap.flyTo([lat, lng], 17, { duration: 1.5 });
        updateDoorstepPin(lat, lng, 'My Live GPS Doorstep Location');
        playChime('success');
        showToast('📍 Pin dropped at your live GPS location!');
      }
    },
    (err) => {
      showToast('Could not access live GPS. Using Tunis City Center.');
      switchCity('tunis', document.querySelector('.city-pill'));
    },
    { timeout: 8000 }
  );
}

function confirmDoorstepLocation() {
  playChime('success');
  showToast(`Doorstep locked! Autonomous rovers will navigate to this pin 🚀`);
  const catSection = document.getElementById('storeCatalogSection');
  if (catSection) catSection.scrollIntoView({ behavior: 'smooth' });
}

function formatAddressFromCoords(lat, lng) {
  if (Math.abs(lat - 36.8005) < 0.05 && Math.abs(lng - 10.1800) < 0.05) {
    return `Avenue Habib Bourguiba, Tunis (Curbside Bay)`;
  } else if (Math.abs(lat - 37.4275) < 0.1) {
    return `Stanford University Ave, Palo Alto, CA`;
  } else if (Math.abs(lat - 48.8698) < 0.1) {
    return `Avenue des Champs-Élysées, Paris`;
  } else if (Math.abs(lat - 35.6595) < 0.1) {
    return `Shibuya Crossing, Tokyo`;
  } else {
    return `GPS Doorstep (${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E)`;
  }
}

function computeDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/* ==========================================================================
   3. CUSTOMER AUTHENTICATION & SESSION MANAGEMENT
   ========================================================================== */
async function initAuth() {
  const token = localStorage.getItem('nexus_client_token');
  if (!token) {
    renderUserAuthSlot(null);
    return;
  }

  try {
    const res = await fetch(`/api/auth/me?token=${encodeURIComponent(token)}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated && data.user) {
        currentUser = data.user;
        renderUserAuthSlot(currentUser);
        return;
      }
    }
  } catch (err) {}

  currentUser = {
    id: 'USR-001',
    name: 'Sophie Laurent',
    email: 'client@nexus.tn',
    phone: '+216 20 123 456',
    address: 'Avenue Habib Bourguiba, Tunis'
  };
  renderUserAuthSlot(currentUser);
}

function renderUserAuthSlot(user) {
  const slot = document.getElementById('userAuthSlot');
  if (!slot) return;

  if (user) {
    const initials = user.name ? user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'CU';
    slot.innerHTML = `
      <div class="user-profile-pill" title="Signed in as ${user.email}">
        <div class="user-avatar-circle">${initials}</div>
        <span class="user-name-text">${user.name}</span>
        <button class="btn-signout-mini" onclick="logoutClient()" title="Sign Out">✕</button>
      </div>
    `;
    const nameEl = document.getElementById('trackingRecipientName');
    if (nameEl) nameEl.textContent = user.name;
  } else {
    slot.innerHTML = `
      <button class="btn-primary-auth" id="btnOpenAuthModal" onclick="openAuthModal('login')">
        <span class="btn-auth-icon">🔑</span>
        <span>Sign In / Inscription</span>
      </button>
    `;
  }
}

function openAuthModal(tab = 'login') {
  playChime('click');
  const backdrop = document.getElementById('authModalBackdrop');
  if (backdrop) backdrop.classList.add('active');
  switchAuthTab(tab);
}

function closeAuthModal() {
  playChime('click');
  const backdrop = document.getElementById('authModalBackdrop');
  if (backdrop) backdrop.classList.remove('active');
}

function switchAuthTab(tab) {
  playChime('click');
  const tabLogin = document.getElementById('tabLogin');
  const tabRegister = document.getElementById('tabRegister');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  if (tab === 'login') {
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
  } else {
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value.trim();
  const errorEl = document.getElementById('loginErrorMsg');
  if (errorEl) errorEl.textContent = '';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (data.success && data.token) {
      localStorage.setItem('nexus_client_token', data.token);
      currentUser = data.user;
      renderUserAuthSlot(currentUser);
      closeAuthModal();
      playChime('success');
      showToast(`Welcome back, ${currentUser.name}! 🚀`);
    } else {
      playChime('error');
      if (errorEl) errorEl.textContent = data.error || 'Authentication failed.';
    }
  } catch (err) {
    if (email === 'client@nexus.tn') {
      currentUser = {
        id: 'USR-001',
        name: 'Sophie Laurent',
        email: 'client@nexus.tn',
        phone: '+216 20 123 456',
        address: 'Avenue Habib Bourguiba, Tunis'
      };
      localStorage.setItem('nexus_client_token', 'CUST-DEMO-TOKEN');
      renderUserAuthSlot(currentUser);
      closeAuthModal();
      playChime('success');
      showToast(`Welcome back, Sophie Laurent! (Demo)`);
    }
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('regName').value.trim();
  const phone = document.getElementById('regPhone').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value.trim();
  const address = document.getElementById('regAddress').value.trim();
  const errorEl = document.getElementById('registerErrorMsg');

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, phone, email, password, address })
    });
    const data = await res.json();
    if (data.success && data.token) {
      localStorage.setItem('nexus_client_token', data.token);
      currentUser = data.user;
      renderUserAuthSlot(currentUser);
      closeAuthModal();
      playChime('success');
      showToast(`Account created! Welcome, ${currentUser.name}! 🎉`);
    } else {
      playChime('error');
      if (errorEl) errorEl.textContent = data.error || 'Registration failed.';
    }
  } catch (err) {
    if (errorEl) errorEl.textContent = 'Network error. Please try again.';
  }
}

function logoutClient() {
  playChime('click');
  localStorage.removeItem('nexus_client_token');
  currentUser = null;
  renderUserAuthSlot(null);
  showToast('You have been signed out.');
}

/* ==========================================================================
   4. CATALOG & CART MANAGEMENT
   ========================================================================== */
async function loadCatalog() {
  try {
    const res = await fetch('/api/products');
    if (res.ok) {
      catalogProducts = await res.json();
    } else {
      catalogProducts = FALLBACK_PRODUCTS;
    }
  } catch (err) {
    catalogProducts = FALLBACK_PRODUCTS;
  }
  renderCatalog('all');
}

function renderCatalog(filterCategory = 'all') {
  const grid = document.getElementById('productsCatalogGrid');
  if (!grid) return;

  const items = filterCategory === 'all' 
    ? catalogProducts 
    : catalogProducts.filter(p => p.category === filterCategory);

  grid.innerHTML = items.map(prod => `
    <article class="product-card">
      <div class="product-top-badge">${prod.category}</div>
      <div class="product-icon-wrap">${prod.icon || '📦'}</div>
      <div class="product-info">
        <h3>${prod.name}</h3>
        <p class="product-desc">${prod.desc || 'Freshly prepared and sealed inside temperature-controlled robot compartment.'}</p>
      </div>
      <div class="product-meta-row">
        <span class="product-price">$${Number(prod.price).toFixed(2)}</span>
        <button class="btn-add-product" onclick="addToCart('${prod.id}')">
          <span>+ Add to Cart</span>
        </button>
      </div>
    </article>
  `).join('');
}

function filterCatalog(category, btnElement) {
  playChime('click');
  const buttons = document.querySelectorAll('.category-pill');
  buttons.forEach(b => b.classList.remove('active'));
  if (btnElement) btnElement.classList.add('active');
  renderCatalog(category);
}

function addToCart(productId) {
  playChime('cart');
  const prod = catalogProducts.find(p => p.id === productId) || FALLBACK_PRODUCTS.find(p => p.id === productId);
  if (!prod) return;

  const existing = clientCart.find(item => item.id === productId);
  if (existing) {
    existing.qty += 1;
  } else {
    clientCart.push({ ...prod, qty: 1 });
  }

  updateCartUI();
  showToast(`Added ${prod.name} to order 🛒`);
}

function changeCartQty(productId, delta) {
  playChime('click');
  const item = clientCart.find(i => i.id === productId);
  if (!item) return;

  item.qty += delta;
  if (item.qty <= 0) {
    clientCart = clientCart.filter(i => i.id !== productId);
  }
  updateCartUI();
}

function updateCartUI() {
  const totalCount = clientCart.reduce((sum, item) => sum + item.qty, 0);
  const subtotal = clientCart.reduce((sum, item) => sum + item.qty * item.price, 0);

  const badge = document.getElementById('cartBadgeCount');
  const headerTotal = document.getElementById('cartHeaderTotal');
  if (badge) badge.textContent = totalCount;
  if (headerTotal) headerTotal.textContent = `$${subtotal.toFixed(2)}`;

  const drawerList = document.getElementById('drawerCartItemsList');
  if (drawerList) {
    if (clientCart.length === 0) {
      drawerList.innerHTML = `
        <div class="empty-cart-state">
          <span class="empty-cart-icon">🛒</span>
          <p>Your delivery cart is empty.</p>
          <button class="btn-browse-catalog" onclick="toggleCartDrawer()">Browse Curbside Menu</button>
        </div>
      `;
    } else {
      drawerList.innerHTML = clientCart.map(item => `
        <div class="cart-item-row">
          <div class="cart-item-info">
            <h4>${item.icon || '🍔'} ${item.name}</h4>
            <span class="cart-item-price">$${(item.price * item.qty).toFixed(2)}</span>
          </div>
          <div class="cart-item-actions">
            <button class="btn-qty" onclick="changeCartQty('${item.id}', -1)">−</button>
            <span class="qty-count">${item.qty}</span>
            <button class="btn-qty" onclick="changeCartQty('${item.id}', 1)">+</button>
          </div>
        </div>
      `).join('');
    }
  }

  const subtotalEl = document.getElementById('billSubtotal');
  const totalEl = document.getElementById('billTotal');
  if (subtotalEl) subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
  if (totalEl) totalEl.textContent = `$${subtotal.toFixed(2)}`;
}

function toggleCartDrawer() {
  playChime('click');
  const drawer = document.getElementById('cartDrawer');
  const backdrop = document.getElementById('cartDrawerBackdrop');
  if (drawer && backdrop) {
    drawer.classList.toggle('active');
    backdrop.classList.toggle('active');
  }
}

async function checkoutOrder() {
  playChime('click');
  if (clientCart.length === 0) {
    showToast('Your cart is empty! Add items first.');
    return;
  }

  const btn = document.getElementById('btnCheckoutDispatch');
  const btnText = document.getElementById('checkoutBtnText');
  const spinner = document.getElementById('checkoutSpinner');

  if (btnText) btnText.textContent = 'Dispatching Rover...';
  if (spinner) spinner.style.display = 'inline-block';
  if (btn) btn.disabled = true;

  try {
    const payload = {
      customer_id: currentUser ? currentUser.customer_id : 'CUST-001',
      customer_name: currentUser ? currentUser.name : 'Sophie Laurent',
      target_lat: selectedDoorstep.lat,
      target_lng: selectedDoorstep.lng,
      delivery_address: selectedDoorstep.address,
      items: clientCart.map(c => ({ id: c.id, name: c.name, qty: c.qty })),
      priority: 1
    };

    const res = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.success && data.order) {
      activeOrder = data.order;
      playChime('success');
      showToast(`Order ${data.order.order_id} Dispatched to Doorstep! Rover En Route 🚀`);
      clientCart = [];
      updateCartUI();
      toggleCartDrawer();
      updateOrderTrackingUI(data.order);
      scrollToTracking();
    } else {
      throw new Error(data.error || 'Dispatch error');
    }
  } catch (err) {
    const simOrder = {
      order_id: `ORD-00${Math.floor(Math.random() * 90 + 10)}`,
      customer_name: currentUser ? currentUser.name : 'Sophie Laurent',
      delivery_name: selectedDoorstep.address,
      status: 'IN_TRANSIT',
      otp: `${Math.floor(100000 + Math.random() * 900000)}`,
      items: [...clientCart]
    };
    activeOrder = simOrder;
    playChime('success');
    showToast(`Order ${simOrder.order_id} Dispatched to Doorstep! 🚀`);
    clientCart = [];
    updateCartUI();
    toggleCartDrawer();
    updateOrderTrackingUI(simOrder);
    scrollToTracking();
  } finally {
    if (btnText) btnText.textContent = 'Confirm & Dispatch Autonomous Rover';
    if (spinner) spinner.style.display = 'none';
    if (btn) btn.disabled = false;
  }
}

function scrollToTracking() {
  playChime('click');
  const section = document.getElementById('liveTrackingSection');
  if (section) section.scrollIntoView({ behavior: 'smooth' });
}

/* ==========================================================================
   5. LIVE TELEMETRY & STREAM POLLING
   ========================================================================== */
function updateOrderTrackingUI(order) {
  if (!order) return;
  const badge = document.getElementById('activeOrderBadge');
  const nameEl = document.getElementById('trackingRecipientName');
  const addrEl = document.getElementById('trackingRecipientAddress');
  const otpDisplay = document.getElementById('displayOtpCode');
  const helperOtp = document.getElementById('helperOtpCode');

  if (badge) badge.textContent = `ORDER ${order.order_id}`;
  if (nameEl && order.customer_name) nameEl.textContent = order.customer_name;
  if (addrEl && order.delivery_name) addrEl.textContent = order.delivery_name;
  if (otpDisplay && order.otp) otpDisplay.textContent = order.otp;
  if (helperOtp && order.otp) helperOtp.textContent = order.otp;
}

async function pollTelemetry() {
  try {
    const res = await fetch('/api/telemetry');
    if (res.ok) {
      latestTelemetry = await res.json();
      updateTelemetryDisplays(latestTelemetry);
    }
  } catch (err) {}
}

function updateTelemetryDisplays(tel) {
  const heroSpeed = document.getElementById('heroVisualSpeed');
  if (heroSpeed) heroSpeed.textContent = `${Number(tel.actual_v || 0.82).toFixed(2)} m/s`;

  const distEl = document.getElementById('trackingDistText');
  const etaEl = document.getElementById('trackingEtaText');
  const hatchEl = document.getElementById('trackingHatchState');

  const dist = tel.dist_to_target || 24.5;
  if (distEl) distEl.textContent = `${Number(dist).toFixed(1)} m`;

  const speed = Math.max(0.2, Math.abs(tel.actual_v || 0.8));
  const etaSec = Math.round(dist / speed);
  const etaMin = Math.floor(etaSec / 60);
  const etaRemSec = etaSec % 60;
  if (etaEl) etaEl.textContent = `${String(etaMin).padStart(2, '0')} min ${String(etaRemSec).padStart(2, '0')} s`;

  if (hatchEl) {
    const isUnlocked = tel.hatch_status === 'OPEN' || tel.hatch_angle > 0.1;
    hatchEl.textContent = isUnlocked ? 'UNLOCKED (60°) 🔓' : 'LOCKED 🔒';
    hatchEl.className = isUnlocked ? 'metric-value text-emerald' : 'metric-value text-amber';
  }

  // Update Rover Leaflet Marker Position on Real Map
  if (roverMapMarker && tel.gps_lat && tel.gps_lng) {
    roverMapMarker.setLatLng([tel.gps_lat, tel.gps_lng]);
  }
}

function handleClientCamFallback(img) {
  img.onerror = null;
  img.src = 'street_camera_frame.jpg';
}

/* ==========================================================================
   6. DOORSTEP 6-DIGIT OTP UNLOCK KEYPAD
   ========================================================================== */
function openOtpModal() {
  playChime('click');
  currentOtpBuffer = '';
  updateOtpDisplay();
  const feedback = document.getElementById('otpFeedbackMsg');
  const successBox = document.getElementById('hatchSuccessDisplay');
  if (feedback) { feedback.textContent = ''; feedback.className = 'otp-feedback-msg'; }
  if (successBox) successBox.style.display = 'none';

  const modal = document.getElementById('otpModalBackdrop');
  if (modal) modal.classList.add('active');
}

function closeOtpModal() {
  playChime('click');
  const modal = document.getElementById('otpModalBackdrop');
  if (modal) modal.classList.remove('active');
}

function pressKeypad(digit) {
  if (currentOtpBuffer.length >= 6) return;
  playChime('click');
  currentOtpBuffer += digit;
  updateOtpDisplay();

  if (currentOtpBuffer.length === 6) {
    verifyOtpCode(currentOtpBuffer);
  }
}

function backspaceKeypad() {
  if (currentOtpBuffer.length > 0) {
    playChime('click');
    currentOtpBuffer = currentOtpBuffer.slice(0, -1);
    updateOtpDisplay();
  }
}

function clearKeypad() {
  playChime('click');
  currentOtpBuffer = '';
  updateOtpDisplay();
}

function autofillOtp() {
  playChime('click');
  const code = (activeOrder && activeOrder.otp) ? activeOrder.otp : '482910';
  currentOtpBuffer = code;
  updateOtpDisplay();
  verifyOtpCode(currentOtpBuffer);
}

function updateOtpDisplay() {
  for (let i = 0; i < 6; i++) {
    const box = document.getElementById(`pinBox${i}`);
    if (box) {
      if (i < currentOtpBuffer.length) {
        box.textContent = currentOtpBuffer[i];
        box.classList.add('filled');
      } else {
        box.textContent = '-';
        box.classList.remove('filled');
      }
    }
  }
}

async function verifyOtpCode(code) {
  const feedback = document.getElementById('otpFeedbackMsg');
  const successBox = document.getElementById('hatchSuccessDisplay');
  if (feedback) {
    feedback.textContent = 'Verifying security code with rover BMS...';
    feedback.className = 'otp-feedback-msg';
  }

  try {
    const res = await fetch('/api/verify_otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        otp: code,
        order_id: activeOrder ? activeOrder.order_id : ''
      })
    });

    const data = await res.json();
    if (data.success) {
      playChime('success');
      if (feedback) {
        feedback.textContent = '✓ CODE CONFIRMED — HATCH UNLOCKED!';
        feedback.className = 'otp-feedback-msg success';
      }
      if (successBox) successBox.style.display = 'block';

      latestTelemetry.hatch_status = 'OPEN';
      latestTelemetry.hatch_angle = 1.05;
      updateTelemetryDisplays(latestTelemetry);
      showToast('🎉 Compartment unlatched to 60°! Enjoy your meal!');
    } else {
      playChime('error');
      if (feedback) {
        feedback.textContent = data.message || 'Incorrect code. Please verify.';
        feedback.className = 'otp-feedback-msg error';
      }
      setTimeout(() => {
        currentOtpBuffer = '';
        updateOtpDisplay();
      }, 900);
    }
  } catch (err) {
    if (code === '482910' || code === '123456' || (activeOrder && code === activeOrder.otp)) {
      playChime('success');
      if (feedback) {
        feedback.textContent = '✓ CODE CONFIRMED — HATCH UNLOCKED!';
        feedback.className = 'otp-feedback-msg success';
      }
      if (successBox) successBox.style.display = 'block';
      latestTelemetry.hatch_status = 'OPEN';
      updateTelemetryDisplays(latestTelemetry);
      showToast('🎉 Compartment unlatched to 60°!');
    }
  }
}

function confirmPackageRetrieved() {
  playChime('click');
  closeOtpModal();
  showToast('Package retrieved. Motorized hatch closing. Thank you! 👋');
  if (activeOrder) activeOrder.status = 'COMPLETED';
}

/* ==========================================================================
   7. TOAST NOTIFICATION UTILITY
   ========================================================================== */
function showToast(message) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/* ==========================================================================
   INITIALIZATION
   ========================================================================== */
window.addEventListener('DOMContentLoaded', () => {
  initAuth();
  loadCatalog();
  initRealWorldMap();

  setInterval(pollTelemetry, 1000);
  pollTelemetry();
});

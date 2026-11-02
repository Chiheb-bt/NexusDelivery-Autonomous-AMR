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

// Gazebo World Map State
let gazeboMap = null;

// Current Selected Doorstep Coordinates in Gazebo Metric Space
let selectedDoorstep = {
  x: -9.80,
  y: 15.00,
  stopping_x: -14.60,
  stopping_y: 15.00,
  heading: 0.0,
  address: 'Sophie Laurent Doorstep (North Avenue Curbside Bay 1)',
  distance_m: 31.5,
  eta_seconds: 45,
  eta_minutes: 1
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
   2. AUTHENTIC GAZEBO SIMULATION WORLD VECTOR MAP INTEGRATION
   ========================================================================== */
function initGazeboMap() {
  const mapContainer = document.getElementById('gazeboCustomerMap');
  if (!mapContainer || typeof GazeboWorldMap === 'undefined') return;

  gazeboMap = new GazeboWorldMap({
    containerId: 'gazeboCustomerMap',
    mode: 'customer',
    onDestinationSelected: (pin) => {
      onDoorstepSelected(pin);
    }
  });

  // Default selection: Sophie Laurent doorstep
  if (selectedDoorstep) {
    const addrEl = document.getElementById('pinSelectedAddress');
    const coordsEl = document.getElementById('pinGpsCoords');
    const distEl = document.getElementById('pinDistanceVal');
    const etaEl = document.getElementById('pinEtaVal');
    if (addrEl) addrEl.textContent = selectedDoorstep.address;
    if (coordsEl) coordsEl.textContent = `X: ${selectedDoorstep.x.toFixed(2)}m, Y: ${selectedDoorstep.y.toFixed(2)}m`;
    if (distEl) distEl.textContent = `${selectedDoorstep.distance_m} m`;
    if (etaEl) etaEl.textContent = `~${selectedDoorstep.eta_seconds} sec`;
  }
}

function onDoorstepSelected(pin) {
  if (pin.valid) {
    selectedDoorstep = {
      x: pin.raw_xy[0],
      y: pin.raw_xy[1],
      stopping_x: pin.stopping_xy ? pin.stopping_xy[0] : pin.raw_xy[0],
      stopping_y: pin.stopping_xy ? pin.stopping_xy[1] : pin.raw_xy[1],
      heading: pin.heading || 0.0,
      address: pin.customer_name ? `${pin.customer_name} Doorstep` : `Doorstep (${pin.raw_xy[0].toFixed(1)}m, ${pin.raw_xy[1].toFixed(1)}m)`,
      distance_m: pin.distance_m || 0.0,
      eta_seconds: pin.eta_seconds || 0,
      eta_minutes: pin.eta_minutes || 1
    };

    const addrEl = document.getElementById('pinSelectedAddress');
    if (addrEl) addrEl.textContent = selectedDoorstep.address;

    const coordsEl = document.getElementById('pinGpsCoords');
    if (coordsEl) coordsEl.textContent = `X: ${pin.raw_xy[0].toFixed(2)}m, Y: ${pin.raw_xy[1].toFixed(2)}m`;

    const distEl = document.getElementById('pinDistanceVal');
    if (distEl) distEl.textContent = `${pin.distance_m || 0} m`;

    const etaEl = document.getElementById('pinEtaVal');
    if (etaEl) etaEl.textContent = pin.eta_seconds < 60 ? `~${pin.eta_seconds} sec` : `~${pin.eta_minutes} min`;

    const cartBadge = document.getElementById('cartSelectedDoorstepBadge');
    if (cartBadge) cartBadge.textContent = `📍 ${selectedDoorstep.address} (X:${pin.raw_xy[0].toFixed(1)}, Y:${pin.raw_xy[1].toFixed(1)})`;

    playChime('click');
    showToast(`📍 Destination set: ${selectedDoorstep.address} (${pin.distance_m}m)`);
  } else {
    showToast(`⚠️ Inaccessible Destination: ${pin.explanation || 'Inside building block or outside map boundaries.'}`);
    playChime('error');
  }
}

function focusGazeboSector(sectorId, buttonEl) {
  playChime('click');
  if (buttonEl) {
    document.querySelectorAll('.city-pill').forEach(b => b.classList.remove('active'));
    buttonEl.classList.add('active');
  }

  if (!gazeboMap) return;

  if (sectorId === 'DEPOT') {
    gazeboMap.selectBay({
      id: 'DEPOT_POST_OFFICE',
      customer_name: 'Central Logistics Depot Hub',
      door_xy: [-27.5, -0.75],
      stopping_xy: [-31.5, -0.75],
      approach_heading: 0.0
    });
    gazeboMap.zoom(1.8, gazeboMap.width / 2, gazeboMap.height / 2);
    showToast('Centered on Central Logistics Depot 🏢');
  } else if (gazeboMap.manifest && gazeboMap.manifest.bays) {
    const bay = gazeboMap.manifest.bays.find(b => b.id === sectorId);
    if (bay) {
      gazeboMap.selectBay(bay);
      const pt = gazeboMap.worldToScreen(bay.door_xy[0], bay.door_xy[1]);
      gazeboMap.panX += (gazeboMap.width / 2 - pt.u);
      gazeboMap.panY += (gazeboMap.height / 2 - pt.v);
      showToast(`Focused on ${bay.customer_name} Doorstep 🏠`);
    }
  }
}

function centerMapOnRover() {
  playChime('click');
  if (gazeboMap) {
    gazeboMap.centerOnRobot();
    showToast('Centered on Nexus Courier Alpha 🎯');
  }
}

function resetGazeboMapView() {
  playChime('click');
  if (gazeboMap) {
    gazeboMap.fitWorldBounds();
    showToast('View reset to full Gazebo city grid ⟲');
  }
}

function confirmDoorstepLocation() {
  playChime('success');
  showToast(`Doorstep locked! Autonomous rovers will navigate to this pin 🚀`);
  const catSection = document.getElementById('storeCatalogSection');
  if (catSection) catSection.scrollIntoView({ behavior: 'smooth' });
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
    const token = localStorage.getItem('nexus_client_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const payload = {
      customer_id: currentUser ? (currentUser.id || currentUser.customer_id || 'USR-001') : 'USR-001',
      customer_name: currentUser ? currentUser.name : 'Sophie Laurent',
      x: selectedDoorstep.stopping_x !== undefined ? selectedDoorstep.stopping_x : selectedDoorstep.x,
      y: selectedDoorstep.stopping_y !== undefined ? selectedDoorstep.stopping_y : selectedDoorstep.y,
      raw_x: selectedDoorstep.x,
      raw_y: selectedDoorstep.y,
      heading: selectedDoorstep.heading || 0.0,
      delivery_name: selectedDoorstep.address,
      delivery_address: selectedDoorstep.address,
      items: clientCart.map(c => ({ id: c.id, name: c.name, qty: c.qty })),
      priority: 1
    };

    const res = await fetch('/api/orders', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.success && (data.order || data.order_id)) {
      activeOrder = data.order || data;
      playChime('success');
      showToast(`Order ${activeOrder.order_id} Dispatched in Gazebo City! Rover En Route 🚀`);
      clientCart = [];
      updateCartUI();
      toggleCartDrawer();
      updateOrderTrackingUI(activeOrder);
      scrollToTracking();

      // Trigger map focus on the customer doorstep
      if (gazeboMap) {
        gazeboMap.selectBay({
          id: activeOrder.order_id,
          customer_name: activeOrder.delivery_name || selectedDoorstep.address,
          door_xy: [selectedDoorstep.x, selectedDoorstep.y],
          stopping_xy: [selectedDoorstep.stopping_x, selectedDoorstep.stopping_y],
          approach_heading: selectedDoorstep.heading || 0.0
        });
      }
    } else {
      throw new Error(data.error || data.message || 'Dispatch rejected by Gazebo safety validator');
    }
  } catch (err) {
    playChime('error');
    showToast(`Order Dispatch Failed: ${err.message || 'Server error'}`);
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
      if (gazeboMap) {
        gazeboMap.updateTelemetry(latestTelemetry);
      }
    }
  } catch (err) {}
}

function updateTelemetryDisplays(tel) {
  const heroSpeed = document.getElementById('heroVisualSpeed');
  if (heroSpeed) heroSpeed.textContent = `${Number(tel.actual_v || 0.0).toFixed(2)} m/s`;

  const distEl = document.getElementById('trackingDistText');
  const etaEl = document.getElementById('trackingEtaText');
  const hatchEl = document.getElementById('trackingHatchState');

  const dist = tel.dist_to_target !== undefined ? tel.dist_to_target : 0.0;
  if (distEl) distEl.textContent = `${Number(dist).toFixed(1)} m`;

  const speed = Math.max(0.1, Math.abs(tel.actual_v || 0.8));
  const etaSec = dist > 0.3 ? Math.round(dist / speed) : 0;
  const etaMin = Math.floor(etaSec / 60);
  const etaRemSec = etaSec % 60;
  if (etaEl) etaEl.textContent = dist <= 0.5 ? 'ARRIVED AT DOORSTEP' : `${String(etaMin).padStart(2, '0')} min ${String(etaRemSec).padStart(2, '0')} s`;

  if (hatchEl) {
    const isUnlocked = tel.hatch_status === 'OPEN' || (tel.hatch_angle && tel.hatch_angle > 0.1);
    hatchEl.textContent = isUnlocked ? 'UNLOCKED (60°) 🔓' : 'LOCKED 🔒';
    hatchEl.className = isUnlocked ? 'metric-value text-emerald' : 'metric-value text-amber';
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
  const code = (activeOrder && activeOrder.otp) ? activeOrder.otp : '';
  if (!code) {
    showToast('No active order OTP found to autofill.');
    return;
  }
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
    const token = localStorage.getItem('nexus_client_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch('/api/verify_otp', {
      method: 'POST',
      headers: headers,
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
      if (gazeboMap) {
        gazeboMap.updateTelemetry(latestTelemetry);
      }
      showToast('🎉 Compartment unlatched to 60°! Enjoy your delivery!');
    } else {
      playChime('error');
      if (feedback) {
        feedback.textContent = data.error || data.message || 'Incorrect verification code. Please check your order OTP.';
        feedback.className = 'otp-feedback-msg error';
      }
      setTimeout(() => {
        currentOtpBuffer = '';
        updateOtpDisplay();
      }, 900);
    }
  } catch (err) {
    playChime('error');
    if (feedback) {
      feedback.textContent = `Verification error: ${err.message || 'Network error'}`;
      feedback.className = 'otp-feedback-msg error';
    }
    setTimeout(() => {
      currentOtpBuffer = '';
      updateOtpDisplay();
    }, 1200);
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
  initGazeboMap();

  setInterval(pollTelemetry, 1000);
  pollTelemetry();
});

/**
 * NexusDelivery — Autonomous Customer Experience Engine
 * Real-time Order Tracking, E-Commerce, 2D Radar Canvas, Web Audio Synthesizer,
 * and Doorstep 6-Digit OTP Hatch Unlocking.
 */

// Global State
let currentUser = null;
let clientCart = [];
let catalogProducts = [];
let activeOrder = null;
let currentOtpBuffer = '';
let audioEnabled = true;
let audioCtx = null;
let mapAnimId = null;

// Telemetry Cache
let latestTelemetry = {
  x: -14.2,
  y: 15.0,
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
   1. WEB AUDIO SYNTHESIZER (NO EXTERNAL AUDIO FILES REQUIRED)
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
      // Triumphant OTP Unlock Major Chord
      const notes = [523.25, 659.25, 783.99, 1046.50]; // C - E - G - C
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
  } catch (err) {
    // Audio context may be blocked by browser policy until gesture
  }
}

function toggleClientAudio() {
  audioEnabled = !audioEnabled;
  const icon = document.getElementById('soundIcon');
  if (icon) icon.textContent = audioEnabled ? '🔊' : '🔇';
  showToast(audioEnabled ? 'Audio Feedback Enabled' : 'Audio Feedback Muted');
  if (audioEnabled) playChime('click');
}

/* ==========================================================================
   2. CUSTOMER AUTHENTICATION & SESSION MANAGEMENT
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
  } catch (err) {
    console.warn('Auth check offline or failed, using demo fallback:', err);
  }

  // Fallback demo user if token is present
  currentUser = {
    id: 'USR-001',
    name: 'Sophie Laurent',
    email: 'client@nexus.tn',
    phone: '+216 20 123 456',
    address: '12 North Avenue, Apt 4B',
    location_bay: 'CLIENT_1_NORTH_AVENUE'
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
    // Update recipient info in tracking section if default
    const nameEl = document.getElementById('trackingRecipientName');
    const addrEl = document.getElementById('trackingRecipientAddress');
    if (nameEl) nameEl.textContent = user.name;
    if (addrEl && user.address) addrEl.textContent = user.address;
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
      if (errorEl) errorEl.textContent = data.error || 'Authentication failed. Please check credentials.';
    }
  } catch (err) {
    console.error('Login error:', err);
    // Demo fallback login
    if (email === 'client@nexus.tn') {
      currentUser = {
        id: 'USR-001',
        name: 'Sophie Laurent',
        email: 'client@nexus.tn',
        phone: '+216 20 123 456',
        address: '12 North Avenue, Apt 4B',
        location_bay: 'CLIENT_1_NORTH_AVENUE'
      };
      localStorage.setItem('nexus_client_token', 'CUST-DEMO-TOKEN');
      renderUserAuthSlot(currentUser);
      closeAuthModal();
      playChime('success');
      showToast(`Welcome back, Sophie Laurent! (Demo Mode)`);
    } else {
      if (errorEl) errorEl.textContent = 'Server connection error. Please try again.';
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
  const location_bay = document.getElementById('regBaySelect').value;
  const errorEl = document.getElementById('registerErrorMsg');
  if (errorEl) errorEl.textContent = '';

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, phone, email, password, address, location_bay })
    });
    const data = await res.json();
    if (data.success && data.token) {
      localStorage.setItem('nexus_client_token', data.token);
      currentUser = data.user;
      renderUserAuthSlot(currentUser);
      closeAuthModal();
      playChime('success');
      showToast(`Account created! Welcome to NexusDelivery, ${currentUser.name}! 🎉`);
    } else {
      playChime('error');
      if (errorEl) errorEl.textContent = data.error || 'Registration failed. Email may already be in use.';
    }
  } catch (err) {
    console.error('Registration error:', err);
    if (errorEl) errorEl.textContent = 'Failed to submit registration. Please verify connection.';
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
   3. CATALOG & CART MANAGEMENT
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

  // Header badges
  const badge = document.getElementById('cartBadgeCount');
  const headerTotal = document.getElementById('cartHeaderTotal');
  if (badge) badge.textContent = totalCount;
  if (headerTotal) headerTotal.textContent = `$${subtotal.toFixed(2)}`;

  // Drawer items
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

  // Bill Totals
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

function onDestinationChange() {
  playChime('click');
}

async function checkoutOrder() {
  playChime('click');
  if (clientCart.length === 0) {
    showToast('Your cart is empty! Add items first.');
    return;
  }

  const select = document.getElementById('cartDestSelect');
  const custId = select ? select.value : 'CUST-001';
  const btn = document.getElementById('btnCheckoutDispatch');
  const btnText = document.getElementById('checkoutBtnText');
  const spinner = document.getElementById('checkoutSpinner');

  if (btnText) btnText.textContent = 'Dispatching Rover...';
  if (spinner) spinner.style.display = 'inline-block';
  if (btn) btn.disabled = true;

  try {
    const payload = {
      customer_id: custId,
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
      showToast(`Order ${data.order.order_id} Dispatched! Autonomous Rover En Route 🚀`);
      clientCart = [];
      updateCartUI();
      toggleCartDrawer();
      updateOrderTrackingUI(data.order);
      scrollToTracking();
    } else {
      throw new Error(data.error || 'Dispatch error');
    }
  } catch (err) {
    console.warn('Backend order dispatch failed, using simulated response:', err);
    // Simulated fallback order
    const simOrder = {
      order_id: `ORD-00${Math.floor(Math.random() * 90 + 10)}`,
      customer_id: custId,
      customer_name: currentUser ? currentUser.name : 'Sophie Laurent',
      delivery_name: 'CLIENT_1_NORTH_AVENUE',
      delivery_xy: [-14.2, 15.0],
      status: 'IN_TRANSIT',
      otp: `${Math.floor(100000 + Math.random() * 900000)}`,
      items: [...clientCart]
    };
    activeOrder = simOrder;
    playChime('success');
    showToast(`Order ${simOrder.order_id} Dispatched! Rover En Route 🚀`);
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
   4. LIVE ORDER TRACKING & RADAR CANVAS
   ========================================================================== */
function updateOrderTrackingUI(order) {
  if (!order) return;
  const badge = document.getElementById('activeOrderBadge');
  const nameEl = document.getElementById('trackingRecipientName');
  const otpDisplay = document.getElementById('displayOtpCode');
  const helperOtp = document.getElementById('helperOtpCode');

  if (badge) badge.textContent = `ORDER ${order.order_id}`;
  if (nameEl && order.customer_name) nameEl.textContent = order.customer_name;
  if (otpDisplay && order.otp) otpDisplay.textContent = order.otp;
  if (helperOtp && order.otp) helperOtp.textContent = order.otp;
}

async function pollTelemetry() {
  try {
    const [telRes, ordRes] = await Promise.all([
      fetch('/api/telemetry'),
      fetch('/api/orders')
    ]);

    if (telRes.ok) {
      latestTelemetry = await telRes.json();
      updateTelemetryDisplays(latestTelemetry);
    }
    if (ordRes.ok) {
      const orders = await ordRes.json();
      if (orders && orders.length > 0) {
        // Pick first active order or latest
        const current = orders.find(o => o.status === 'IN_TRANSIT' || o.status === 'ASSIGNED') || orders[0];
        if (current && (!activeOrder || activeOrder.order_id !== current.order_id)) {
          activeOrder = current;
          updateOrderTrackingUI(activeOrder);
        }
      }
    }
  } catch (err) {
    // Keep internal simulated movement if offline
  }
}

function updateTelemetryDisplays(tel) {
  // Update Hero visual card metrics
  const heroSpeed = document.getElementById('heroVisualSpeed');
  if (heroSpeed) heroSpeed.textContent = `${Number(tel.actual_v || 0.82).toFixed(2)} m/s`;

  // Update Tracking bar metrics
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

  // Update Stepper
  updateStepper(tel.mission_state, dist);

  // Floating map HUD
  const coordsEl = document.getElementById('hudRoverCoords');
  const speedEl = document.getElementById('hudRoverSpeed');
  const safetyEl = document.getElementById('hudRoverSafety');
  if (coordsEl) coordsEl.textContent = `X: ${Number(tel.x).toFixed(2)}, Y: ${Number(tel.y).toFixed(2)}`;
  if (speedEl) speedEl.textContent = `${Number(tel.actual_v).toFixed(2)} m/s`;
  if (safetyEl) safetyEl.textContent = tel.safety_state || 'NORMAL';
}

function updateStepper(state, dist) {
  const s1 = document.getElementById('step1');
  const s2 = document.getElementById('step2');
  const s3 = document.getElementById('step3');
  const s4 = document.getElementById('step4');

  if (!s1 || !s2 || !s3 || !s4) return;

  // Reset
  [s1, s2, s3, s4].forEach(s => s.className = 'step-item');

  if (state === 'COMPLETED' || latestTelemetry.hatch_status === 'OPEN') {
    s1.classList.add('completed');
    s2.classList.add('completed');
    s3.classList.add('completed');
    s4.classList.add('completed');
  } else if (dist < 1.5 || state === 'ARRIVED_AT_DOORSTEP' || state === 'DOORSTEP_HANDOVER') {
    s1.classList.add('completed');
    s2.classList.add('completed');
    s3.classList.add('completed');
    s4.classList.add('active');
  } else {
    s1.classList.add('completed');
    s2.classList.add('completed');
    s3.classList.add('active');
  }
}

/* ==========================================================================
   5. 2D CANVAS RADAR & TOPOLOGICAL MAP RENDERER
   ========================================================================== */
function initCanvasMaps() {
  const mainCanvas = document.getElementById('clientTrackingMapCanvas');
  const miniCanvas = document.getElementById('heroRadarMiniCanvas');

  function renderLoop() {
    if (mainCanvas) drawClientMap(mainCanvas, false);
    if (miniCanvas) drawClientMap(miniCanvas, true);
    mapAnimId = requestAnimationFrame(renderLoop);
  }
  renderLoop();
}

function drawClientMap(canvas, isMini = false) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  // Background Obsidian
  ctx.fillStyle = '#06090f';
  ctx.fillRect(0, 0, w, h);

  // Coordinate Transform: Map coordinate system (-50..50, -30..50)
  const scale = isMini ? 2.5 : 4.8;
  const cx = w / 2;
  const cy = h / 2;

  // Draw Grid Lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
  ctx.lineWidth = 1;
  const gridSize = isMini ? 25 : 35;
  for (let x = 0; x < w; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y < h; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  function toScreen(x, y) {
    return {
      sx: cx + x * scale,
      sy: cy - y * scale
    };
  }

  // Draw Sidewalk Corridors
  const sidewalks = [
    { x1: -32, y1: 0, x2: 30, y2: 0 },
    { x1: -14.2, y1: -25, x2: -14.2, y2: 40 },
    { x1: 20, y1: -20, x2: 20, y2: 35 }
  ];

  ctx.strokeStyle = 'rgba(99, 102, 241, 0.25)';
  ctx.lineWidth = isMini ? 6 : 10;
  ctx.lineCap = 'round';
  sidewalks.forEach(sw => {
    const p1 = toScreen(sw.x1, sw.y1);
    const p2 = toScreen(sw.x2, sw.y2);
    ctx.beginPath();
    ctx.moveTo(p1.sx, p1.sy);
    ctx.lineTo(p2.sx, p2.sy);
    ctx.stroke();
  });

  // Draw Depot Hub (-31.5, 2.5)
  const depotPt = toScreen(-31.5, 2.5);
  ctx.fillStyle = 'rgba(16, 185, 129, 0.2)';
  ctx.beginPath();
  ctx.arc(depotPt.sx, depotPt.sy, isMini ? 8 : 14, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#10b981';
  ctx.font = isMini ? '9px sans-serif' : '11px Outfit';
  ctx.fillText('DEPOT', depotPt.sx - 15, depotPt.sy - (isMini ? 10 : 16));

  // Draw Destination Doorstep (-14.2, 15.0)
  const destPt = toScreen(-14.2, 15.0);
  ctx.strokeStyle = 'rgba(0, 240, 255, 0.5)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(destPt.sx, destPt.sy, isMini ? 10 : 18, 0, Math.PI * 2);
  ctx.stroke();

  ctx.fillStyle = '#00f0ff';
  ctx.beginPath();
  ctx.arc(destPt.sx, destPt.sy, isMini ? 4 : 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.font = isMini ? '9px sans-serif' : '11px Outfit';
  ctx.fillText('DOORSTEP', destPt.sx - 24, destPt.sy + (isMini ? 16 : 24));

  // Draw Trail Breadcrumbs
  if (latestTelemetry.trail && latestTelemetry.trail.length > 1) {
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.4)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    latestTelemetry.trail.forEach((pt, idx) => {
      const sp = toScreen(pt[0], pt[1]);
      if (idx === 0) ctx.moveTo(sp.sx, sp.sy);
      else ctx.lineTo(sp.sx, sp.sy);
    });
    ctx.stroke();
  }

  // Draw Rover AMR (-14.2, 15.0 or current telemetry)
  const roverPt = toScreen(latestTelemetry.x || -14.2, latestTelemetry.y || 15.0);
  const yaw = latestTelemetry.yaw || 1.571;

  // Radar Pulse Rings around Rover
  const time = Date.now() * 0.003;
  const pulseR = (time % 2) * (isMini ? 12 : 22);
  ctx.strokeStyle = `rgba(0, 240, 255, ${Math.max(0, 0.6 - (pulseR / 30))})`;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(roverPt.sx, roverPt.sy, pulseR, 0, Math.PI * 2);
  ctx.stroke();

  // Rover Body (Chassis)
  ctx.save();
  ctx.translate(roverPt.sx, roverPt.sy);
  ctx.rotate(-yaw);

  // Chassis box
  const bw = isMini ? 12 : 20;
  const bh = isMini ? 18 : 28;
  ctx.fillStyle = '#07090e';
  ctx.fillRect(-bw / 2, -bh / 2, bw, bh);
  ctx.strokeStyle = '#00f0ff';
  ctx.lineWidth = 2;
  ctx.strokeRect(-bw / 2, -bh / 2, bw, bh);

  // Wheels
  ctx.fillStyle = '#38bdf8';
  ctx.fillRect(-bw / 2 - 3, -bh / 3, 3, bh / 1.5);
  ctx.fillRect(bw / 2, -bh / 3, 3, bh / 1.5);

  // Front camera beam
  ctx.fillStyle = 'rgba(0, 240, 255, 0.25)';
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(-bw, -bh * 1.4);
  ctx.lineTo(bw, -bh * 1.4);
  ctx.closePath();
  ctx.fill();

  ctx.restore();
}

function resetMapCenter() {
  playChime('click');
  showToast('Map recentered on Autonomous Rover 🎯');
}

function toggleMapRoute() {
  playChime('click');
  showToast('Sidewalk Corridors Highlighted 🛣️');
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

      // Update local telemetry hatch status
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
    console.warn('Backend OTP check failed, fallback test check:', err);
    if (code === '482910' || code === '123456' || (activeOrder && code === activeOrder.otp)) {
      playChime('success');
      if (feedback) {
        feedback.textContent = '✓ CODE CONFIRMED — HATCH UNLOCKED!';
        feedback.className = 'otp-feedback-msg success';
      }
      if (successBox) successBox.style.display = 'block';
      latestTelemetry.hatch_status = 'OPEN';
      updateTelemetryDisplays(latestTelemetry);
      showToast('🎉 Compartment unlatched to 60°! (Demo verified)');
    } else {
      playChime('error');
      if (feedback) {
        feedback.textContent = 'Incorrect 6-digit OTP. Please re-enter.';
        feedback.className = 'otp-feedback-msg error';
      }
      setTimeout(() => {
        currentOtpBuffer = '';
        updateOtpDisplay();
      }, 900);
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
  initCanvasMaps();

  // Poll telemetry every second
  setInterval(pollTelemetry, 1000);
  pollTelemetry();
});

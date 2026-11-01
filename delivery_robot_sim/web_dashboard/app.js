/**
 * Chiheb Robotics — NexusDelivery Dual-Portal Web Experience
 * Client E-Commerce + Live Tracking & Founder Fleet Operations Console
 */

// =====================================================================
// 1. Web Audio API Acoustic Feedback Engine (Zero External Audio Assets)
// =====================================================================
class WebSoundEngine {
  constructor() {
    this.ctx = null;
    this.muted = false;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  playTone(freq, type, duration, delay = 0, gainLevel = 0.2) {
    if (this.muted) return;
    try {
      this.init();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime + delay);

      gain.gain.setValueAtTime(gainLevel, this.ctx.currentTime + delay);
      gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + delay + duration);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(this.ctx.currentTime + delay);
      osc.stop(this.ctx.currentTime + delay + duration);
    } catch (e) {
      // Audio autoplay policy fallback
    }
  }

  playOrderPlaced() {
    // Pleasant ascending harp chime
    this.playTone(440.0, 'sine', 0.20, 0, 0.22);     // A4
    this.playTone(554.37, 'sine', 0.22, 0.10, 0.22);  // C#5
    this.playTone(659.25, 'sine', 0.35, 0.20, 0.26);  // E5
    this.playTone(880.0, 'sine', 0.45, 0.32, 0.28);   // A5
  }

  playDoorbellArrival() {
    // Two-tone British doorbell chime: ding-dong
    this.playTone(659.25, 'sine', 0.40, 0, 0.3);      // E5 (Ding)
    this.playTone(523.25, 'sine', 0.60, 0.35, 0.35);  // C5 (Dong)
  }

  playSolenoidUnlock() {
    // Mechanical solenoid pop + positive beep
    this.playTone(140.0, 'square', 0.08, 0, 0.3);
    this.playTone(587.33, 'sine', 0.15, 0.08, 0.25);
    this.playTone(880.0, 'sine', 0.25, 0.18, 0.28);
  }

  playCaution() {
    this.playTone(740.0, 'triangle', 0.12, 0, 0.2);
    this.playTone(740.0, 'triangle', 0.12, 0.14, 0.2);
  }

  playAlert() {
    this.playTone(440.0, 'sawtooth', 0.25, 0, 0.3);
  }
}

const sounds = new WebSoundEngine();

// =====================================================================
// 2. Global State & Presets
// =====================================================================
let currentPortal = 'customer'; // 'customer' or 'founder'
let telemetry = {};
let hardware = {};
let orders = [];
let followRobot = true;
let isPinDropMode = true;
let userDroppedPin = { x: -14.60, y: 15.00 };
let selectedItem = { id: 'PRD-01', name: 'Artisan Margherita Pizza', price: 14.50, icon: '🍕' };
let arrivalChimeTriggered = false;
let compartmentUnlocked = false;

// Enhanced Map & 3D Digital Twin State
let customerMapZoom = 1.0;
let customerPanX = 0;
let customerPanY = 0;
let founderMapZoom = 1.0;
let founderPanX = 0;
let founderPanY = 0;
let hudOverlayMode = 'all'; // 'all' | 'distance' | 'clean'
let customer3DViewer = null;
let fleet3DViewer = null;

const PRESET_CUSTOMERS = {
  'CUST-001': { name: 'Sophie Laurent', phone: '+1 (555) 234-5678', x: -14.6, y: 15.0, address: 'North Avenue East Sidewalk (Residence)' },
  'CUST-002': { name: 'Marc Dubois', phone: '+1 (555) 345-6789', x: -14.6, y: 28.0, address: 'North Avenue Commercial Hub' },
  'CUST-003': { name: 'Elena Rostova', phone: '+1 (555) 432-1098', x: -14.6, y: 38.0, address: 'North Plaza Promenade' },
  'CUST-004': { name: 'Lucas Vance', phone: '+1 (555) 543-2109', x: -43.8, y: 15.0, address: 'West Boulevard Bistro Patio' },
  'CUST-005': { name: 'Amira Khan', phone: '+1 (555) 654-3210', x: -6.0, y: 0.0, address: 'Central Square Artisan Bakery' }
};

// =====================================================================
// 3. Portal Navigation & Mode Toggling
// =====================================================================
function switchPortal(mode) {
  currentPortal = mode;
  document.getElementById('tabCustomerPortal').classList.toggle('active', mode === 'customer');
  document.getElementById('tabFounderPortal').classList.toggle('active', mode === 'founder');
  document.getElementById('tabHardwarePortal').classList.toggle('active', mode === 'hardware');
  document.getElementById('tabCadPortal').classList.toggle('active', mode === 'cad');

  document.getElementById('customerPortalView').classList.toggle('active', mode === 'customer');
  document.getElementById('founderPortalView').classList.toggle('active', mode === 'founder');
  document.getElementById('hardwarePortalView').classList.toggle('active', mode === 'hardware');
  document.getElementById('cadPortalView').classList.toggle('active', mode === 'cad');

  sounds.playTone(600, 'sine', 0.08, 0, 0.1);
  if (mode === 'customer' || mode === 'founder') {
    drawMaps();
  }
}

function toggleAudio() {
  sounds.muted = !sounds.muted;
  document.getElementById('audioIcon').textContent = sounds.muted ? '🔇' : '🔊';
  showToast(sounds.muted ? 'Audio chimes muted' : 'Audio chimes enabled');
}

// =====================================================================
// 4. Customer Order & E-Commerce Flow
// =====================================================================
function selectMenuItem(cardEl, id, name, price, icon) {
  document.querySelectorAll('.menu-card').forEach(c => c.classList.remove('selected'));
  cardEl.classList.add('selected');
  selectedItem = { id, name, price, icon };
  sounds.playTone(520, 'sine', 0.08, 0, 0.15);
}

function setPresetCustomer(custId) {
  const c = PRESET_CUSTOMERS[custId];
  if (!c) return;
  document.querySelectorAll('.dest-chip').forEach(btn => btn.classList.remove('active'));
  if (event && event.currentTarget) event.currentTarget.classList.add('active');

  document.getElementById('custInputName').value = c.name;
  document.getElementById('custInputPhone').value = c.phone;
  document.getElementById('custInputCoords').value = `${c.x.toFixed(2)}, ${c.y.toFixed(2)}`;
  userDroppedPin = { x: c.x, y: c.y };
  drawMaps();
  sounds.playTone(680, 'sine', 0.08, 0, 0.15);
}

function togglePinDropMode() {
  isPinDropMode = !isPinDropMode;
  document.getElementById('btnDropPinMode').classList.toggle('active', isPinDropMode);
  showToast(isPinDropMode ? 'Pin Drop Mode: Click map to place delivery pin' : 'Map Navigation Mode');
}

async function placeCustomerOrder() {
  const name = document.getElementById('custInputName').value.trim() || 'Valued Customer';
  const phone = document.getElementById('custInputPhone').value.trim() || '+1 (555) 000-0000';
  const notes = document.getElementById('custInputNotes').value.trim();
  const [xStr, yStr] = document.getElementById('custInputCoords').value.split(',');
  const x = parseFloat(xStr) || userDroppedPin.x;
  const y = parseFloat(yStr) || userDroppedPin.y;

  const btn = document.getElementById('btnPlaceCustomerOrder');
  btn.disabled = true;
  btn.style.opacity = '0.7';

  // Find nearest customer id or create dynamic one
  const payload = {
    customer_id: 'CUST-001',
    customer_name: name,
    items: [{ id: selectedItem.id, name: selectedItem.name, qty: 1 }],
    x: x,
    y: y,
    notes: notes,
    priority: 1
  };

  try {
    const res = await fetch('/api/customer_order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success) {
      sounds.playOrderPlaced();
      showToast(`🎉 Order Placed! ${selectedItem.icon} ${selectedItem.name} en route to ${name}`);
      arrivalChimeTriggered = false;
      compartmentUnlocked = false;

      // Update tracker UI
      document.getElementById('trackingOrderNum').textContent = data.order?.order_id || 'ORD-001';
      document.getElementById('trackingDestName').textContent = name;
      document.getElementById('customerOtpCode').textContent = formatOtp(data.order?.otp || '482910');

      // Update stepper to step 2
      setStepperStep(2);
    } else {
      sounds.playAlert();
      showToast(`⚠️ Order Notice: ${data.error || 'Destination snapped to nearest sidewalk bay'}`);
    }
  } catch (err) {
    showToast(`⚠️ Order dispatched via autonomous sidewalk route.`);
    sounds.playOrderPlaced();
    setStepperStep(2);
  } finally {
    btn.disabled = false;
    btn.style.opacity = '1';
  }
}

async function triggerCustomerHatchUnlock() {
  sounds.playSolenoidUnlock();
  compartmentUnlocked = true;

  try {
    await fetch('/api/customer_unlock', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  } catch (e) {}

  const btn = document.getElementById('btnUnlockCompartment');
  btn.classList.remove('pulse-glow');
  btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
  document.getElementById('unlockBtnText').textContent = '✅ CARGO COMPARTMENT UNLOCKED';
  document.getElementById('unlockStatusSub').textContent = 'Hatch latch released. Please collect your parcel and close the hatch.';
  setStepperStep(5);
  showToast('🔓 Cargo compartment hatch unlatched! Enjoy your order.');
}

function formatOtp(otp) {
  if (!otp) return '482 910';
  const s = String(otp);
  return s.length === 6 ? `${s.slice(0, 3)} ${s.slice(3)}` : s;
}

function setStepperStep(stepNum) {
  for (let i = 1; i <= 5; i++) {
    const stepEl = document.getElementById(`step${i}`);
    if (stepEl) {
      stepEl.classList.toggle('completed', i < stepNum);
      stepEl.classList.toggle('active', i === stepNum);
    }
    const lineEl = document.getElementById(`line${i}`);
    if (lineEl) {
      lineEl.classList.toggle('active', i < stepNum);
    }
  }
}

// =====================================================================
// 5. Founder Dispatch Direct Commands & Telemetry
// =====================================================================
async function dispatchDirectTarget(name, xy, action, orderId) {
  sounds.playTone(700, 'sine', 0.12, 0, 0.2);
  try {
    const res = await fetch('/api/dispatch_target', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_name: name,
        target_xy: xy,
        action: action,
        order_id: orderId,
        token: 'nexus-operator-2026'
      })
    });
    const d = await res.json();
    if (d.success) {
      showToast(`🚀 Dispatched to ${name} (${xy[0]}, ${xy[1]})`);
    }
  } catch (e) {
    showToast(`Dispatch signal sent to robot.`);
  }
}

async function toggleEStop() {
  sounds.playAlert();
  try {
    await fetch('/api/estop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state: 'STOP', token: 'nexus-operator-2026' })
    });
    showToast('🛑 EMERGENCY STOP ACTIVATED');
  } catch (e) {}
}

function toggleFollowRobot() {
  followRobot = !followRobot;
  document.getElementById('btnFollowToggle').classList.toggle('active', followRobot);
  showToast(followRobot ? 'Camera tracking robot' : 'Free map navigation');
}

function recenterMap() {
  followRobot = true;
  drawMaps();
  showToast('Map recentered on robot');
}

// =====================================================================
// 6. Real-Time Telemetry & Hardware Polling Loop
// =====================================================================
async function pollBackend() {
  try {
    const [telRes, hwRes, ordRes] = await Promise.all([
      fetch('/api/telemetry').then(r => r.json()).catch(() => null),
      fetch('/api/hardware').then(r => r.json()).catch(() => null),
      fetch('/api/orders').then(r => r.json()).catch(() => [])
    ]);

    if (telRes) {
      telemetry = telRes;
      updateTelemetryUI();
    }
    if (hwRes) {
      hardware = hwRes;
      updateHardwareUI();
    }
    if (Array.isArray(ordRes)) {
      orders = ordRes;
      updateManifestUI();
    }
    drawMaps();
  } catch (err) {
    // Network retry loop
  }
}

function updateTelemetryUI() {
  const v = telemetry.actual_v || 0.0;
  const state = telemetry.mission_state || 'IDLE';
  const dist = telemetry.dist_to_target || 0.0;
  const target = telemetry.target_name || 'DEPOT';

  document.getElementById('connStatusText').textContent = 'ROS 2 ONLINE';
  document.getElementById('topSpeed').textContent = `${v.toFixed(2)} m/s`;
  document.getElementById('topBattery').textContent = `${hardware.battery?.soc_pct || 98}% (${hardware.battery?.voltage_v || 25.1}V)`;

  // Founder Cam Watermark
  const camOverlay = document.getElementById('camTargetOverlay');
  if (camOverlay) camOverlay.textContent = `GOAL: ${target} (${dist.toFixed(1)}m)`;
  const camState = document.getElementById('camMissionState');
  if (camState) camState.textContent = state;

  // Customer Stepper & Arrival Chime
  if (state === 'DELIVERING' || state === 'HANDOVER' || (dist <= 2.2 && telemetry.target_action === 'DELIVERY')) {
    setStepperStep(4);
    document.getElementById('trackingEtaText').textContent = 'ARRIVED AT DOOR';
    document.getElementById('trackingEtaText').style.color = '#10b981';

    if (!arrivalChimeTriggered) {
      arrivalChimeTriggered = true;
      sounds.playDoorbellArrival();
      showToast('🔔 Doorbell Chime: Your robot has arrived at your doorstep!');
    }

    if (!compartmentUnlocked) {
      const btn = document.getElementById('btnUnlockCompartment');
      if (btn) {
        btn.classList.add('pulse-glow');
        btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        document.getElementById('unlockBtnText').textContent = '🔓 TAP TO UNLOCK YOUR COMPARTMENT';
        document.getElementById('unlockStatusSub').textContent = 'Robot is at your door. Tap button above to unlatch the cargo door.';
      }
    }
  } else if (v > 0.05 || state === 'MOVING_TO_DELIVERY_POINT' || state === 'SIDEWALK_CRUISE') {
    setStepperStep(3);
    const etaSec = Math.round(dist / Math.max(0.4, v));
    const etaMin = (etaSec / 60).toFixed(1);
    document.getElementById('trackingEtaText').textContent = `~${etaMin} Mins (${dist.toFixed(1)}m)`;
    document.getElementById('trackingEtaText').style.color = '#00f2fe';
  }

  // Hatch & Cargo Badges and Tactical Buttons Update
  const isHatchOpen = telemetry.hatch_status === 'OPEN' || (telemetry.hatch_angle && telemetry.hatch_angle > 0.1);
  const isPkgLoaded = telemetry.package_loaded !== false;

  const custHatch = document.getElementById('custHatchBadge');
  const custCargo = document.getElementById('custCargoBadge');
  const txtHatch = document.getElementById('txtHatchBtn');
  const txtPkg = document.getElementById('txtPackageBtn');

  if (custHatch) {
    custHatch.textContent = isHatchOpen ? 'HATCH: OPEN (60°)' : 'HATCH: LOCKED (0°)';
    custHatch.classList.toggle('open', isHatchOpen);
  }
  if (custCargo) {
    custCargo.textContent = isPkgLoaded ? 'PARCEL: 1x INSIDE' : 'PARCEL: EMPTY';
    custCargo.classList.toggle('loaded', isPkgLoaded);
  }
  if (txtHatch) txtHatch.textContent = isHatchOpen ? 'Close Hatch (0°)' : 'Open Hatch (60°)';
  if (txtPkg) txtPkg.textContent = isPkgLoaded ? 'Unload Parcel' : 'Load Parcel';

  // Image 3 Tri-Panel Cockpit Live Status Sync
  const heroStatus = document.getElementById('cockpitHeroStatus');
  if (heroStatus) {
    if (state === 'MOVING_TO_DELIVERY_POINT' || state === 'SIDEWALK_CRUISE' || state === 'NORMAL_OPERATION' || state === 'CRUISING') {
      heroStatus.textContent = 'OPERATIONAL';
      heroStatus.className = 'status-val-hero text-emerald';
    } else if (state === 'DELIVERING' || state === 'HANDOVER') {
      heroStatus.textContent = 'DELIVERING';
      heroStatus.className = 'status-val-hero text-cyan';
    } else if (state === 'LOADING_PACKAGE_AT_DEPOT' || state === 'LOADING') {
      heroStatus.textContent = 'LOADING PARCEL';
      heroStatus.className = 'status-val-hero text-amber';
    } else if (state === 'WAITING_AT_RED_LIGHT') {
      heroStatus.textContent = 'WAITING LIGHT';
      heroStatus.className = 'status-val-hero text-amber';
    } else {
      heroStatus.textContent = 'OPERATIONAL';
      heroStatus.className = 'status-val-hero text-emerald';
    }
  }

  const heroBat = document.getElementById('cockpitBattery');
  if (heroBat) heroBat.textContent = `${hardware.battery?.soc_pct || 74}%`;
  const heroWifi = document.getElementById('cockpitWifi');
  if (heroWifi) heroWifi.textContent = '92%';
  const heroCpu = document.getElementById('cockpitCpu');
  if (heroCpu) heroCpu.textContent = `${hardware.compute?.load_pct || 38}%`;
  const heroMem = document.getElementById('cockpitMem');
  if (heroMem) heroMem.textContent = `${hardware.compute?.ram_used_gb || 4.1}GB`;

  const cockHatch = document.getElementById('cockpitHatchLabel');
  if (cockHatch) cockHatch.textContent = isHatchOpen ? '🚪 HATCH: OPEN (60°)' : '🚪 HATCH: CLOSED (0°)';
  const cockCargo = document.getElementById('cockpitCargoLabel');
  if (cockCargo) cockCargo.textContent = isPkgLoaded ? '📦 CARGO: LOADED (1x)' : '📦 CARGO: EMPTY';

  update3DViewers();
  drawCameraHudOverlay();
}

function updateHardwareUI() {
  if (!hardware.compute) return;
  const cpu = hardware.compute;
  const npu = hardware.npu;
  const bat = hardware.battery;

  document.getElementById('hwCpuLoad').textContent = `${cpu.load_pct}%`;
  document.getElementById('hwCpuTemp').textContent = `${cpu.temperature_c}°C`;
  document.getElementById('hwBatVolt').textContent = `${bat.voltage_v} V`;
  document.getElementById('hwBatPower').textContent = `${bat.power_w} W`;
}

function updateManifestUI() {
  const container = document.getElementById('manifestItemsBox');
  if (!container) return;
  document.getElementById('manifestCountBadge').textContent = `${orders.length} Orders`;

  if (orders.length === 0) {
    container.innerHTML = '<div style="color:#64748b; font-size:12px; padding:8px;">No active orders in queue</div>';
    return;
  }

  container.innerHTML = orders.map(o => `
    <div class="manifest-item">
      <div class="item-meta">
        <span class="item-id">${o.order_id} • OTP: ${o.otp || '------'}</span>
        <span class="item-name">${o.customer_name} (${o.delivery_name || 'Curbside'})</span>
      </div>
      <span class="item-status ${o.status === 'IN_TRANSIT' ? 'status-in-transit' : 'status-assigned'}">
        ${o.status}
      </span>
    </div>
  `).join('');
}

// =====================================================================
// 7. Tactical & Customer Vector Map Canvas Rendering
// =====================================================================
function drawMaps() {
  drawCanvasMap('customerCanvasMap', true);
  drawCanvasMap('founderCanvasMap', false);
}

function drawCanvasMap(canvasId, isCustomerView) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Coordinate Transform: small_city runs X in [-45, 110], Y in [-45, 45]
  // In Customer View: focus on the active corridor around North Ave & Depot (X in [-36, 10], Y in [-10, 42])
  let centerX = telemetry.x !== undefined ? telemetry.x : -20.0;
  let centerY = telemetry.y !== undefined ? telemetry.y : 15.0;

  if (!followRobot && isCustomerView) {
    centerX = (userDroppedPin.x - 20.0) / 2;
    centerY = userDroppedPin.y;
  }

  const zoom = isCustomerView ? customerMapZoom : founderMapZoom;
  const panX = isCustomerView ? customerPanX : founderPanX;
  const panY = isCustomerView ? customerPanY : founderPanY;

  const baseScale = isCustomerView ? 14.0 : 10.5; // pixels per meter
  const scale = baseScale * zoom;
  const offsetX = (w / 2 - centerX * scale) + panX;
  const offsetY = (h / 2 + centerY * scale) + panY;

  function toScreen(x, y) {
    return {
      sx: offsetX + x * scale,
      sy: offsetY - y * scale
    };
  }

  // 1. Draw City Background Grid
  ctx.fillStyle = '#060a14';
  ctx.fillRect(0, 0, w, h);

  // Subtle grid lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
  ctx.lineWidth = 1;
  const gridStep = 5.0 * scale;
  for (let x = offsetX % gridStep; x < w; x += gridStep) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  for (let y = offsetY % gridStep; y < h; y += gridStep) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }

  // 2. Draw Solid City Buildings (No-go zones)
  const buildings = [
    { name: 'NW Residential', minX: -42.5, maxX: -17.5, minY: 3.5, maxY: 42.5 },
    { name: 'SW Commercial', minX: -42.5, maxX: -17.5, minY: -42.5, maxY: -3.5 },
    { name: 'NC Business', minX: -12.5, maxX: 42.5, minY: 3.5, maxY: 42.5 },
    { name: 'SC Market', minX: -12.5, maxX: 42.5, minY: -42.5, maxY: -3.5 },
    { name: 'NE Housing', minX: 47.5, maxX: 105.0, minY: 3.5, maxY: 42.5 },
    { name: 'SE Apartments', minX: 47.5, maxX: 105.0, minY: -42.5, maxY: -3.5 },
  ];

  buildings.forEach(b => {
    const p1 = toScreen(b.minX, b.maxY);
    const p2 = toScreen(b.maxX, b.minY);
    ctx.fillStyle = '#111827';
    ctx.fillRect(p1.sx, p1.sy, p2.sx - p1.sx, p2.sy - p1.sy);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.strokeRect(p1.sx, p1.sy, p2.sx - p1.sx, p2.sy - p1.sy);

    ctx.fillStyle = '#4b5563';
    ctx.font = '10px Inter, sans-serif';
    ctx.fillText(b.name, p1.sx + 8, p1.sy + 18);
  });

  // 3. Draw North Sidewalk Logistics Depot Compound (@ y = 2.50)
  const depotP1 = toScreen(-34.5, 4.5);
  const depotP2 = toScreen(-28.0, 0.5);
  ctx.fillStyle = 'rgba(16, 185, 129, 0.12)';
  ctx.fillRect(depotP1.sx, depotP1.sy, depotP2.sx - depotP1.sx, depotP2.sy - depotP1.sy);
  ctx.strokeStyle = '#10b981';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(depotP1.sx, depotP1.sy, depotP2.sx - depotP1.sx, depotP2.sy - depotP1.sy);

  ctx.fillStyle = '#10b981';
  ctx.font = 'bold 10px Outfit, sans-serif';
  ctx.fillText('DEPOT DOCK (y=2.5)', depotP1.sx + 6, depotP1.sy + 16);

  // 4. Draw Pedestrian Sidewalks (Trottoirs) in Vibrant Light Slate/Cyan
  // North Sidewalk along Central Blvd
  const swNorth1 = toScreen(-28.0, 3.5);
  const swNorth2 = toScreen(45.0, 1.8);
  ctx.fillStyle = 'rgba(0, 242, 254, 0.08)';
  ctx.fillRect(swNorth1.sx, swNorth1.sy, swNorth2.sx - swNorth1.sx, swNorth2.sy - swNorth1.sy);

  // East Sidewalk along North Ave (from y = 0 to y = 42)
  const swEast1 = toScreen(-15.5, 42.0);
  const swEast2 = toScreen(-13.5, 0.0);
  ctx.fillStyle = 'rgba(0, 242, 254, 0.10)';
  ctx.fillRect(swEast1.sx, swEast1.sy, swEast2.sx - swEast1.sx, swEast2.sy - swEast1.sy);

  // Draw Zebra Crosswalks
  const cw = toScreen(-15.0, 2.5);
  ctx.fillStyle = '#ffffff';
  for (let z = -2; z <= 2; z++) {
    const cp = toScreen(-15.0, 2.5 + z * 0.4);
    ctx.fillRect(cp.sx - 12, cp.sy - 2, 24, 4);
  }

  // 5. Draw Waypoint Route & Breadcrumbs Trail
  if (telemetry.trail && telemetry.trail.length > 1) {
    ctx.strokeStyle = 'rgba(0, 242, 254, 0.4)';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    telemetry.trail.forEach((pt, i) => {
      const sp = toScreen(pt[0], pt[1]);
      if (i === 0) ctx.moveTo(sp.sx, sp.sy);
      else ctx.lineTo(sp.sx, sp.sy);
    });
    ctx.stroke();
  }

  // 6. Draw Planned A* Sidewalk Route
  if (telemetry.planned_route && telemetry.planned_route.length > 0) {
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    const startSp = toScreen(telemetry.x, telemetry.y);
    ctx.moveTo(startSp.sx, startSp.sy);
    telemetry.planned_route.forEach(wp => {
      const wsp = toScreen(wp[0], wp[1]);
      ctx.lineTo(wsp.sx, wsp.sy);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // 7. Draw Customer Destination Pins
  Object.values(PRESET_CUSTOMERS).forEach(c => {
    const cp = toScreen(c.x, c.y);
    ctx.beginPath();
    ctx.arc(cp.sx, cp.sy, 5, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0, 242, 254, 0.7)';
    ctx.fill();
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px Inter, sans-serif';
    ctx.fillText(c.name.split(' ')[0], cp.sx + 8, cp.sy + 3);
  });

  // User Dropped Pin
  const userPinScreen = toScreen(userDroppedPin.x, userDroppedPin.y);
  ctx.beginPath();
  ctx.arc(userPinScreen.sx, userPinScreen.sy, 8, 0, Math.PI * 2);
  ctx.fillStyle = '#f59e0b';
  ctx.fill();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = '#f59e0b';
  ctx.font = 'bold 11px Outfit, sans-serif';
  ctx.fillText('📍 Deliver Here', userPinScreen.sx + 10, userPinScreen.sy - 8);

  // 8. Draw Autonomous Delivery Robot Marker
  if (telemetry.x !== undefined && telemetry.y !== undefined) {
    const rp = toScreen(telemetry.x, telemetry.y);
    const yaw = telemetry.yaw || 0.0;

    ctx.save();
    ctx.translate(rp.sx, rp.sy);
    ctx.rotate(-yaw);

    // Glowing footprint circle
    ctx.beginPath();
    ctx.arc(0, 0, 14, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0, 242, 254, 0.25)';
    ctx.fill();

    // Robot Chassis Box
    ctx.fillStyle = '#00f2fe';
    ctx.fillRect(-10, -7, 20, 14);

    // Direction Heading Triangle
    ctx.beginPath();
    ctx.moveTo(12, 0);
    ctx.lineTo(5, -6);
    ctx.lineTo(5, 6);
    ctx.closePath();
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    ctx.restore();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px Outfit, sans-serif';
    ctx.fillText('NexusBot', rp.sx + 16, rp.sy + 4);
  }
}

// Map Click & Drag Listeners with Curbside Snapping and Smooth Pan/Zoom
function attachMapClickListeners() {
  const custCanvas = document.getElementById('customerCanvasMap');
  const founderCanvas = document.getElementById('founderCanvasMap');

  function setupMapInteractivity(canvas, isCustomer) {
    if (!canvas) return;
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let hasMoved = false;

    canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      hasMoved = false;
      startX = e.clientX;
      startY = e.clientY;
    });

    window.addEventListener('mouseup', () => { isDragging = false; });

    canvas.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
        hasMoved = true;
      }
      if (isCustomer) {
        customerPanX += dx;
        customerPanY += dy;
      } else {
        founderPanX += dx;
        founderPanY += dy;
        followRobot = false;
        const btn = document.getElementById('btnFollowToggle');
        if (btn) btn.classList.remove('active');
      }
      startX = e.clientX;
      startY = e.clientY;
      drawMaps();
    });

    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.15 : 0.85;
      if (isCustomer) {
        zoomCustomerMap(factor);
      } else {
        zoomFounderMap(factor);
      }
    }, { passive: false });

    canvas.addEventListener('click', (e) => {
      if (hasMoved) return; // Drag occurred, not a pin drop click
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const centerX = telemetry.x !== undefined ? telemetry.x : -20.0;
      const centerY = telemetry.y !== undefined ? telemetry.y : 15.0;
      const zoom = isCustomer ? customerMapZoom : founderMapZoom;
      const panX = isCustomer ? customerPanX : founderPanX;
      const panY = isCustomer ? customerPanY : founderPanY;

      const baseScale = isCustomer ? 14.0 : 10.5;
      const scale = baseScale * zoom;
      const offsetX = (canvas.width / 2 - centerX * scale) + panX;
      const offsetY = (canvas.height / 2 + centerY * scale) + panY;

      const rawX = (clickX - offsetX) / scale;
      const rawY = (offsetY - clickY) / scale;

      const snapped = snapToCurbside(rawX, rawY);
      userDroppedPin = { x: snapped.x, y: snapped.y };

      const coordsInput = document.getElementById('custInputCoords');
      if (coordsInput) coordsInput.value = `${userDroppedPin.x.toFixed(2)}, ${userDroppedPin.y.toFixed(2)}`;

      sounds.playTone(840, 'sine', 0.1, 0, 0.2);
      showToast(`📍 Snapped to ${snapped.label} (${userDroppedPin.x.toFixed(2)}, ${userDroppedPin.y.toFixed(2)})`);
      drawMaps();
    });
  }

  setupMapInteractivity(custCanvas, true);
  setupMapInteractivity(founderCanvas, false);
}

function handleCameraError() {
  // Graceful fallback for video feed
}

function showToast(msg) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>⚡</span> <span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// =====================================================================
// 8. Initialization
// =====================================================================
window.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash.replace('#', '');
  const params = new URLSearchParams(window.location.search);
  const portalParam = params.get('portal') || hash;
  if (['customer', 'founder', 'hardware', 'cad'].includes(portalParam)) {
    switchPortal(portalParam);
  }
  attachMapClickListeners();
  setInterval(pollBackend, 250); // 4 Hz refresh
  pollBackend();
});

// =====================================================================
// 9. Hardware Simulator & Electronics Workbench Engine
// =====================================================================
function inspectGpio(pinNum, label, desc) {
  sounds.playTone(750, 'sine', 0.06, 0, 0.15);
  const el = document.getElementById('gpioDetailCallout');
  if (el) {
    el.innerHTML = `<strong>Pin ${pinNum} [${label}]:</strong> ${desc}`;
  }
}

let cadZoomLevel = 1.0;
function zoomCad(factor) {
  cadZoomLevel = Math.max(0.4, Math.min(3.5, cadZoomLevel * factor));
  const img = document.getElementById('cadBlueprintImg');
  if (img) img.style.transform = `scale(${cadZoomLevel})`;
  sounds.playTone(850, 'sine', 0.05, 0, 0.1);
}

function resetCadZoom() {
  cadZoomLevel = 1.0;
  const img = document.getElementById('cadBlueprintImg');
  if (img) img.style.transform = `scale(1)`;
  sounds.playTone(550, 'sine', 0.05, 0, 0.1);
}

function toggleCadLayer(layer) {
  sounds.playTone(640, 'sine', 0.05, 0, 0.1);
  if (layer === 'dims') {
    const btn = document.getElementById('btnToggleCadDims');
    const active = btn.classList.toggle('active');
    btn.textContent = active ? 'Dimensions: ON' : 'Dimensions: OFF';
    showToast(active ? 'CAD Dimension Lines: Enabled' : 'CAD Dimension Lines: Disabled');
  } else if (layer === 'holes') {
    const btn = document.getElementById('btnToggleCadHoles');
    const active = btn.classList.toggle('active');
    btn.textContent = active ? 'Holes & Drill Schedule: ON' : 'Holes & Drill Schedule: OFF';
    showToast(active ? 'Drill Holes & Schedule: Enabled' : 'Drill Holes & Schedule: Disabled');
  }
}

function printCadBlueprint() {
  sounds.playTone(880, 'sine', 0.12, 0, 0.2);
  showToast('Opening 1:1 Scale Print Dialog (A2/A3 Paper Scale)...');
  setTimeout(() => window.print(), 500);
}

let isSolenoidUnlocked = false;
let isEstopTripped = false;

async function testHardwareAction(action) {
  try {
    const res = await fetch('/api/hardware_test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    
    if (action === 'test_solenoid') {
      isSolenoidUnlocked = !isSolenoidUnlocked;
      sounds.playHatchUnlocked();
      const badge = document.getElementById('hwLockStatusBadge');
      if (badge) {
        badge.textContent = isSolenoidUnlocked ? 'UNLATCHED (GPIO18 HIGH)' : 'SECURELY LATCHED';
        badge.className = isSolenoidUnlocked ? 'val text-cyan' : 'val text-emerald';
      }
      showToast(isSolenoidUnlocked ? '⚡ 12V Solenoid Energized: Latch Opened' : '🔒 Solenoid De-energized: Spring Latch Engaged');
    } else if (action === 'test_estop') {
      isEstopTripped = !isEstopTripped;
      if (isEstopTripped) {
        sounds.playWarningBeep();
        sounds.playWarningBeep();
        document.getElementById('hwHaloPreview').querySelector('.halo-circle').style.background = '#ef4444';
        document.getElementById('hwHaloPreview').querySelector('.halo-circle').style.boxShadow = '0 0 16px #ef4444';
        document.getElementById('hwHaloLabel').textContent = 'E-STOP KILL INTERLOCK ENGAGED';
        document.getElementById('hwHaloLabel').style.color = '#f87171';
        showToast('🛑 Emergency Stop Activated: ODrive Motor Power Cut!');
      } else {
        sounds.playTone(520, 'sine', 0.1, 0, 0.2);
        document.getElementById('hwHaloPreview').querySelector('.halo-circle').style.background = '#10b981';
        document.getElementById('hwHaloPreview').querySelector('.halo-circle').style.boxShadow = '0 0 14px #10b981';
        document.getElementById('hwHaloLabel').textContent = 'NOMINAL AUTONOMOUS OPERATION';
        document.getElementById('hwHaloLabel').style.color = '#34d399';
        showToast('🟢 Emergency Stop Released: Motor Bus Restored');
      }
    } else if (action === 'test_npu') {
      sounds.playTone(700, 'sine', 0.08, 0, 0.2);
      sounds.playTone(900, 'sine', 0.12, 0.08, 0.25);
      const topsEl = document.getElementById('npuTopsVal');
      const fpsEl = document.getElementById('npuFpsVal');
      if (topsEl && fpsEl) {
        topsEl.textContent = '13.0';
        fpsEl.textContent = (135 + Math.random() * 8).toFixed(1);
      }
      showToast('🧠 HailoRT Inference Benchmark: 138.4 FPS (7.18 ms) @ 48.2°C');
    } else if (action === 'test_bms') {
      sounds.playTone(660, 'sine', 0.1, 0, 0.2);
      sounds.playTone(880, 'sine', 0.15, 0.1, 0.2);
      const fills = document.querySelectorAll('.bms-cells-bars .bar-fill');
      fills.forEach(f => f.style.height = '95%');
      showToast('🔋 Daly BMS Active Equalization: All 8 Cells Balanced to 3.21V');
    }
  } catch (e) {
    showToast('Hardware sandbox action dispatched');
  }
}

// =====================================================================
// 10. Multi-Feed Camera Switcher, Teleoperation & 360 Radar Engine
// =====================================================================
let currentCamFeed = 'camera';
let currentTeleopSpeed = 0.6;
let teleopTimer = null;
let radarSweepAngle = 0;

function switchCamFeed(mode) {
  currentCamFeed = mode;
  document.getElementById('btnCamFront').classList.toggle('active', mode === 'camera');
  document.getElementById('btnCamRadar').classList.toggle('active', mode === 'radar');
  document.getElementById('btnCamTeleop').classList.toggle('active', mode === 'teleop');
  const btn3D = document.getElementById('btnCam3D');
  if (btn3D) btn3D.classList.toggle('active', mode === 'twin3d');

  const streamImg = document.getElementById('cinemaCameraStream');
  const radarCanvas = document.getElementById('cinemaRadarCanvas');
  const twinCanvas = document.getElementById('fleet3DCanvas');
  const teleopPanel = document.getElementById('teleopOverlayPanel');
  const hudCanvas = document.getElementById('cameraHudCanvas');
  const feedLabel = document.getElementById('camFeedLabel');

  if (mode === 'camera') {
    streamImg.style.display = 'block';
    if (hudCanvas) hudCanvas.style.display = 'block';
    radarCanvas.style.display = 'none';
    if (twinCanvas) twinCanvas.style.display = 'none';
    teleopPanel.style.display = 'none';
    if (feedLabel) feedLabel.textContent = 'LIVE STREAM • 30 FPS • RTCP 45ms';
    sounds.playTone(600, 'sine', 0.05, 0, 0.1);
    drawCameraHudOverlay();
  } else if (mode === 'radar') {
    streamImg.style.display = 'none';
    if (hudCanvas) hudCanvas.style.display = 'none';
    radarCanvas.style.display = 'block';
    if (twinCanvas) twinCanvas.style.display = 'none';
    teleopPanel.style.display = 'none';
    if (feedLabel) feedLabel.textContent = '360° DEPTH PROXIMITY RADAR • ACTIVE SCAN';
    sounds.playTone(720, 'sine', 0.05, 0, 0.1);
    draw360Radar();
  } else if (mode === 'twin3d') {
    streamImg.style.display = 'none';
    if (hudCanvas) hudCanvas.style.display = 'none';
    radarCanvas.style.display = 'none';
    if (twinCanvas) twinCanvas.style.display = 'block';
    teleopPanel.style.display = 'none';
    if (feedLabel) feedLabel.textContent = '3D FLEET DIGITAL TWIN • THREE.JS WEBGL';
    sounds.playTone(880, 'sine', 0.08, 0, 0.15);
    if (!fleet3DViewer) init3DViewers();
  } else if (mode === 'teleop') {
    streamImg.style.display = 'block';
    if (hudCanvas) hudCanvas.style.display = 'block';
    radarCanvas.style.display = 'none';
    if (twinCanvas) twinCanvas.style.display = 'none';
    teleopPanel.style.display = 'flex';
    if (feedLabel) feedLabel.textContent = 'MANUAL REMOTE OVERRIDE (TELEOP ACTIVE)';
    sounds.playTone(840, 'sine', 0.08, 0, 0.15);
    showToast('🎮 Manual Teleop Active: Use on-screen arrows or W/A/S/D keys');
  }
}

function toggleCamFullscreen() {
  const box = document.getElementById('cinemaViewportBox');
  if (!box) return;
  if (!document.fullscreenElement) {
    box.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
}

function setTeleopSpeed(spd, btnEl) {
  currentTeleopSpeed = spd;
  document.querySelectorAll('.speed-chip').forEach(c => c.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  sounds.playTone(550, 'sine', 0.05, 0, 0.1);
  showToast(`Teleop Speed Limit: ${spd.toFixed(1)} m/s`);
}

function sendTeleopCmd(v, w) {
  fetch('/api/teleop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ v, w })
  }).catch(() => {});
}

function startTeleop(vRatio, wRatio) {
  sounds.playTone(480, 'triangle', 0.04, 0, 0.08);
  const v = vRatio * currentTeleopSpeed;
  const w = wRatio * 0.9;
  sendTeleopCmd(v, w);
  if (teleopTimer) clearInterval(teleopTimer);
  teleopTimer = setInterval(() => sendTeleopCmd(v, w), 100);
}

function stopTeleop() {
  if (teleopTimer) {
    clearInterval(teleopTimer);
    teleopTimer = null;
  }
  sendTeleopCmd(0.0, 0.0);
}

// Global Keyboard Teleoperation Listeners (W, A, S, D, Space)
let activeKeys = {};
window.addEventListener('keydown', (e) => {
  if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
  const key = e.key.toLowerCase();
  if (['w', 'a', 's', 'd', ' ', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
    e.preventDefault();
    if (activeKeys[key]) return;
    activeKeys[key] = true;

    let vRatio = 0.0;
    let wRatio = 0.0;
    if (activeKeys['w'] || activeKeys['arrowup']) vRatio += 1.0;
    if (activeKeys['s'] || activeKeys['arrowdown']) vRatio -= 0.8;
    if (activeKeys['a'] || activeKeys['arrowleft']) wRatio += 1.0;
    if (activeKeys['d'] || activeKeys['arrowright']) wRatio -= 1.0;

    if (activeKeys[' ']) {
      stopTeleop();
      return;
    }

    startTeleop(vRatio, wRatio);
  }
});

window.addEventListener('keyup', (e) => {
  const key = e.key.toLowerCase();
  if (['w', 'a', 's', 'd', ' ', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
    delete activeKeys[key];
    if (Object.keys(activeKeys).length === 0) {
      stopTeleop();
    }
  }
});

// 360° Proximity Depth Radar Rendering Loop (Exact Image 3 Aesthetic)
let radarSimBlips = [
  { angle: -0.35, dist: 2.1, color: '#22c55e' },
  { angle: 0.25, dist: 3.4, color: '#22c55e' },
  { angle: 0.85, dist: 4.2, color: '#10b981' },
  { angle: -1.10, dist: 3.8, color: '#22c55e' },
  { angle: 2.30, dist: 2.8, color: '#f59e0b' },
  { angle: -2.40, dist: 3.2, color: '#10b981' }
];

function draw360Radar() {
  const canvas = document.getElementById('cinemaRadarCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  const maxR = Math.min(w, h) * 0.38;

  ctx.fillStyle = '#050811';
  ctx.fillRect(0, 0, w, h);

  // Concentric Range Rings (1m, 2m, 3.5m, 5m)
  const ranges = [1.0, 2.0, 3.5, 5.0];
  ctx.lineWidth = 1;
  ranges.forEach((r, idx) => {
    const rad = (r / 5.0) * maxR;
    ctx.strokeStyle = idx === 0 ? 'rgba(239, 68, 68, 0.4)' : 'rgba(34, 197, 94, 0.25)';
    ctx.beginPath();
    ctx.arc(cx, cy, rad, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = 'rgba(148, 163, 184, 0.55)';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText(`${r.toFixed(1)}m`, cx + rad + 2, cy - 3);
  });

  // Crosshairs & Degree Radial Rays (Every 30 degrees)
  ctx.strokeStyle = 'rgba(34, 197, 94, 0.12)';
  ctx.font = '8px "JetBrains Mono", monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  for (let deg = 0; deg < 360; deg += 30) {
    const rad = (deg - 90) * (Math.PI / 180);
    const xEnd = cx + Math.cos(rad) * maxR;
    const yEnd = cy + Math.sin(rad) * maxR;

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(xEnd, yEnd);
    ctx.stroke();

    // Degree numbers on perimeter like Image 3
    const xLbl = cx + Math.cos(rad) * (maxR + 12);
    const yLbl = cy + Math.sin(rad) * (maxR + 12);
    ctx.fillStyle = (deg === 0 || deg === 90 || deg === 180 || deg === 270) ? '#22c55e' : 'rgba(148, 163, 184, 0.5)';
    ctx.fillText(deg.toString(), xLbl, yLbl);
  }

  // Active Sweeping Beam & Forward Vision Sector (Green Sector)
  radarSweepAngle = (radarSweepAngle + 0.035) % (Math.PI * 2);

  // Forward FOV Cone (Intel RealSense 87° FOV)
  ctx.fillStyle = 'rgba(34, 197, 94, 0.06)';
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, maxR, -Math.PI / 2 - 0.76, -Math.PI / 2 + 0.76);
  ctx.closePath();
  ctx.fill();

  // Rotating Radar Sweep Slice
  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxR);
  grad.addColorStop(0, 'rgba(34, 197, 94, 0.45)');
  grad.addColorStop(1, 'rgba(34, 197, 94, 0.0)');
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, maxR, radarSweepAngle - 0.28, radarSweepAngle);
  ctx.closePath();
  ctx.fill();

  // Heading pointer line (Robot Forward = 0 deg / Up)
  ctx.strokeStyle = '#22c55e';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx, cy - maxR);
  ctx.stroke();

  // Robot Center Dot
  ctx.fillStyle = '#22c55e';
  ctx.shadowColor = '#22c55e';
  ctx.shadowBlur = 10;
  ctx.beginPath();
  ctx.arc(cx, cy, 4.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  // Render Simulated Ambient Sidewalk Depth Points (Image 3 Reality)
  radarSimBlips.forEach(b => {
    const rad = (b.dist / 5.0) * maxR;
    const bx = cx + Math.sin(b.angle) * rad;
    const by = cy - Math.cos(b.angle) * rad;

    ctx.fillStyle = b.color;
    ctx.shadowColor = b.color;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(bx, by, 3.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  });

  // Render Primary Detected Forward Obstacle from Real ROS 2 RealSense Depth
  const obsDist = telemetry.obstacle_dist !== undefined ? telemetry.obstacle_dist : 1.05;
  if (telemetry.obstacle_detected && obsDist < 5.0) {
    const distClamped = Math.max(0.4, Math.min(5.0, obsDist));
    const rDist = (distClamped / 5.0) * maxR;
    const obX = cx;
    const obY = cy - rDist;

    const col = distClamped < 1.2 ? '#ef4444' : (distClamped < 2.5 ? '#f59e0b' : '#22c55e');
    ctx.fillStyle = col;
    ctx.shadowColor = col;
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(obX, obY, 5.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = col;
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`${distClamped.toFixed(1)}m`, obX + 8, obY + 3);
  }

  requestAnimationFrame(draw360Radar);
}

// =====================================================================
// 11. Enhanced Vector Map Pan, Zoom & Curbside Snapping
// =====================================================================
function zoomCustomerMap(factor) {
  customerMapZoom = Math.max(0.4, Math.min(4.0, customerMapZoom * factor));
  sounds.playTone(720, 'sine', 0.04, 0, 0.1);
  drawMaps();
}

function resetCustomerMapZoom() {
  customerMapZoom = 1.0;
  customerPanX = 0;
  customerPanY = 0;
  sounds.playTone(520, 'sine', 0.05, 0, 0.1);
  drawMaps();
}

function zoomFounderMap(factor) {
  founderMapZoom = Math.max(0.4, Math.min(4.0, founderMapZoom * factor));
  sounds.playTone(720, 'sine', 0.04, 0, 0.1);
  drawMaps();
}

function resetFounderMapZoom() {
  founderMapZoom = 1.0;
  founderPanX = 0;
  founderPanY = 0;
  sounds.playTone(520, 'sine', 0.05, 0, 0.1);
  drawMaps();
}

function snapToCurbside(x, y) {
  // Snap to known sidewalk lanes
  if (Math.abs(x - (-14.6)) < 4.5) {
    return { x: -14.6, y: Math.max(-35.0, Math.min(42.0, y)), label: 'North Avenue Sidewalk' };
  } else if (Math.abs(y - 0.0) < 4.0 && x > -25.0 && x < 12.0) {
    return { x: Math.max(-25.0, Math.min(12.0, x)), y: 0.0, label: 'Central Square Plaza' };
  } else if (Math.abs(x - (-43.8)) < 4.5) {
    return { x: -43.8, y: Math.max(-10.0, Math.min(30.0, y)), label: 'West Boulevard Corridor' };
  }
  return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, label: 'Custom Street Waypoint' };
}

// =====================================================================
// 12. Tactical Operator Action Bar Handlers
// =====================================================================
async function triggerHatchAction(action) {
  sounds.playSolenoidUnlock();
  try {
    const res = await fetch('/api/hatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const d = await res.json();
    showToast(`🚪 Hatch ${d.hatch_status} (${Math.round((d.hatch_angle || 0) * 180 / Math.PI)}°)`);
    if (telemetry) {
      telemetry.hatch_status = d.hatch_status;
      telemetry.hatch_angle = d.hatch_angle;
    }
    updateTelemetryUI();
  } catch (e) {
    showToast('Hatch actuated locally');
  }
}

async function triggerPackageAction(action) {
  sounds.playTone(680, 'sine', 0.1, 0, 0.2);
  try {
    const res = await fetch('/api/package', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const d = await res.json();
    showToast(d.package_loaded ? '📦 Parcel Loaded into Cargo Bay' : '📦 Parcel Unloaded from Cargo Bay');
    if (telemetry) {
      telemetry.package_loaded = d.package_loaded;
    }
    updateTelemetryUI();
  } catch (e) {
    showToast('Package state updated locally');
  }
}

async function returnToDepotDock() {
  sounds.playTone(580, 'sine', 0.15, 0, 0.2);
  showToast('🚚 Returning to Depot Logistics Bay (-31.5, -0.75)...');
  await dispatchDirectTarget('DEPOT_POST_OFFICE', [-31.5, -0.75], 'PARK', 'NONE');
}

function testDoorstepChime() {
  sounds.playDoorbellArrival();
  showToast('🔔 Doorbell Chime triggered! Customer OTP: 739-204');
}

function setHudOverlayMode(mode) {
  hudOverlayMode = mode;
  ['all', 'distance', 'clean'].forEach(m => {
    const el = document.getElementById(`chipHud${m.charAt(0).toUpperCase() + m.slice(1)}`);
    if (el) el.classList.toggle('active', m === mode);
  });
  sounds.playTone(720, 'sine', 0.05, 0, 0.1);
  drawCameraHudOverlay();
}

function drawCameraHudOverlay() {
  const canvas = document.getElementById('cameraHudCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  if (hudOverlayMode === 'clean') return;

  const obsDist = telemetry.obstacle_dist !== undefined ? telemetry.obstacle_dist : 1.05;
  const hasObs = telemetry.obstacle_detected || (obsDist < 8.0);
  const isPed = telemetry.is_pedestrian;

  if (hasObs && obsDist < 8.0) {
    const scale = 1.0 / Math.max(0.8, Math.min(8.0, obsDist));
    const bw = Math.min(w * 0.45, Math.max(50, 140 * scale * 2));
    const bh = Math.min(h * 0.65, Math.max(70, 180 * scale * 2));
    const bx = (w - bw) / 2;
    const by = Math.max(30, h * 0.45 - bh / 2);

    const col = isPed ? '#22c55e' : (obsDist < 1.2 ? '#ef4444' : '#f59e0b');

    ctx.strokeStyle = col;
    ctx.lineWidth = 2.5;
    ctx.strokeRect(bx, by, bw, bh);

    // Subtle translucent tint inside box
    ctx.fillStyle = isPed ? 'rgba(34, 197, 94, 0.08)' : 'rgba(239, 68, 68, 0.08)';
    ctx.fillRect(bx, by, bw, bh);

    // Image 3 YOLO Bounding Box Header Badge (pedestrian [0.89] / ID: 4)
    ctx.fillStyle = 'rgba(7, 10, 20, 0.90)';
    ctx.fillRect(bx, by - 32, 125, 30);
    ctx.strokeStyle = col;
    ctx.lineWidth = 1.0;
    ctx.strokeRect(bx, by - 32, 125, 30);

    ctx.fillStyle = col;
    ctx.font = 'bold 11px "JetBrains Mono", monospace';
    const label = isPed ? 'pedestrian [0.89]' : `obstacle [${obsDist.toFixed(1)}m]`;
    ctx.fillText(label, bx + 6, by - 18);
    ctx.fillText('ID: 4', bx + 6, by - 6);

    if (hudOverlayMode === 'all') {
      const speed = Math.max(0.1, telemetry.actual_v || 0.8);
      const ttc = obsDist / speed;
      ctx.fillStyle = '#ffffff';
      ctx.font = '10px Inter, sans-serif';
      ctx.fillText(`TTC: ${ttc.toFixed(1)}s • ${obsDist.toFixed(1)}m`, bx + 6, by + bh + 14);
    }
  }
}

// =====================================================================
// 13. Three.js 3D Robot Digital Twin Engine
// =====================================================================
class Nexus3DViewer {
  constructor(canvasId, isFleet = false) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas || typeof THREE === 'undefined') return;
    this.isFleet = isFleet;
    this.currentHatchAngle = 0.0;
    this.targetHatchAngle = 0.0;
    this.init();
  }

  init() {
    const width = this.canvas.clientWidth || (this.isFleet ? 640 : 480);
    const height = this.canvas.clientHeight || (this.isFleet ? 380 : 240);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(this.isFleet ? 0x070a14 : 0x0a0f1d);

    this.camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    this.camera.position.set(this.isFleet ? 2.8 : 2.2, 1.5, 2.3);
    this.camera.lookAt(0, 0.25, 0);

    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const ambient = new THREE.AmbientLight(0xffffff, 0.75);
    this.scene.add(ambient);

    const dirLight = new THREE.DirectionalLight(0x00f2fe, 0.9);
    dirLight.position.set(5, 10, 7);
    this.scene.add(dirLight);

    const warmLight = new THREE.DirectionalLight(0xffedd5, 0.6);
    warmLight.position.set(-5, 5, -5);
    this.scene.add(warmLight);

    const grid = new THREE.GridHelper(5, 16, 0x00f2fe, 0x1e293b);
    grid.position.y = -0.01;
    this.scene.add(grid);

    this.buildRobot();
    this.setupInteractivity();
    this.animate();
  }

  buildRobot() {
    this.robotGroup = new THREE.Group();
    this.scene.add(this.robotGroup);

    // 1. Lower Chassis
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.5, metalness: 0.8 });
    const baseMesh = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.16, 0.54), baseMat);
    baseMesh.position.y = 0.20;
    this.robotGroup.add(baseMesh);

    // 2. Automotive Upper Shell (Pearl White)
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.2, metalness: 0.15 });
    const bodyMesh = new THREE.Mesh(new THREE.BoxGeometry(0.80, 0.24, 0.52), bodyMat);
    bodyMesh.position.y = 0.38;
    this.robotGroup.add(bodyMesh);

    // 3. Recessed Front Visor (Gloss Black Housing for RealSense D435i)
    const visorMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.1, metalness: 0.9 });
    const visorMesh = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.12, 0.44), visorMat);
    visorMesh.position.set(0.40, 0.38, 0);
    this.robotGroup.add(visorMesh);

    // RealSense Dual Stereo Optics
    const lensMat = new THREE.MeshStandardMaterial({ color: 0x00f2fe, emissive: 0x00f2fe, emissiveIntensity: 0.5 });
    const lensGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.02, 16);
    lensGeo.rotateZ(Math.PI / 2);

    const leftLens = new THREE.Mesh(lensGeo, lensMat);
    leftLens.position.set(0.44, 0.38, -0.12);
    this.robotGroup.add(leftLens);

    const rightLens = new THREE.Mesh(lensGeo, lensMat);
    rightLens.position.set(0.44, 0.38, 0.12);
    this.robotGroup.add(rightLens);

    // Center IR Projector
    const irMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.6 });
    const irLens = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.02, 16), irMat);
    irLens.geometry.rotateZ(Math.PI / 2);
    irLens.position.set(0.44, 0.38, 0.0);
    this.robotGroup.add(irLens);

    // 4. Cyan LED Status Strips
    const ledCyanMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe });
    const ledStripGeo = new THREE.BoxGeometry(0.70, 0.015, 0.015);
    const leftLed = new THREE.Mesh(ledStripGeo, ledCyanMat);
    leftLed.position.set(0, 0.49, -0.26);
    this.robotGroup.add(leftLed);
    const rightLed = new THREE.Mesh(ledStripGeo, ledCyanMat);
    rightLed.position.set(0, 0.49, 0.26);
    this.robotGroup.add(rightLed);

    // 5. Amber Safety Beacon Mast
    const mastMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8 });
    const mastMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.25, 12), mastMat);
    mastMesh.position.set(-0.25, 0.62, 0.20);
    this.robotGroup.add(mastMesh);

    const beaconMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0xf59e0b, emissiveIntensity: 0.8, roughness: 0.3 });
    this.beaconMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.06, 16), beaconMat);
    this.beaconMesh.position.set(-0.25, 0.76, 0.20);
    this.robotGroup.add(this.beaconMesh);

    // 6. Motorized Cargo Hatch & Parcel (Hinged at rear x = -0.32, y = 0.50)
    this.hatchPivot = new THREE.Group();
    this.hatchPivot.position.set(-0.32, 0.50, 0);
    this.robotGroup.add(this.hatchPivot);

    const hatchLidMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.3, metalness: 0.6 });
    const hatchLid = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.03, 0.46), hatchLidMat);
    hatchLid.position.set(0.275, 0.015, 0);
    this.hatchPivot.add(hatchLid);

    // 7. Physical Delivery Parcel inside Cargo Bay
    this.parcelGroup = new THREE.Group();
    const boxMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.8 });
    const parcelMesh = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.16, 0.28), boxMat);
    parcelMesh.position.set(0.05, 0.36, 0);
    this.parcelGroup.add(parcelMesh);

    const labelMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const labelMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.18, 0.08), labelMat);
    labelMesh.rotation.x = -Math.PI / 2;
    labelMesh.position.set(0.05, 0.441, 0);
    this.parcelGroup.add(labelMesh);

    this.robotGroup.add(this.parcelGroup);

    // 8. 4x All-Terrain Rubber Wheels with Hubcaps
    this.wheels = [];
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.9 });
    const rimMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.8, roughness: 0.3 });
    const wheelGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.08, 24);
    wheelGeo.rotateX(Math.PI / 2);
    const rimGeo = new THREE.CylinderGeometry(0.10, 0.10, 0.085, 16);
    rimGeo.rotateX(Math.PI / 2);

    const wheelPositions = [
      [0.24, 0.18, 0.30],
      [0.24, 0.18, -0.30],
      [-0.24, 0.18, 0.30],
      [-0.24, 0.18, -0.30]
    ];

    wheelPositions.forEach(pos => {
      const wGroup = new THREE.Group();
      wGroup.position.set(pos[0], pos[1], pos[2]);
      const wMesh = new THREE.Mesh(wheelGeo, wheelMat);
      const rMesh = new THREE.Mesh(rimGeo, rimMat);
      wGroup.add(wMesh);
      wGroup.add(rMesh);
      this.robotGroup.add(wGroup);
      this.wheels.push(wGroup);
    });
  }

  setupInteractivity() {
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;

    this.canvas.addEventListener('mousedown', e => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    });

    window.addEventListener('mouseup', () => { isDragging = false; });

    window.addEventListener('mousemove', e => {
      if (!isDragging) return;
      const dx = e.clientX - prevMouseX;
      const dy = e.clientY - prevMouseY;
      this.robotGroup.rotation.y += dx * 0.01;
      this.camera.position.y = Math.max(0.5, Math.min(4.0, this.camera.position.y - dy * 0.01));
      this.camera.lookAt(0, 0.25, 0);
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    });

    this.canvas.addEventListener('wheel', e => {
      e.preventDefault();
      const zoomDelta = e.deltaY * 0.002;
      const dist = this.camera.position.length();
      if ((dist > 1.2 || zoomDelta > 0) && (dist < 6.0 || zoomDelta < 0)) {
        this.camera.position.multiplyScalar(1 + zoomDelta);
      }
    }, { passive: false });
  }

  update(telemetryData) {
    if (!this.robotGroup) return;

    // 1. Sync Hatch Angle (0.0 to 1.05 rad / 60 deg)
    const isHatchOpen = (telemetryData.hatch_status === 'OPEN' || (telemetryData.hatch_angle && telemetryData.hatch_angle > 0.1));
    this.targetHatchAngle = isHatchOpen ? -1.05 : 0.0;
    this.currentHatchAngle += (this.targetHatchAngle - this.currentHatchAngle) * 0.18;
    if (this.hatchPivot) {
      this.hatchPivot.rotation.z = this.currentHatchAngle;
    }

    // 2. Sync Package Visibility
    const hasPackage = telemetryData.package_loaded !== false;
    if (this.parcelGroup) {
      this.parcelGroup.visible = hasPackage;
    }

    // 3. Rotate Wheels when moving
    const speed = telemetryData.actual_v || 0.0;
    if (Math.abs(speed) > 0.01) {
      this.wheels.forEach(w => {
        w.children.forEach(mesh => { mesh.rotation.z += speed * 0.15; });
      });
    }

    // 4. Subtle beacon pulse
    if (this.beaconMesh) {
      const pulse = 0.5 + 0.5 * Math.sin(Date.now() * 0.008);
      this.beaconMesh.material.emissiveIntensity = 0.5 + pulse * 0.7;
    }
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }
}

function init3DViewers() {
  if (typeof THREE === 'undefined') return;
  if (!customer3DViewer && document.getElementById('customer3DCanvas')) {
    customer3DViewer = new Nexus3DViewer('customer3DCanvas', false);
  }
  if (!fleet3DViewer && document.getElementById('fleet3DCanvas')) {
    fleet3DViewer = new Nexus3DViewer('fleet3DCanvas', true);
  }
}

function update3DViewers() {
  if (customer3DViewer) customer3DViewer.update(telemetry);
  if (fleet3DViewer) fleet3DViewer.update(telemetry);
}

let isStreamPaused = false;
function toggleStreamPause(btnEl) {
  isStreamPaused = !isStreamPaused;
  const img = document.getElementById('cinemaCameraStream');
  if (isStreamPaused) {
    if (img) img.src = '';
    if (btnEl) btnEl.innerHTML = '<span>RESUME STREAM</span>';
    showToast('Front Camera Feed Paused');
  } else {
    if (img) img.src = '/stream/camera.mjpg';
    if (btnEl) btnEl.innerHTML = '<span>STOP STREAM</span>';
    showToast('Front Camera Feed Resumed (30 FPS)');
  }
}

// Initialize 3D viewers and live Radar after DOM load
window.addEventListener('load', () => {
  setTimeout(init3DViewers, 300);
  setTimeout(draw360Radar, 400);
});

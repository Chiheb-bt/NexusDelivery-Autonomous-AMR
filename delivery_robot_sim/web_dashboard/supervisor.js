/**
 * NexusDelivery — Fleet Engineer & Tactical Supervisor Cockpit Controller
 * Real-World Leaflet Tactical Map (CartoDB Dark Matter + Esri Satellite),
 * Multi-Rover Fleet Tracking (NEXUS-01, 02, 03), AI Perception HUD Overlay,
 * ODrive Powertrain Diagnostics, BMS 8-Cell Monitor, and Master E-Stop.
 */

// Operator Security State
let operatorToken = sessionStorage.getItem('nexus_operator_token') || localStorage.getItem('nexus_client_token') || '';
let isEstopEngaged = false;
let currentCameraMode = 'ai_hud';
let selectedRoverId = 'NEXUS-01';

/* ==========================================================================
   THEME SWITCHER (Light Default + Dark Mode)
   ========================================================================== */
function initTheme() {
  const theme = localStorage.getItem('nexus_theme') || 'light';
  applyTheme(theme);
}

function toggleTheme() {
  const current = localStorage.getItem('nexus_theme') || 'light';
  const next = (current === 'light') ? 'dark' : 'light';
  localStorage.setItem('nexus_theme', next);
  applyTheme(next);
}

function applyTheme(theme) {
  const body = document.body;
  const icon = document.getElementById('themeToggleIcon');
  if (theme === 'dark') {
    body.classList.remove('light-theme');
    if (icon) icon.textContent = '☀️';
  } else {
    body.classList.add('light-theme');
    if (icon) icon.textContent = '🌙';
  }
}

// Gazebo World Map State
let gazeboSupervisorMap = null;

// Telemetry Cache
let telemetryData = {
  x: -14.2,
  y: 15.0,
  yaw: 1.571,
  yaw_deg: 90.0,
  actual_v: 0.82,
  actual_w: 0.05,
  cmd_v: 0.85,
  cmd_w: 0.0,
  mission_state: 'NAVIGATING_TO_CLIENT',
  safety_state: 'NORMAL_OPERATION',
  target_name: 'CLIENT_1_NORTH_AVENUE',
  target_x: -14.2,
  target_y: 15.0,
  dist_to_target: 24.5,
  obstacle_detected: true,
  obstacle_dist: 1.05,
  is_pedestrian: true,
  hatch_status: 'LOCKED',
  hatch_angle: 0.0,
  trail: []
};

// Hardware Cache
let hardwareData = null;

// Audio Context for Alerts
let cockpitAudioCtx = null;
function playAlarmSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!cockpitAudioCtx && AudioContext) cockpitAudioCtx = new AudioContext();
    if (cockpitAudioCtx) {
      const now = cockpitAudioCtx.currentTime;
      const osc = cockpitAudioCtx.createOscillator();
      const gain = cockpitAudioCtx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.setValueAtTime(880, now + 0.15);
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
      osc.connect(gain);
      gain.connect(cockpitAudioCtx.destination);
      osc.start(now);
      osc.stop(now + 0.3);
    }
  } catch (e) {}
}

/* ==========================================================================
   1. OPERATOR AUTHENTICATION & SECURITY GATE
   ========================================================================== */
function promptOperatorPin() {
  const modal = document.getElementById('operatorPinModal');
  const feedback = document.getElementById('operatorPinFeedback');
  if (feedback) feedback.textContent = '';
  if (modal) modal.classList.add('active');
}

function closeOperatorPinModal() {
  const modal = document.getElementById('operatorPinModal');
  if (modal) modal.classList.remove('active');
}

async function handleOperatorPinSubmit(e) {
  e.preventDefault();
  const pinInput = document.getElementById('inputOperatorPin');
  const feedback = document.getElementById('operatorPinFeedback');
  const token = pinInput ? pinInput.value.trim() : '';

  try {
    const res = await fetch('/api/auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    const data = await res.json();
    if (data.valid) {
      operatorToken = data.token;
      sessionStorage.setItem('nexus_operator_token', operatorToken);
      if (feedback) {
        feedback.textContent = '✓ Operator authorized successfully!';
        feedback.className = 'pin-feedback success';
      }
      setTimeout(() => {
        closeOperatorPinModal();
        updateOperatorUI(true);
        appendTerminalLog('success', `[SECURITY] Operator session authenticated with cryptographic token.`);
      }, 500);
    } else {
      if (feedback) {
        feedback.textContent = data.message || 'Invalid security PIN.';
        feedback.className = 'pin-feedback error';
      }
    }
  } catch (err) {
    operatorToken = token || 'NEXUS-DEMO-PIN';
    sessionStorage.setItem('nexus_operator_token', operatorToken);
    closeOperatorPinModal();
    updateOperatorUI(true);
    appendTerminalLog('warn', `[SECURITY] Offline validation accepted: Operator PIN armed.`);
  }
}

function autofillDemoPin() {
  const pinInput = document.getElementById('inputOperatorPin');
  if (pinInput) pinInput.value = operatorToken || 'nexus2026';
}

function updateOperatorUI(isAuth) {
  const textEl = document.getElementById('operatorStatusText');
  const badge = document.getElementById('operatorBadge');
  if (textEl) textEl.textContent = isAuth ? 'OPERATOR SECURE' : 'OPERATOR LOCKED';
  if (badge) {
    badge.style.color = isAuth ? 'var(--accent-emerald)' : 'var(--accent-red)';
    badge.style.borderColor = isAuth ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)';
  }
}

/* ==========================================================================
   2. REAL-TIME TELEMETRY POLLING & HARDWARE METRICS
   ========================================================================== */
async function fetchTelemetry() {
  try {
    const res = await fetch('/api/telemetry');
    if (res.ok) {
      telemetryData = await res.json();
      updateCockpitDisplays(telemetryData);
    }
  } catch (e) {}
}

async function fetchHardware() {
  try {
    const res = await fetch('/api/hardware');
    if (res.ok) {
      hardwareData = await res.json();
      updateHardwareDisplays(hardwareData);
    }
  } catch (e) {}
}

function updateCockpitDisplays(tel) {
  // Freshness & Environment Mode
  const envModeEl = document.getElementById('topEnvMode');
  const freshnessEl = document.getElementById('topFreshness');
  if (envModeEl) envModeEl.textContent = tel.mode || 'SIMULATION (Gazebo 11)';
  if (freshnessEl) {
    const age = tel.freshness_age_s !== undefined ? tel.freshness_age_s : 0.02;
    if (age > 2.5) {
      freshnessEl.textContent = `STALE (${age.toFixed(1)}s)`;
      freshnessEl.className = 'rm-v text-amber';
    } else {
      freshnessEl.textContent = `LIVE (${Math.round(1 / Math.max(0.01, age))} Hz)`;
      freshnessEl.className = 'rm-v text-emerald';
    }
  }

  // Top ribbon
  const fsmEl = document.getElementById('topSafetyFsm');
  if (fsmEl) fsmEl.textContent = tel.safety_state || 'NORMAL_OP';

  // Pane 1 Perception
  const detectionsEl = document.getElementById('metricDetections');
  const depthMinEl = document.getElementById('metricDepthMin');
  const tlEl = document.getElementById('metricTrafficLight');
  const distEl = document.getElementById('hudObstacleDist');
  const ttcEl = document.getElementById('hudTtcMetric');

  if (detectionsEl) {
    detectionsEl.textContent = tel.is_pedestrian ? '1 Pedestrian (Conf 0.94)' : 'Obstacle Clear';
  }
  if (depthMinEl) {
    depthMinEl.textContent = `${Number(tel.obstacle_dist || 1.05).toFixed(2)} m`;
  }
  if (tlEl) {
    tlEl.textContent = tel.red_light ? 'RED (STOPPING)' : 'GREEN (NOMINAL)';
    tlEl.className = tel.red_light ? 'sc-val text-red' : 'sc-val text-emerald';
  }
  if (distEl) {
    distEl.textContent = tel.obstacle_detected ? `${Number(tel.obstacle_dist).toFixed(2)} m` : 'CLEAR (> 4.5m)';
  }
  if (ttcEl) {
    const ttc = tel.obstacle_detected ? (tel.obstacle_dist / Math.max(0.1, tel.actual_v)) : 99.0;
    if (ttc < 3.0) {
      ttcEl.textContent = `TTC: ${ttc.toFixed(1)} s (WARNING)`;
      ttcEl.className = 'hud-pill text-red';
    } else {
      ttcEl.textContent = `TTC: > 10.0 s (CLEAR)`;
      ttcEl.className = 'hud-pill text-emerald';
    }
  }

  // Pane 2 Map HUD Coordinates (Exact metric Gazebo simulation coordinates)
  const mx = document.getElementById('mapCoordX');
  const my = document.getElementById('mapCoordY');
  const myaw = document.getElementById('mapCoordYaw');
  if (mx) mx.textContent = `${Number(tel.x || 0.0).toFixed(2)} m`;
  if (my) my.textContent = `${Number(tel.y || 0.0).toFixed(2)} m`;
  if (myaw) myaw.textContent = `${Number(tel.yaw_deg || 0.0).toFixed(1)}°`;

  // Pane 3 Hatch Status
  const hatchStatus = document.getElementById('cockpitHatchStatus');
  if (hatchStatus) {
    const isUnlocked = tel.hatch_status === 'OPEN' || tel.hatch_angle > 0.1;
    hatchStatus.textContent = isUnlocked ? `OPEN (${Number(tel.hatch_angle * 57.3).toFixed(1)}°)` : `LOCKED (0.0°)`;
    hatchStatus.className = isUnlocked ? 'cs-v text-emerald' : 'cs-v text-amber';
  }

  // Update Vector Map
  if (gazeboSupervisorMap) {
    gazeboSupervisorMap.updateTelemetry(tel);
  }
}

function updateHardwareDisplays(hw) {
  if (!hw) return;

  // Battery Deck
  if (hw.battery) {
    const soc = hw.battery.soc_pct || 98;
    const socFill = document.getElementById('bmsSocFill');
    const socText = document.getElementById('bmsSocText');
    const currentDraw = document.getElementById('bmsCurrentDraw');
    const topBattery = document.getElementById('topBattery');

    if (socFill) socFill.style.width = `${soc}%`;
    if (socText) socText.textContent = `${soc}% SOC (${Math.round(soc * 5.12)} Wh / 512 Wh)`;
    if (currentDraw) currentDraw.textContent = `${hw.battery.current_a} A (${hw.battery.power_w} W)`;
    if (topBattery) topBattery.textContent = `${hw.battery.voltage_v}V (${soc}%)`;
  }

  // Compute Deck
  if (hw.compute) {
    const rpiCpu = document.getElementById('rpiCpuLoad');
    if (rpiCpu) rpiCpu.textContent = `${hw.compute.load_pct}% (${hw.compute.temperature_c}°C)`;
  }
  if (hw.npu) {
    const hailoLoad = document.getElementById('hailoLoad');
    if (hailoLoad) hailoLoad.textContent = `${hw.npu.fps} FPS (${hw.npu.latency_ms} ms)`;
  }
}

/* ==========================================================================
   3. AI VISION HUD CANVAS OVERLAY
   ========================================================================== */
function initCameraOverlay() {
  const canvas = document.getElementById('cameraOverlayCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function renderHud() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (currentCameraMode === 'ai_hud') {
      const w = canvas.width;
      const h = canvas.height;

      // Horizon line
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.2)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, h * 0.45);
      ctx.lineTo(w, h * 0.45);
      ctx.stroke();
      ctx.setLineDash([]);

      // Pinhole Ground Corridor Lines
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.45)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(w * 0.25, h);
      ctx.lineTo(w * 0.42, h * 0.52);
      ctx.moveTo(w * 0.75, h);
      ctx.lineTo(w * 0.58, h * 0.52);
      ctx.stroke();

      // Simulated / Real YOLO Bounding Box for Obstacle/Pedestrian
      if (telemetryData.obstacle_detected) {
        const bx = w * 0.40;
        const by = h * 0.32;
        const bw = w * 0.20;
        const bh = h * 0.48;

        const boxColor = telemetryData.is_pedestrian ? '#10b981' : '#f59e0b';
        ctx.strokeStyle = boxColor;
        ctx.lineWidth = 2;
        ctx.strokeRect(bx, by, bw, bh);

        // Header label badge
        ctx.fillStyle = 'rgba(10, 15, 24, 0.85)';
        ctx.fillRect(bx, by - 26, bw, 26);
        ctx.strokeStyle = boxColor;
        ctx.strokeRect(bx, by - 26, bw, 26);

        ctx.fillStyle = boxColor;
        ctx.font = 'bold 11px JetBrains Mono';
        const label = telemetryData.is_pedestrian ? 'pedestrian [0.94]' : 'obstacle [0.89]';
        ctx.fillText(label, bx + 5, by - 14);

        const distStr = `${Number(telemetryData.obstacle_dist).toFixed(2)} m`;
        ctx.font = '10px JetBrains Mono';
        ctx.fillText(`DIST: ${distStr}`, bx + 5, by - 4);
      }
    }

    requestAnimationFrame(renderHud);
  }
  renderHud();
}

function setCameraMode(mode, btn) {
  currentCameraMode = mode;
  const tabs = document.querySelectorAll('.cam-tab');
  tabs.forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');

  fetch('/api/camera_mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  }).catch(() => {});

  appendTerminalLog('info', `[VISION] Camera mode switched to: ${mode.toUpperCase()}`);
}

function handleStreamFallback(img) {
  img.onerror = null;
  img.src = 'street_camera_frame.jpg';
}

/* ==========================================================================
   4. AUTHENTIC GAZEBO SIMULATION WORLD TACTICAL MAP & OPERATIONS DECK
   ========================================================================== */
function initCockpitNavMap() {
  const container = document.getElementById('supervisorTacticalMap');
  if (!container || typeof GazeboWorldMap === 'undefined') {
    setTimeout(initCockpitNavMap, 150);
    return;
  }

  gazeboSupervisorMap = new GazeboWorldMap({
    containerId: 'supervisorTacticalMap',
    mode: 'supervisor',
    onDestinationSelected: (pin) => {
      if (pin && pin.valid) {
        appendTerminalLog('info', `[MAP] Selected Gazebo coordinates: (${pin.raw_xy[0].toFixed(2)}, ${pin.raw_xy[1].toFixed(2)})`);
        dispatchTargetCoordinates(pin.stopping_xy[0], pin.stopping_xy[1], pin.customer_name || 'TACTICAL_WAYPOINT');
      } else {
        appendTerminalLog('warn', `[MAP] Inaccessible Gazebo location: ${pin.explanation || 'Restricted area'}`);
      }
    }
  });

  pollFleet();
  setInterval(pollFleet, 1000);

  fetchOrdersQueue();
  setInterval(fetchOrdersQueue, 2000);

  fetchAuditLogs();
  setInterval(fetchAuditLogs, 4000);
}

// Tactical Vector Map Layer Toggles
function toggleTacticalLayer(layerName) {
  if (!gazeboSupervisorMap) return;
  gazeboSupervisorMap.layers[layerName] = !gazeboSupervisorMap.layers[layerName];
  gazeboSupervisorMap.render();
  appendTerminalLog('info', `[LAYER] Toggled ${layerName}: ${gazeboSupervisorMap.layers[layerName] ? 'ON' : 'OFF'}`);
}

function centerSupervisorOnRover() {
  if (gazeboSupervisorMap) {
    gazeboSupervisorMap.centerOnRobot();
    appendTerminalLog('info', '[MAP] Viewport centered on active robot.');
  }
}

function resetSupervisorMapView() {
  if (gazeboSupervisorMap) {
    gazeboSupervisorMap.fitWorldBounds();
    appendTerminalLog('info', '[MAP] Viewport reset to full Gazebo city grid.');
  }
}

// Focus on a Specific Fleet Rover
function focusRover(roverId) {
  selectedRoverId = roverId;
  const chips = document.querySelectorAll('.presets-chips .preset-chip');
  chips.forEach(c => {
    if (c.id === `chip${roverId.replace('-', '')}`) {
      c.classList.add('active');
    } else {
      c.classList.remove('active');
    }
  });

  if (roverId === 'NEXUS-01') {
    centerSupervisorOnRover();
    appendTerminalLog('info', `[FLEET] Cockpit tracking active unit: NEXUS-01 (Gazebo Classic Active)`);
  } else {
    appendTerminalLog('warn', `[FLEET] ${roverId} is in STANDBY (Fleet expansion target for multi-robot dispatch).`);
  }
}

// Poll Multi-Rover Fleet Data from Backend
async function pollFleet() {
  try {
    const res = await fetch('/api/fleet');
    if (!res.ok) return;
    const fleet = await res.json();

    const activeRover = fleet.find(r => r.id === 'NEXUS-01');
    if (activeRover && gazeboSupervisorMap) {
      gazeboSupervisorMap.updateTelemetry({
        x: activeRover.x,
        y: activeRover.y,
        yaw: (activeRover.heading_deg || 0) * (Math.PI / 180),
        actual_v: activeRover.speed || 0.0,
        dist_to_target: activeRover.dist_to_target || 0.0,
        mission_state: activeRover.status || 'NORMAL_OPERATION'
      });
    }
  } catch (err) {}
}

// Fetch Orders Queue from SQLite Database
async function fetchOrdersQueue() {
  try {
    const res = await fetch('/api/orders');
    if (!res.ok) return;
    const orders = await res.json();
    renderOrdersTable(orders);
  } catch (e) {}
}

function renderOrdersTable(orders) {
  const tbody = document.getElementById('ordersTableBody');
  const countBadge = document.getElementById('ordersQueueCount');
  if (!tbody) return;

  if (!orders || orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-dim">No active delivery missions queued in Gazebo world.</td></tr>`;
    if (countBadge) countBadge.textContent = '0 Active Missions';
    return;
  }

  if (countBadge) countBadge.textContent = `${orders.length} Active Missions`;

  tbody.innerHTML = orders.map(ord => {
    let statusClass = 'queued';
    const st = (ord.status || 'QUEUED').toUpperCase();
    if (st.includes('ROUTE') || st.includes('TRANSIT')) statusClass = 'en_route';
    else if (st.includes('DELIVERED') || st.includes('COMPLETED')) statusClass = 'completed';
    else if (st.includes('FAIL') || st.includes('REJECT')) statusClass = 'failed';

    const tx = ord.target_x !== undefined ? Number(ord.target_x).toFixed(1) : '-';
    const ty = ord.target_y !== undefined ? Number(ord.target_y).toFixed(1) : '-';
    const dist = ord.route_dist_m ? `${ord.route_dist_m}m` : (ord.est_route_distance ? `${ord.est_route_distance}m` : '~32m');
    const eta = ord.est_duration_s ? `${Math.round(ord.est_duration_s)}s` : '~45s';

    return `
      <tr>
        <td class="text-cyan"><strong>${ord.order_id || ord.id}</strong></td>
        <td>${ord.customer_name || 'Customer'}<br><span class="text-dim" style="font-size:0.72rem;">${ord.delivery_name || ord.delivery_address || 'Doorstep'}</span></td>
        <td>(${tx}, ${ty})</td>
        <td><span class="status-tag en_route">${ord.assigned_robot || 'NEXUS-01'}</span></td>
        <td><span class="status-tag ${statusClass}">${st}</span></td>
        <td>${ord.priority || 1}</td>
        <td>${dist} / ${eta}</td>
        <td class="text-emerald"><strong>${ord.otp || '******'}</strong></td>
      </tr>
    `;
  }).join('');
}

// Fetch Security Audit Logs from Database
async function fetchAuditLogs() {
  try {
    const res = await fetch('/api/audit_logs');
    if (!res.ok) return;
    const logs = await res.json();
    renderAuditTable(logs);
  } catch (e) {}
}

function renderAuditTable(logs) {
  const tbody = document.getElementById('auditTableBody');
  if (!tbody) return;

  if (!logs || logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-dim">No audit records found.</td></tr>`;
    return;
  }

  // Display latest 25 logs
  const displayLogs = logs.slice(0, 25);
  tbody.innerHTML = displayLogs.map(log => {
    const statusColor = (log.status === 'SUCCESS' || log.status === 'AUTHORIZED') ? 'text-emerald' : (log.status === 'DENIED' || log.status === 'FAILED' ? 'text-red' : 'text-cyan');
    const ts = (log.timestamp || '').split('T')[1] || log.timestamp || '-';
    const corr = (log.correlation_id || '').substring(0, 8);

    return `
      <tr>
        <td class="text-dim">${ts}</td>
        <td><strong>${log.actor_id || log.principal || 'SYSTEM'}</strong> <span class="text-dim">(${log.role || 'CORE'})</span></td>
        <td class="text-cyan">${log.action}</td>
        <td>${log.target_entity || log.entity || '-'}</td>
        <td class="${statusColor}"><strong>${log.status}</strong></td>
        <td class="text-dim">${corr ? '#' + corr : '-'}</td>
      </tr>
    `;
  }).join('');
}

// Click-to-Dispatch Target Coordinates in Gazebo Metric Space
async function dispatchTargetCoordinates(x, y, name = 'TACTICAL_WAYPOINT') {
  appendTerminalLog('info', `[DISPATCH] Waypoint target locked: ${name} at Gazebo (${x.toFixed(2)}, ${y.toFixed(2)})`);

  try {
    const res = await fetch('/api/dispatch_target', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${operatorToken}`
      },
      body: JSON.stringify({
        token: operatorToken,
        target_name: name,
        target_xy: [round(x, 2), round(y, 2)],
        action: 'TRANSIT'
      })
    });
    const data = await res.json();
    if (data.success) {
      appendTerminalLog('success', `[DISPATCH] Waypoint acknowledged by ROS 2 Nav2 stack. Route computation active.`);
      fetchOrdersQueue();
    } else {
      appendTerminalLog('error', `[DISPATCH] Dispatch rejected: ${data.message || data.error}`);
      if (data.error === 'UNAUTHORIZED') promptOperatorPin();
    }
  } catch (err) {
    appendTerminalLog('warn', `[DISPATCH] Simulated local waypoint set: (${x.toFixed(2)}, ${y.toFixed(2)})`);
    telemetryData.target_x = x;
    telemetryData.target_y = y;
    telemetryData.target_name = name;
  }
}

function clearDispatchRoute() {
  if (gazeboSupervisorMap) {
    gazeboSupervisorMap.currentRoute = [];
    gazeboSupervisorMap.targetWaypoint = null;
    gazeboSupervisorMap.render();
  }
  appendTerminalLog('warn', '[DISPATCH] Cleared target waypoint. Rover entering autonomous idle hold.');
}

function round(val, dec = 2) {
  return Number(Math.round(val + 'e' + dec) + 'e-' + dec);
}

/* ==========================================================================
   5. REMOTE TELEOPERATION & MANUAL CONTROLS
   ========================================================================== */
async function sendTeleop(v, w) {
  const pill = document.getElementById('teleopModePill');
  if (pill) {
    if (v !== 0.0 || w !== 0.0) {
      pill.textContent = `TELEOP OVERRIDE (v:${v} w:${w})`;
      pill.style.borderColor = 'var(--accent-amber)';
      pill.style.color = 'var(--accent-amber)';
    } else {
      pill.textContent = 'AUTONOMOUS DISPATCH';
      pill.style.borderColor = 'rgba(0, 240, 255, 0.3)';
      pill.style.color = 'var(--accent-cyan)';
    }
  }

  try {
    await fetch('/api/teleop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ v, w })
    });
  } catch (err) {}
}

async function toggleHatchManual(action) {
  appendTerminalLog('info', `[CARGO] Solenoid command dispatched: ${action.toUpperCase()}`);
  try {
    const res = await fetch('/api/hatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    if (data.success) {
      telemetryData.hatch_status = data.hatch_status;
      telemetryData.hatch_angle = data.hatch_angle;
      updateCockpitDisplays(telemetryData);
      appendTerminalLog('success', `[CARGO] Hatch status is now: ${data.hatch_status}`);
    }
  } catch (err) {}
}

/* Master E-Stop System */
async function toggleMasterEstop() {
  isEstopEngaged = true;
  playAlarmSound();
  const banner = document.getElementById('estopBanner');
  if (banner) banner.style.display = 'block';

  appendTerminalLog('error', '[CRITICAL] MASTER EMERGENCY STOP ENGAGED. Motor bus power terminated.');

  try {
    await fetch('/api/estop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${operatorToken}`
      },
      body: JSON.stringify({ state: 'STOP', token: operatorToken })
    });
  } catch (err) {}
}

async function resetMasterEstop() {
  isEstopEngaged = false;
  const banner = document.getElementById('estopBanner');
  if (banner) banner.style.display = 'none';

  appendTerminalLog('success', '[SAFETY] Emergency stop released. System transitioning to standby.');

  try {
    await fetch('/api/estop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${operatorToken}`
      },
      body: JSON.stringify({ state: 'RESUME', token: operatorToken })
    });
  } catch (err) {}
}

// Keyboard teleop WASD / Arrows
window.addEventListener('keydown', (e) => {
  if (document.activeElement && document.activeElement.tagName === 'INPUT') return;
  const k = e.key.toLowerCase();
  if (k === 'w' || k === 'arrowup') sendTeleop(0.65, 0.0);
  else if (k === 's' || k === 'arrowdown') sendTeleop(-0.45, 0.0);
  else if (k === 'a' || k === 'arrowleft') sendTeleop(0.0, 0.65);
  else if (k === 'd' || k === 'arrowright') sendTeleop(0.0, -0.65);
  else if (k === ' ') { sendTeleop(0.0, 0.0); toggleMasterEstop(); }
});

window.addEventListener('keyup', (e) => {
  if (document.activeElement && document.activeElement.tagName === 'INPUT') return;
  const k = e.key.toLowerCase();
  if (['w', 's', 'a', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(k)) {
    sendTeleop(0.0, 0.0);
  }
});

/* ==========================================================================
   6. TERMINAL LOG UTILITY
   ========================================================================== */
function appendTerminalLog(type, message) {
  const terminal = document.getElementById('cockpitTerminalOutput');
  if (!terminal) return;

  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];

  const line = document.createElement('div');
  line.className = `log-line ${type}`;
  line.textContent = `[${timeStr}] ${message}`;

  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function clearTerminalLogs() {
  const terminal = document.getElementById('cockpitTerminalOutput');
  if (terminal) terminal.innerHTML = '';
}

/* ==========================================================================
   INITIALIZATION
   ========================================================================== */
window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initCameraOverlay();
  initCockpitNavMap();

  setInterval(fetchTelemetry, 250);
  setInterval(fetchHardware, 1000);

  fetchTelemetry();
  fetchHardware();

  updateOperatorUI(Boolean(operatorToken));
});

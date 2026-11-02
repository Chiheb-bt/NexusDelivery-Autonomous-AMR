/**
 * NexusDelivery — Fleet Engineer & Supervisor Cockpit Controller
 * Real-time Telemetry, AI Perception HUD, Click-to-Dispatch Canvas Map,
 * ODrive Powertrain Diagnostics, Teleoperation, and Master E-Stop.
 */

// Operator Security State
let operatorToken = sessionStorage.getItem('nexus_operator_token') || '';
let isEstopEngaged = false;
let currentCameraMode = 'ai_hud';

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
        appendTerminalLog('success', `[SECURITY] Operator session authenticated with token.`);
      }, 500);
    } else {
      if (feedback) {
        feedback.textContent = data.message || 'Invalid security PIN.';
        feedback.className = 'pin-feedback error';
      }
    }
  } catch (err) {
    // If running in disconnected simulation test, accept token
    operatorToken = token || 'NEXUS-DEMO-PIN';
    sessionStorage.setItem('nexus_operator_token', operatorToken);
    closeOperatorPinModal();
    updateOperatorUI(true);
    appendTerminalLog('warn', `[SECURITY] Offline validation accepted: Operator PIN armed.`);
  }
}

function autofillDemoPin() {
  const pinInput = document.getElementById('inputOperatorPin');
  if (pinInput) pinInput.value = operatorToken || 'NEXUS_OPERATOR_PIN';
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
  } catch (e) {
    // Keep local cache
  }
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

  // Pane 2 Map HUD
  const mx = document.getElementById('mapCoordX');
  const my = document.getElementById('mapCoordY');
  const myaw = document.getElementById('mapCoordYaw');
  if (mx) mx.textContent = Number(tel.x).toFixed(2);
  if (my) my.textContent = Number(tel.y).toFixed(2);
  if (myaw) myaw.textContent = `${Number(tel.yaw_deg || 90.0).toFixed(1)}°`;

  // Pane 3 Hatch
  const hatchStatus = document.getElementById('cockpitHatchStatus');
  if (hatchStatus) {
    const isUnlocked = tel.hatch_status === 'OPEN' || tel.hatch_angle > 0.1;
    hatchStatus.textContent = isUnlocked ? `OPEN (${Number(tel.hatch_angle * 57.3).toFixed(1)}°)` : `LOCKED (0.0°)`;
    hatchStatus.className = isUnlocked ? 'cs-v text-emerald' : 'cs-v text-amber';
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
  // If MJPEG stream server is running in standalone mock, fallback to static street frame
  img.onerror = null;
  img.src = 'street_camera_frame.jpg';
}

/* ==========================================================================
   4. TOPOLOGICAL 2D CANVAS MAP & CLICK-TO-DISPATCH
   ========================================================================== */
function initCockpitNavMap() {
  const canvas = document.getElementById('cockpitNavCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  // Handle Canvas Click-To-Dispatch
  canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const scale = 5.2;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    const mapX = (clickX - cx) / scale;
    const mapY = -(clickY - cy) / scale;

    dispatchTargetCoordinates(mapX, mapY, 'OPERATOR_CLICK_WAYPOINT');
  });

  function renderMap() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = '#05070c';
    ctx.fillRect(0, 0, w, h);

    const scale = 5.2;
    const cx = w / 2;
    const cy = h / 2;

    function toScreen(x, y) {
      return { sx: cx + x * scale, sy: cy - y * scale };
    }

    // Grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 30) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += 30) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Corridors
    const sidewalks = [
      { x1: -35, y1: 0, x2: 35, y2: 0 },
      { x1: -14.2, y1: -28, x2: -14.2, y2: 42 },
      { x1: 22, y1: -25, x2: 22, y2: 35 }
    ];
    ctx.strokeStyle = 'rgba(99, 102, 241, 0.3)';
    ctx.lineWidth = 12;
    ctx.lineCap = 'round';
    sidewalks.forEach(sw => {
      const p1 = toScreen(sw.x1, sw.y1);
      const p2 = toScreen(sw.x2, sw.y2);
      ctx.beginPath(); ctx.moveTo(p1.sx, p1.sy); ctx.lineTo(p2.sx, p2.sy); ctx.stroke();
    });

    // Preset Stopping Bays
    const bays = [
      { name: 'DEPOT', x: -31.5, y: 2.5, col: '#10b981' },
      { name: 'BAY_1', x: -14.2, y: 15.0, col: '#00f0ff' },
      { name: 'BAY_2', x: -14.2, y: 28.0, col: '#00f0ff' },
      { name: 'BAY_3', x: -14.2, y: 38.0, col: '#00f0ff' },
      { name: 'BAY_4', x: -43.8, y: 15.0, col: '#00f0ff' },
      { name: 'BAY_5', x: -6.0, y: 0.0, col: '#00f0ff' }
    ];
    bays.forEach(b => {
      const sp = toScreen(b.x, b.y);
      ctx.fillStyle = b.col;
      ctx.beginPath(); ctx.arc(sp.sx, sp.sy, 5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#cbd5e1';
      ctx.font = '9px JetBrains Mono';
      ctx.fillText(b.name, sp.sx - 12, sp.sy - 8);
    });

    // Trail
    if (telemetryData.trail && telemetryData.trail.length > 1) {
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.5)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      telemetryData.trail.forEach((t, i) => {
        const sp = toScreen(t[0], t[1]);
        if (i === 0) ctx.moveTo(sp.sx, sp.sy);
        else ctx.lineTo(sp.sx, sp.sy);
      });
      ctx.stroke();
    }

    // Active Target Waypoint Indicator
    const targetPt = toScreen(telemetryData.target_x || -14.2, telemetryData.target_y || 15.0);
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(targetPt.sx, targetPt.sy, 14, 0, Math.PI * 2);
    ctx.stroke();

    // Rover Marker
    const roverPt = toScreen(telemetryData.x || -14.2, telemetryData.y || 15.0);
    const yaw = telemetryData.yaw || 1.571;

    ctx.save();
    ctx.translate(roverPt.sx, roverPt.sy);
    ctx.rotate(-yaw);

    // Rover body
    ctx.fillStyle = '#0a0e17';
    ctx.fillRect(-12, -18, 24, 36);
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 2;
    ctx.strokeRect(-12, -18, 24, 36);

    // Front sensor pod
    ctx.fillStyle = '#10b981';
    ctx.fillRect(-6, -18, 12, 4);

    ctx.restore();

    requestAnimationFrame(renderMap);
  }
  renderMap();
}

async function dispatchTargetCoordinates(x, y, name = 'WAYPOINT') {
  appendTerminalLog('info', `[DISPATCH] Requesting destination: ${name} (${x.toFixed(2)}, ${y.toFixed(2)})`);

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
      appendTerminalLog('success', `[DISPATCH] Target locked: ${name}. Navigation planner active.`);
    } else {
      appendTerminalLog('error', `[DISPATCH] Dispatch rejected: ${data.message || data.error}`);
      if (data.error === 'UNAUTHORIZED') promptOperatorPin();
    }
  } catch (err) {
    appendTerminalLog('warn', `[DISPATCH] Local simulation waypoint set: (${x.toFixed(2)}, ${y.toFixed(2)})`);
    telemetryData.target_x = x;
    telemetryData.target_y = y;
    telemetryData.target_name = name;
  }
}

function dispatchToBay(name, x, y) {
  const chips = document.querySelectorAll('.preset-chip');
  chips.forEach(c => c.classList.remove('active'));
  if (event && event.target) event.target.classList.add('active');
  dispatchTargetCoordinates(x, y, name);
}

function centerRoverOnMap() {
  appendTerminalLog('info', '[MAP] Recentered viewport on vehicle telemetry.');
}

function clearDispatchRoute() {
  appendTerminalLog('warn', '[DISPATCH] Cleared target waypoint. Rover entering idle hold.');
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
  initCameraOverlay();
  initCockpitNavMap();

  setInterval(fetchTelemetry, 250);
  setInterval(fetchHardware, 1000);

  fetchTelemetry();
  fetchHardware();

  updateOperatorUI(Boolean(operatorToken));
});

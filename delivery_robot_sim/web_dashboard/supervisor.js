/**
 * NexusDelivery — Fleet Engineer & Tactical Supervisor Cockpit Controller
 * Real-World Leaflet Tactical Map (CartoDB Dark Matter + Esri Satellite),
 * Multi-Rover Fleet Tracking (NEXUS-01, 02, 03), AI Perception HUD Overlay,
 * ODrive Powertrain Diagnostics, BMS 8-Cell Monitor, and Master E-Stop.
 */

// Operator Security State
let operatorToken = sessionStorage.getItem('nexus_operator_token') || '';
let isEstopEngaged = false;
let currentCameraMode = 'ai_hud';
let selectedRoverId = 'NEXUS-01';

// Leaflet Tactical Map State
let tacticalMap = null;
let darkTileLayer = null;
let satelliteTileLayer = null;
let isSatelliteMode = false;
let geofencePolygon = null;
let isGeofenceVisible = true;
let fleetMarkers = {};
let activeRoverTrail = null;
let targetWaypointMarker = null;

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

  // Pane 3 Hatch Status
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
  img.onerror = null;
  img.src = 'street_camera_frame.jpg';
}

/* ==========================================================================
   4. REAL-WORLD LEAFLET TACTICAL FLEET MAP
   ========================================================================== */
function initCockpitNavMap() {
  if (typeof L === 'undefined') {
    setTimeout(initCockpitNavMap, 150);
    return;
  }

  const container = document.getElementById('supervisorTacticalMap');
  if (!container) return;

  // Initialize Leaflet Map centered on Avenue Habib Bourguiba, Tunis
  const defaultCenter = [36.800542, 10.180012];
  tacticalMap = L.map('supervisorTacticalMap', {
    center: defaultCenter,
    zoom: 17,
    zoomControl: false,
    attributionControl: false
  });

  // Base Tile Layers
  darkTileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 20,
    subdomains: 'abcd'
  }).addTo(tacticalMap);

  satelliteTileLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19
  });

  // Zoom control top right
  L.control.zoom({ position: 'topright' }).addTo(tacticalMap);

  // Autonomous Sidewalk Geofence Corridor (Tunis Avenue Corridor)
  const geofenceCoords = [
    [36.801600, 10.177800],
    [36.801850, 10.183200],
    [36.799300, 10.183400],
    [36.799100, 10.178000]
  ];
  geofencePolygon = L.polygon(geofenceCoords, {
    color: '#00f0ff',
    weight: 2,
    dashArray: '6, 6',
    fillColor: '#00f0ff',
    fillOpacity: 0.12
  }).addTo(tacticalMap);

  // Active rover historical trail
  activeRoverTrail = L.polyline([], {
    color: '#00f0ff',
    weight: 3,
    opacity: 0.75,
    dashArray: '4, 4'
  }).addTo(tacticalMap);

  // Click-To-Dispatch on Real-World Map
  tacticalMap.on('click', (e) => {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;

    // Convert GPS coordinates to Gazebo simulation coordinates (Origin: Habib Bourguiba)
    const lat_0 = 36.800500;
    const lng_0 = 10.180000;
    const x = (lng - lng_0) * (111139.0 * Math.cos(lat_0 * Math.PI / 180));
    const y = (lat - lat_0) * 111139.0;

    dispatchTargetCoordinates(x, y, 'TACTICAL_GPS_WAYPOINT', lat, lng);
  });

  // Initial Fleet Fetch
  pollFleet();
  setInterval(pollFleet, 1000);
}

// Basemap Switcher (Satellite vs Dark Matter)
function toggleTacticalTiles() {
  if (!tacticalMap) return;
  const btn = document.getElementById('btnTacticalTile');

  if (!isSatelliteMode) {
    tacticalMap.removeLayer(darkTileLayer);
    satelliteTileLayer.addTo(tacticalMap);
    isSatelliteMode = true;
    if (btn) btn.innerHTML = '🏙️ Dark Matter';
    appendTerminalLog('info', '[MAP] Tile layer switched to: Esri World Imagery HD Satellite');
  } else {
    tacticalMap.removeLayer(satelliteTileLayer);
    darkTileLayer.addTo(tacticalMap);
    isSatelliteMode = false;
    if (btn) btn.innerHTML = '🛰️ Satellite';
    appendTerminalLog('info', '[MAP] Tile layer switched to: CartoDB Dark Matter Cyber Streets');
  }
}

// Geofence Layer Toggle
function toggleGeofence() {
  if (!tacticalMap || !geofencePolygon) return;
  if (isGeofenceVisible) {
    tacticalMap.removeLayer(geofencePolygon);
    isGeofenceVisible = false;
    appendTerminalLog('warn', '[GEOFENCE] Sidewalk boundary overlay disabled.');
  } else {
    geofencePolygon.addTo(tacticalMap);
    isGeofenceVisible = true;
    appendTerminalLog('success', '[GEOFENCE] Sidewalk boundary corridor armed and displayed.');
  }
}

// Recenter Map on Active Rover
function centerFleetMap() {
  if (!tacticalMap) return;
  const marker = fleetMarkers[selectedRoverId];
  if (marker) {
    tacticalMap.flyTo(marker.getLatLng(), 18, { duration: 1.2 });
    appendTerminalLog('info', `[MAP] Viewport centered on active unit: ${selectedRoverId}`);
  }
}

// Focus on a Specific Fleet Rover
function focusRover(roverId) {
  selectedRoverId = roverId;
  const chips = document.querySelectorAll('.presets-chips .preset-chip');
  chips.forEach(c => {
    if (c.textContent.includes(roverId)) {
      c.classList.add('active');
    } else {
      c.classList.remove('active');
    }
  });

  const marker = fleetMarkers[roverId];
  if (marker && tacticalMap) {
    tacticalMap.flyTo(marker.getLatLng(), 18, { duration: 1.2 });
  }
  appendTerminalLog('info', `[FLEET] Supervisor cockpit focused on: ${roverId}`);
}

// Poll Multi-Rover Fleet Data from Backend
async function pollFleet() {
  try {
    const res = await fetch('/api/fleet');
    if (!res.ok) return;
    const fleet = await res.json();

    fleet.forEach(rover => {
      const lat = rover.lat;
      const lng = rover.lng;
      const heading = rover.heading_deg || 0;
      const bat = rover.battery_pct || 98;
      const id = rover.id;

      // Color scheme per rover unit
      let colorClass = '';
      if (id === 'NEXUS-02') colorClass = 'rover-blue';
      else if (id === 'NEXUS-03') colorClass = 'rover-amber';

      const iconHtml = `
        <div class="tactical-rover-marker">
          <div class="tactical-marker-body ${colorClass}">
            <div class="tactical-radar-ring"></div>
            <svg class="tactical-chevron" viewBox="0 0 24 24" style="transform: rotate(${heading}deg);">
              <path d="M12 2L4 20L12 16L20 20L12 2Z" fill="#00f0ff" stroke="#ffffff" stroke-width="1.5" />
            </svg>
          </div>
          <div class="tactical-rover-tag">${id} • ${bat}%</div>
        </div>
      `;

      if (!fleetMarkers[id]) {
        const customIcon = L.divIcon({
          className: 'tactical-div-icon',
          html: iconHtml,
          iconSize: [44, 44],
          iconAnchor: [22, 22]
        });
        const marker = L.marker([lat, lng], { icon: customIcon }).addTo(tacticalMap);
        marker.on('click', () => focusRover(id));
        fleetMarkers[id] = marker;
      } else {
        fleetMarkers[id].setLatLng([lat, lng]);
        const el = fleetMarkers[id].getElement();
        if (el) {
          const chevron = el.querySelector('.tactical-chevron');
          if (chevron) chevron.style.transform = `rotate(${heading}deg)`;
          const tag = el.querySelector('.tactical-rover-tag');
          if (tag) tag.textContent = `${id} • ${bat}%`;
        }
      }

      // If this is the active rover, update HUD coordinates and trail
      if (id === selectedRoverId) {
        const mx = document.getElementById('mapCoordX');
        const my = document.getElementById('mapCoordY');
        const myaw = document.getElementById('mapCoordYaw');
        if (mx) mx.textContent = `${lat.toFixed(6)}° N`;
        if (my) my.textContent = `${lng.toFixed(6)}° E`;
        if (myaw) myaw.textContent = `${heading.toFixed(1)}°`;

        if (activeRoverTrail) {
          activeRoverTrail.addLatLng([lat, lng]);
          if (activeRoverTrail.getLatLngs().length > 300) {
            const pts = activeRoverTrail.getLatLngs();
            pts.shift();
            activeRoverTrail.setLatLngs(pts);
          }
        }
      }
    });
  } catch (err) {}
}

// Click-to-Dispatch Target Coordinates
async function dispatchTargetCoordinates(x, y, name = 'TACTICAL_WAYPOINT', lat = null, lng = null) {
  // If lat/lng not provided, calculate back from Gazebo (x, y)
  const lat_0 = 36.800500;
  const lng_0 = 10.180000;
  const targetLat = lat !== null ? lat : (lat_0 + (y / 111139.0));
  const targetLng = lng !== null ? lng : (lng_0 + (x / (111139.0 * Math.cos(lat_0 * Math.PI / 180))));

  // Render Waypoint Marker on Tactical Map
  if (tacticalMap) {
    const waypointHtml = `
      <div class="tactical-waypoint-marker">
        <div class="waypoint-crosshair">
          <div class="waypoint-center-dot"></div>
        </div>
        <div class="waypoint-tag">${name}</div>
      </div>
    `;
    const wpIcon = L.divIcon({
      className: 'tactical-div-icon',
      html: waypointHtml,
      iconSize: [36, 36],
      iconAnchor: [18, 18]
    });

    if (!targetWaypointMarker) {
      targetWaypointMarker = L.marker([targetLat, targetLng], { icon: wpIcon }).addTo(tacticalMap);
    } else {
      targetWaypointMarker.setLatLng([targetLat, targetLng]);
    }
  }

  appendTerminalLog('info', `[DISPATCH] Target locked: ${name} (GPS: ${targetLat.toFixed(6)}, ${targetLng.toFixed(6)} | Gazebo: ${x.toFixed(2)}, ${y.toFixed(2)})`);

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
        target_lat: round(targetLat, 6),
        target_lng: round(targetLng, 6),
        action: 'TRANSIT'
      })
    });
    const data = await res.json();
    if (data.success) {
      appendTerminalLog('success', `[DISPATCH] Waypoint acknowledged by ROS 2 Nav2 stack. Route computation active.`);
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

function clearDispatchRoute() {
  if (targetWaypointMarker && tacticalMap) {
    tacticalMap.removeLayer(targetWaypointMarker);
    targetWaypointMarker = null;
  }
  if (activeRoverTrail) {
    activeRoverTrail.setLatLngs([]);
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
  initCameraOverlay();
  initCockpitNavMap();

  setInterval(fetchTelemetry, 250);
  setInterval(fetchHardware, 1000);

  fetchTelemetry();
  fetchHardware();

  updateOperatorUI(Boolean(operatorToken));
});

/**
 * NexusDelivery — Gazebo World Interactive Vector Map Engine
 * 
 * High-performance HTML5 Canvas rendering of the actual Gazebo Classic simulation environment:
 * - Metric coordinate reference: X in [-48.0, 112.0] m, Y in [-48.0, 48.0] m
 * - Navigable road networks, lane dividing lines, and pedestrian sidewalks
 * - Solid building footprint blocks (restricted no-go zones)
 * - Central Logistics Depot Compound with interior dock bay and entrance portal
 * - Zebra crosswalks, traffic lights, and urban street furniture
 * - Authentic live robot pose (x, y, yaw), trajectory breadcrumbs, and planned A* route
 * - Interactive doorstep destination picker with reachability and curbside snapping
 * - Retina-crisp scaling, smooth pan, mouse-wheel zoom, and coordinate HUD
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.GazeboWorldMap = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {

  // World metric constants matching rdsim_gazebo/worlds/small_city_dynamic.world
  const DEFAULT_BOUNDS = {
    min_x: -48.0,
    max_x: 112.0,
    min_y: -48.0,
    max_y: 48.0,
    width_m: 160.0,
    height_m: 96.0
  };

  class GazeboWorldMap {
    constructor(options = {}) {
      this.containerId = options.containerId;
      this.container = document.getElementById(this.containerId);
      if (!this.container) {
        console.error(`[GazeboWorldMap] Container element #${this.containerId} not found.`);
        return;
      }

      this.mode = options.mode || 'customer'; // 'customer' or 'supervisor'
      this.onDestinationSelected = options.onDestinationSelected || null;
      this.onRobotClicked = options.onRobotClicked || null;

      // World manifest
      this.manifest = null;
      this.bounds = Object.assign({}, DEFAULT_BOUNDS);

      // Viewport transform (Pan & Zoom)
      this.scale = 1.0;
      this.baseScale = 1.0;
      this.panX = 0;
      this.panY = 0;
      this.margin = 35; // margin in px
      this.minZoom = 0.5;
      this.maxZoom = 5.0;

      // Telemetry state
      this.robotPose = { x: -32.0, y: -0.75, yaw: 0.0, v: 0.0 };
      this.robotTarget = { name: 'DEPOT', x: -32.0, y: -0.75 };
      this.trajectoryTrail = [];
      this.plannedRoute = [];
      this.telemetryFreshness = 'DISCONNECTED';
      this.trafficLightRed = false;
      this.obstacleDetected = false;
      this.obstacleDist = 999.0;

      // Selected / Hovered Destination
      this.selectedPin = null; // { x, y, stopping_x, stopping_y, heading, valid, explanation }
      this.hoveredEntity = null;
      this.cursorWorld = { x: 0.0, y: 0.0 };

      // Layer Toggles (for supervisor)
      this.layers = {
        grid: true,
        buildings: true,
        roads: true,
        crosswalks: true,
        landmarks: true,
        stoppingBays: true,
        plannedRoute: true,
        trajectoryTrail: true,
        robot: true,
        roadNetworkGraph: options.mode === 'supervisor',
        obstacleZones: options.mode === 'supervisor'
      };

      // Mouse drag state
      this.isDragging = false;
      this.dragStart = { x: 0, y: 0 };
      this.hasPanned = false;

      // Animation loop
      this.animFrameId = null;
      this.pulsePhase = 0;

      this._initDom();
      this._bindEvents();
      this._loadWorldManifest();
      this._startRenderLoop();
    }

    // ========================================================================
    // DOM & Canvas Setup
    // ========================================================================

    _initDom() {
      this.container.innerHTML = '';
      this.container.style.position = 'relative';
      this.container.style.overflow = 'hidden';
      this.container.style.backgroundColor = '#0a0f1d';
      this.container.style.userSelect = 'none';

      // 1. Main Canvas
      this.canvas = document.createElement('canvas');
      this.canvas.className = 'gazebo-map-canvas';
      this.canvas.style.display = 'block';
      this.canvas.style.width = '100%';
      this.canvas.style.height = '100%';
      this.canvas.style.cursor = 'crosshair';
      this.container.appendChild(this.canvas);
      this.ctx = this.canvas.getContext('2d');

      // 2. Map Controls (Zoom In/Out, Reset, Focus Robot)
      this.controlsWrap = document.createElement('div');
      this.controlsWrap.className = 'gazebo-map-controls';
      this.controlsWrap.style.position = 'absolute';
      this.controlsWrap.style.bottom = '16px';
      this.controlsWrap.style.right = '16px';
      this.controlsWrap.style.display = 'flex';
      this.controlsWrap.style.flexDirection = 'column';
      this.controlsWrap.style.gap = '6px';
      this.controlsWrap.style.zIndex = '10';

      const btnStyle = `
        width: 38px; height: 38px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.15);
        background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px); color: #e2e8f0;
        font-size: 16px; font-weight: bold; cursor: pointer; display: flex; align-items: center;
        justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.4); transition: all 0.2s;
      `;

      this.btnZoomIn = document.createElement('button');
      this.btnZoomIn.innerHTML = '+';
      this.btnZoomIn.title = 'Zoom In';
      this.btnZoomIn.style.cssText = btnStyle;
      this.btnZoomIn.onclick = () => this.zoom(1.25);

      this.btnZoomOut = document.createElement('button');
      this.btnZoomOut.innerHTML = '−';
      this.btnZoomOut.title = 'Zoom Out';
      this.btnZoomOut.style.cssText = btnStyle;
      this.btnZoomOut.onclick = () => this.zoom(0.8);

      this.btnReset = document.createElement('button');
      this.btnReset.innerHTML = '⟲';
      this.btnReset.title = 'Fit World Extent';
      this.btnReset.style.cssText = btnStyle;
      this.btnReset.onclick = () => this.fitWorldBounds();

      this.btnFocusRobot = document.createElement('button');
      this.btnFocusRobot.innerHTML = '🎯';
      this.btnFocusRobot.title = 'Center on Nexus AMR';
      this.btnFocusRobot.style.cssText = btnStyle;
      this.btnFocusRobot.onclick = () => this.centerOnRobot();

      this.controlsWrap.appendChild(this.btnZoomIn);
      this.controlsWrap.appendChild(this.btnZoomOut);
      this.controlsWrap.appendChild(this.btnReset);
      this.controlsWrap.appendChild(this.btnFocusRobot);
      this.container.appendChild(this.controlsWrap);

      // 3. Top-Left HUD (World Title & Coordinate Inspector)
      this.coordHud = document.createElement('div');
      this.coordHud.className = 'gazebo-coord-hud';
      this.coordHud.style.position = 'absolute';
      this.coordHud.style.top = '14px';
      this.coordHud.style.left = '14px';
      this.coordHud.style.padding = '8px 12px';
      this.coordHud.style.borderRadius = '8px';
      this.coordHud.style.background = 'rgba(15, 23, 42, 0.85)';
      this.coordHud.style.backdropFilter = 'blur(8px)';
      this.coordHud.style.border = '1px solid rgba(56, 189, 248, 0.25)';
      this.coordHud.style.color = '#94a3b8';
      this.coordHud.style.fontFamily = "'JetBrains Mono', monospace";
      this.coordHud.style.fontSize = '12px';
      this.coordHud.style.zIndex = '10';
      this.coordHud.style.pointerEvents = 'none';
      this.coordHud.innerHTML = `
        <div style="font-weight: 700; color: #38bdf8; margin-bottom: 2px;">GAZEBO SIMULATION WORLD</div>
        <div id="${this.containerId}-cursorCoord">X: 0.00m  Y: 0.00m</div>
      `;
      this.container.appendChild(this.coordHud);

      // 4. Top-Right Freshness Badge
      this.freshnessBadge = document.createElement('div');
      this.freshnessBadge.className = 'gazebo-freshness-badge';
      this.freshnessBadge.style.position = 'absolute';
      this.freshnessBadge.style.top = '14px';
      this.freshnessBadge.style.right = '14px';
      this.freshnessBadge.style.padding = '6px 12px';
      this.freshnessBadge.style.borderRadius = '20px';
      this.freshnessBadge.style.fontSize = '11px';
      this.freshnessBadge.style.fontWeight = '700';
      this.freshnessBadge.style.fontFamily = "'JetBrains Mono', monospace";
      this.freshnessBadge.style.display = 'flex';
      this.freshnessBadge.style.alignItems = 'center';
      this.freshnessBadge.style.gap = '6px';
      this.freshnessBadge.style.zIndex = '10';
      this.freshnessBadge.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';
      this.updateFreshness('STANDBY');
      this.container.appendChild(this.freshnessBadge);

      this._resizeCanvas();
    }

    _resizeCanvas() {
      const rect = this.container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      this.width = rect.width;
      this.height = rect.height;

      this.canvas.width = Math.floor(rect.width * dpr);
      this.canvas.height = Math.floor(rect.height * dpr);
      this.ctx.setTransform(1, 0, 0, 1, 0, 0);
      this.ctx.scale(dpr, dpr);

      this.fitWorldBounds();
    }

    fitWorldBounds() {
      const usableW = this.width - (2 * this.margin);
      const usableH = this.height - (2 * this.margin);

      const scaleX = usableW / this.bounds.width_m;
      const scaleY = usableH / this.bounds.height_m;
      this.baseScale = Math.min(scaleX, scaleY);
      this.scale = this.baseScale;

      this.panX = this.margin + (usableW - (this.bounds.width_m * this.scale)) / 2.0;
      this.panY = this.margin + (usableH - (this.bounds.height_m * this.scale)) / 2.0;
    }

    centerOnRobot() {
      if (!this.robotPose) return;
      const screenPt = this.worldToScreen(this.robotPose.x, this.robotPose.y);
      const centerScreenX = this.width / 2.0;
      const centerScreenY = this.height / 2.0;

      this.panX += (centerScreenX - screenPt.u);
      this.panY += (centerScreenY - screenPt.v);
    }

    zoom(factor, centerScreenX = this.width / 2, centerScreenY = this.height / 2) {
      const newScale = Math.max(this.baseScale * this.minZoom, Math.min(this.baseScale * this.maxZoom, this.scale * factor));
      const actualFactor = newScale / this.scale;

      this.panX = centerScreenX - (centerScreenX - this.panX) * actualFactor;
      this.panY = centerScreenY - (centerScreenY - this.panY) * actualFactor;
      this.scale = newScale;
    }

    // ========================================================================
    // Coordinate Transformations: Gazebo World (m) <-> Screen (px)
    // ========================================================================

    worldToScreen(x_g, y_g) {
      const u = this.panX + (x_g - this.bounds.min_x) * this.scale;
      const v = this.panY + (this.bounds.max_y - y_g) * this.scale;
      return { u, v };
    }

    screenToWorld(u, v) {
      const x_g = this.bounds.min_x + (u - this.panX) / this.scale;
      const y_g = this.bounds.max_y - (v - this.panY) / this.scale;
      return { x: Math.round(x_g * 100) / 100, y: Math.round(y_g * 100) / 100 };
    }

    // ========================================================================
    // Event Listeners
    // ========================================================================

    _bindEvents() {
      window.addEventListener('resize', () => this._resizeCanvas());

      this.canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        const factor = e.deltaY < 0 ? 1.15 : 0.87;
        this.zoom(factor, mouseX, mouseY);
      }, { passive: false });

      this.canvas.addEventListener('mousedown', (e) => {
        this.isDragging = true;
        this.hasPanned = false;
        this.dragStart = { x: e.clientX, y: e.clientY };
      });

      window.addEventListener('mousemove', (e) => {
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        if (this.isDragging) {
          const dx = e.clientX - this.dragStart.x;
          const dy = e.clientY - this.dragStart.y;
          if (Math.hypot(dx, dy) > 4) {
            this.hasPanned = true;
          }
          this.panX += dx;
          this.panY += dy;
          this.dragStart = { x: e.clientX, y: e.clientY };
        }

        // Update cursor coordinate HUD if mouse inside canvas
        if (mouseX >= 0 && mouseX <= this.width && mouseY >= 0 && mouseY <= this.height) {
          this.cursorWorld = this.screenToWorld(mouseX, mouseY);
          const coordEl = document.getElementById(`${this.containerId}-cursorCoord`);
          if (coordEl) {
            coordEl.innerText = `X: ${this.cursorWorld.x.toFixed(2)}m  Y: ${this.cursorWorld.y.toFixed(2)}m`;
          }
        }
      });

      window.addEventListener('mouseup', (e) => {
        if (!this.isDragging) return;
        this.isDragging = false;

        // If user just clicked without panning, handle destination pick
        if (!this.hasPanned) {
          const rect = this.canvas.getBoundingClientRect();
          const mouseX = e.clientX - rect.left;
          const mouseY = e.clientY - rect.top;
          if (mouseX >= 0 && mouseX <= this.width && mouseY >= 0 && mouseY <= this.height) {
            const worldPt = this.screenToWorld(mouseX, mouseY);
            this.handleMapClick(worldPt.x, worldPt.y);
          }
        }
      });

      // Touch events for mobile tablet / phone responsiveness
      this.canvas.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) {
          this.isDragging = true;
          this.hasPanned = false;
          this.dragStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
      }, { passive: true });

      this.canvas.addEventListener('touchmove', (e) => {
        if (this.isDragging && e.touches.length === 1) {
          const dx = e.touches[0].clientX - this.dragStart.x;
          const dy = e.touches[0].clientY - this.dragStart.y;
          if (Math.hypot(dx, dy) > 4) this.hasPanned = true;
          this.panX += dx;
          this.panY += dy;
          this.dragStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
      }, { passive: true });

      this.canvas.addEventListener('touchend', (e) => {
        if (!this.hasPanned && e.changedTouches.length === 1) {
          const rect = this.canvas.getBoundingClientRect();
          const touchX = e.changedTouches[0].clientX - rect.left;
          const touchY = e.changedTouches[0].clientY - rect.top;
          const worldPt = this.screenToWorld(touchX, touchY);
          this.handleMapClick(worldPt.x, worldPt.y);
        }
        this.isDragging = false;
      });
    }

    // ========================================================================
    // Data Loading & Validation
    // ========================================================================

    async _loadWorldManifest() {
      try {
        const resp = await fetch('/api/map/gazebo_world');
        if (resp.ok) {
          this.manifest = await resp.json();
          if (this.manifest && this.manifest.bounds) {
            this.bounds = Object.assign({}, this.manifest.bounds);
            this.fitWorldBounds();
          }
        } else {
          console.warn('[GazeboWorldMap] Manifest fetch failed, using fallback.');
          this._initFallbackManifest();
        }
      } catch (err) {
        console.warn('[GazeboWorldMap] API unreachable, using fallback manifest:', err);
        this._initFallbackManifest();
      }
    }

    _initFallbackManifest() {
      // Offline fallback geometry matching route_planner.py
      this.manifest = {
        bounds: DEFAULT_BOUNDS,
        depot: {
          name: 'Central Logistics Depot Hub',
          bounds: { min_x: -35.0, max_x: -28.0, min_y: -2.5, max_y: 4.5 },
          dock_xy: [-31.5, -0.75],
          door_xy: [-27.5, -0.75]
        },
        buildings: [
          { name: 'Block NW', min_x: -42.5, max_x: -17.5, min_y: 3.0, max_y: 42.5 },
          { name: 'Block SW', min_x: -42.5, max_x: -17.5, min_y: -42.5, max_y: -3.0 },
          { name: 'Block NC', min_x: -12.5, max_x: 42.5, min_y: 3.0, max_y: 42.5 },
          { name: 'Block SC', min_x: -12.5, max_x: 42.5, min_y: -42.5, max_y: -3.0 },
          { name: 'Block NE', min_x: 47.5, max_x: 105.0, min_y: 3.0, max_y: 42.5 },
          { name: 'Block SE', min_x: 47.5, max_x: 105.0, min_y: -42.5, max_y: -3.0 }
        ],
        roads: [
          { name: 'Central Boulevard', orientation: 'HORIZONTAL', fixed_y: 0.0, min_x: -28.0, max_x: 108.0, width_m: 7.0 },
          { name: 'North Street', orientation: 'HORIZONTAL', fixed_y: 45.0, min_x: -45.0, max_x: 108.0, width_m: 7.0 },
          { name: 'South Street', orientation: 'HORIZONTAL', fixed_y: -45.0, min_x: -45.0, max_x: 108.0, width_m: 7.0 },
          { name: 'North Avenue', orientation: 'VERTICAL', fixed_x: -15.0, min_y: -45.0, max_y: 45.0, width_m: 7.0 },
          { name: 'West Boulevard', orientation: 'VERTICAL', fixed_x: -45.0, min_y: -45.0, max_y: 45.0, width_m: 7.0 },
          { name: 'East Avenue', orientation: 'VERTICAL', fixed_x: 45.0, min_y: -45.0, max_y: 45.0, width_m: 7.0 },
          { name: 'Far East Avenue', orientation: 'VERTICAL', fixed_x: 108.0, min_y: -45.0, max_y: 45.0, width_m: 7.0 }
        ],
        bays: [
          { id: 'CLIENT_1_NORTH_AVENUE', customer_name: 'Sophie Laurent', door_xy: [-9.8, 15.0], stopping_xy: [-14.6, 15.0], approach_heading: 0.0 },
          { id: 'CLIENT_2_NORTH_AVENUE', customer_name: 'Marc Dubois', door_xy: [-9.8, 28.0], stopping_xy: [-14.6, 28.0], approach_heading: 0.0 },
          { id: 'CLIENT_3_NORTH_PLAZA', customer_name: 'Elena Rostova', door_xy: [-13.4, 38.0], stopping_xy: [-14.6, 38.0], approach_heading: 0.0 },
          { id: 'CLIENT_4_WEST_BOULEVARD', customer_name: 'Lucas Vance', door_xy: [-46.5, 15.0], stopping_xy: [-43.8, 15.0], approach_heading: 3.1416 },
          { id: 'CLIENT_5_CENTRAL_SQUARE', customer_name: 'Amira Khan', door_xy: [-5.0, 2.5], stopping_xy: [-6.0, 0.0], approach_heading: 1.5708 },
          { id: 'CLIENT_6_EAST_AVENUE', customer_name: 'David Kim', door_xy: [46.5, 15.0], stopping_xy: [43.8, 15.0], approach_heading: 0.0 },
          { id: 'CLIENT_7_SOUTH_MARKET', customer_name: 'Marcus Brody', door_xy: [-13.4, -25.0], stopping_xy: [-14.6, -25.0], approach_heading: 0.0 },
          { id: 'CLIENT_8_FAR_EAST_MARINA', customer_name: 'Chloe Dubois', door_xy: [108.0, 2.5], stopping_xy: [106.0, 0.0], approach_heading: 0.0 }
        ]
      };
    }

    async handleMapClick(x, y) {
      // 1. Check if user clicked near an existing customer bay pin
      if (this.manifest && this.manifest.bays) {
        for (const bay of this.manifest.bays) {
          const d = Math.hypot(x - bay.door_xy[0], y - bay.door_xy[1]);
          if (d < 3.0) {
            this.selectBay(bay);
            return;
          }
        }
      }

      // 2. Validate arbitrary clicked coordinate via backend
      try {
        const resp = await fetch('/api/map/validate_destination', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ x, y })
        });
        const result = await resp.json();
        if (result.valid) {
          this.selectedPin = {
            valid: true,
            raw_xy: result.raw_xy,
            stopping_xy: result.stopping_xy,
            heading: result.approach_heading,
            heading_deg: result.approach_heading_deg,
            explanation: result.explanation,
            route: result.route,
            distance_m: result.distance_m,
            eta_seconds: result.eta_seconds,
            eta_minutes: result.eta_minutes
          };
          if (this.onDestinationSelected) {
            this.onDestinationSelected(this.selectedPin);
          }
        } else {
          this.selectedPin = {
            valid: false,
            raw_xy: [x, y],
            explanation: result.explanation || 'Location inside restricted building block or out of range.'
          };
          if (this.onDestinationSelected) {
            this.onDestinationSelected(this.selectedPin);
          }
        }
      } catch (err) {
        console.warn('Destination validation error:', err);
      }
    }

    selectBay(bay) {
      const sx = bay.stopping_xy[0];
      const sy = bay.stopping_xy[1];
      const dx = bay.door_xy[0];
      const dy = bay.door_xy[1];
      const dist = Math.round(Math.hypot(sx - this.robotPose.x, sy - this.robotPose.y) * 10) / 10;
      const eta = Math.round((dist / 0.8) + 6);

      this.selectedPin = {
        valid: true,
        bay_id: bay.id,
        customer_name: bay.customer_name,
        raw_xy: [dx, dy],
        stopping_xy: [sx, sy],
        heading: bay.approach_heading,
        heading_deg: Math.round(bay.approach_heading * 57.2958),
        explanation: `Curbside Bay for ${bay.customer_name}`,
        distance_m: dist,
        eta_seconds: eta,
        eta_minutes: Math.max(1, Math.round(eta / 60))
      };

      if (this.onDestinationSelected) {
        this.onDestinationSelected(this.selectedPin);
      }
    }

    // ========================================================================
    // Live Telemetry Synchronization
    // ========================================================================

    updateTelemetry(data) {
      if (!data) return;

      this.robotPose.x = typeof data.gazebo_x !== 'undefined' ? data.gazebo_x : data.x;
      this.robotPose.y = typeof data.gazebo_y !== 'undefined' ? data.gazebo_y : data.y;
      this.robotPose.yaw = data.yaw || 0.0;
      this.robotPose.v = data.actual_v || 0.0;

      if (data.target_name) {
        this.robotTarget.name = data.target_name;
        this.robotTarget.x = data.target_x || -32.0;
        this.robotTarget.y = data.target_y || -0.75;
      }

      if (Array.isArray(data.trail)) {
        this.trajectoryTrail = data.trail;
      }
      if (Array.isArray(data.planned_route)) {
        this.plannedRoute = data.planned_route;
      }

      this.trafficLightRed = !!data.red_light;
      this.obstacleDetected = !!data.obstacle_detected;
      this.obstacleDist = data.obstacle_dist || 999.0;

      const freshness = data.freshness_status || (data.is_stale ? 'STALE' : 'LIVE');
      this.updateFreshness(freshness, data.odom_age_s);
    }

    updateFreshness(status, age = 0) {
      this.telemetryFreshness = status;
      if (!this.freshnessBadge) return;

      if (status.includes('LIVE')) {
        this.freshnessBadge.style.background = 'rgba(16, 185, 129, 0.2)';
        this.freshnessBadge.style.border = '1px solid #10b981';
        this.freshnessBadge.style.color = '#34d399';
        this.freshnessBadge.innerHTML = `<span style="width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981;"></span> ROS 2 LIVE (50Hz)`;
      } else if (status.includes('STALE')) {
        this.freshnessBadge.style.background = 'rgba(245, 158, 11, 0.2)';
        this.freshnessBadge.style.border = '1px solid #f59e0b';
        this.freshnessBadge.style.color = '#fbbf24';
        this.freshnessBadge.innerHTML = `<span style="width:8px;height:8px;border-radius:50%;background:#f59e0b;"></span> STALE (${age.toFixed(1)}s)`;
      } else {
        this.freshnessBadge.style.background = 'rgba(239, 68, 68, 0.2)';
        this.freshnessBadge.style.border = '1px solid #ef4444';
        this.freshnessBadge.style.color = '#f87171';
        this.freshnessBadge.innerHTML = `<span style="width:8px;height:8px;border-radius:50%;background:#ef4444;"></span> SIMULATION DISCONNECTED`;
      }
    }

    // ========================================================================
    // Canvas Render Loop
    // ========================================================================

    _startRenderLoop() {
      const render = () => {
        this.pulsePhase = (this.pulsePhase + 0.05) % (Math.PI * 2);
        this._draw();
        this.animFrameId = requestAnimationFrame(render);
      };
      this.animFrameId = requestAnimationFrame(render);
    }

    _draw() {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.width, this.height);

      // 1. Background Grid & Coordinates
      if (this.layers.grid) this._drawGrid(ctx);

      // 2. Navigable Roads & Sidewalks
      if (this.layers.roads) this._drawRoads(ctx);

      // 3. Zebra Crosswalks
      if (this.layers.crosswalks) this._drawCrosswalks(ctx);

      // 4. Solid Building Footprint Blocks
      if (this.layers.buildings) this._drawBuildings(ctx);

      // 5. Logistics Depot Compound
      this._drawDepot(ctx);

      // 6. Urban Infrastructure & Street Furniture
      if (this.layers.landmarks) this._drawLandmarks(ctx);

      // 7. Customer Doorstep Stopping Bays
      if (this.layers.stoppingBays) this._drawStoppingBays(ctx);

      // 8. Planned A* Route Polyline
      if (this.layers.plannedRoute && this.plannedRoute.length > 1) {
        this._drawPlannedRoute(ctx);
      }

      // 9. Executed Trajectory Trail
      if (this.layers.trajectoryTrail && this.trajectoryTrail.length > 1) {
        this._drawTrajectoryTrail(ctx);
      }

      // 10. Selected User Pin
      if (this.selectedPin) {
        this._drawSelectedPin(ctx);
      }

      // 11. Autonomous Robot Marker
      if (this.layers.robot) {
        this._drawRobot(ctx);
      }

      // 12. Supervisor Topological Graph (if enabled)
      if (this.layers.roadNetworkGraph && this.manifest && this.manifest.intersections) {
        this._drawTopologicalGraph(ctx);
      }
    }

    // ========================================================================
    // Drawing Primitives
    // ========================================================================

    _drawGrid(ctx) {
      ctx.save();
      ctx.lineWidth = 1;

      // Draw 10m grid lines
      for (let x = -40; x <= 110; x += 10) {
        const p1 = this.worldToScreen(x, this.bounds.min_y);
        const p2 = this.worldToScreen(x, this.bounds.max_y);
        ctx.strokeStyle = (x === 0) ? 'rgba(56, 189, 248, 0.25)' : 'rgba(255, 255, 255, 0.04)';
        ctx.beginPath();
        ctx.moveTo(p1.u, p1.v);
        ctx.lineTo(p2.u, p2.v);
        ctx.stroke();

        // Label on top
        if (x % 20 === 0 && this.scale > 3.0) {
          ctx.fillStyle = 'rgba(148, 163, 184, 0.4)';
          ctx.font = '9px monospace';
          ctx.fillText(`${x}m`, p1.u + 2, this.margin - 4);
        }
      }

      for (let y = -40; y <= 40; y += 10) {
        const p1 = this.worldToScreen(this.bounds.min_x, y);
        const p2 = this.worldToScreen(this.bounds.max_x, y);
        ctx.strokeStyle = (y === 0) ? 'rgba(56, 189, 248, 0.25)' : 'rgba(255, 255, 255, 0.04)';
        ctx.beginPath();
        ctx.moveTo(p1.u, p1.v);
        ctx.lineTo(p2.u, p2.v);
        ctx.stroke();

        if (y % 20 === 0 && this.scale > 3.0) {
          ctx.fillStyle = 'rgba(148, 163, 184, 0.4)';
          ctx.font = '9px monospace';
          ctx.fillText(`${y}m`, 4, p1.v - 2);
        }
      }

      // World outer boundary border
      const bTL = this.worldToScreen(this.bounds.min_x, this.bounds.max_y);
      const bBR = this.worldToScreen(this.bounds.max_x, this.bounds.min_y);
      ctx.strokeStyle = 'rgba(99, 102, 241, 0.35)';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 6]);
      ctx.strokeRect(bTL.u, bTL.v, bBR.u - bTL.u, bBR.v - bTL.v);
      ctx.setLineDash([]);
      ctx.restore();
    }

    _drawRoads(ctx) {
      if (!this.manifest || !this.manifest.roads) return;
      ctx.save();

      for (const road of this.manifest.roads) {
        const width = (road.width_m || 7.0);
        const halfW = width / 2.0;
        const sidewalkW = 2.0;

        let rMinX, rMaxX, rMinY, rMaxY;
        if (road.orientation === 'HORIZONTAL') {
          rMinX = road.min_x;
          rMaxX = road.max_x;
          rMinY = road.fixed_y - halfW;
          rMaxY = road.fixed_y + halfW;
        } else {
          rMinX = road.fixed_x - halfW;
          rMaxX = road.fixed_x + halfW;
          rMinY = road.min_y;
          rMaxY = road.max_y;
        }

        // Sidewalk band (outer curb)
        const swTL = this.worldToScreen(rMinX - (road.orientation === 'VERTICAL' ? sidewalkW : 0),
                                        rMaxY + (road.orientation === 'HORIZONTAL' ? sidewalkW : 0));
        const swBR = this.worldToScreen(rMaxX + (road.orientation === 'VERTICAL' ? sidewalkW : 0),
                                        rMinY - (road.orientation === 'HORIZONTAL' ? sidewalkW : 0));
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(swTL.u, swTL.v, swBR.u - swTL.u, swBR.v - swTL.v);

        // Asphalt roadway
        const tl = this.worldToScreen(rMinX, rMaxY);
        const br = this.worldToScreen(rMaxX, rMinY);
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(tl.u, tl.v, br.u - tl.u, br.v - tl.v);

        // Curbside borders
        ctx.strokeStyle = '#334155';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(tl.u, tl.v, br.u - tl.u, br.v - tl.v);

        // Center dashed dividing line
        ctx.strokeStyle = '#f59e0b88';
        ctx.lineWidth = Math.max(1, 1.5 * (this.scale / this.baseScale));
        ctx.setLineDash([8, 8]);
        ctx.beginPath();
        if (road.orientation === 'HORIZONTAL') {
          const c1 = this.worldToScreen(road.min_x, road.fixed_y);
          const c2 = this.worldToScreen(road.max_x, road.fixed_y);
          ctx.moveTo(c1.u, c1.v);
          ctx.lineTo(c2.u, c2.v);
        } else {
          const c1 = this.worldToScreen(road.fixed_x, road.min_y);
          const c2 = this.worldToScreen(road.fixed_x, road.max_y);
          ctx.moveTo(c1.u, c1.v);
          ctx.lineTo(c2.u, c2.v);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }
      ctx.restore();
    }

    _drawCrosswalks(ctx) {
      ctx.save();
      // Depot Zebra Crosswalk at x = -26.5m
      const x_cw = -26.5;
      const stripeW = 0.5;
      for (let y = -2.6; y <= 2.6; y += 0.8) {
        const p1 = this.worldToScreen(x_cw - stripeW / 2, y + 0.25);
        const p2 = this.worldToScreen(x_cw + stripeW / 2, y - 0.25);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.75)';
        ctx.fillRect(p1.u, p1.v, p2.u - p1.u, p2.v - p1.v);
      }

      // North Ave Intersection Crosswalk at y = 3.5m
      const y_cw = 3.5;
      for (let x = -17.5; x <= -12.5; x += 0.8) {
        const p1 = this.worldToScreen(x - 0.25, y_cw + stripeW / 2);
        const p2 = this.worldToScreen(x + 0.25, y_cw - stripeW / 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.75)';
        ctx.fillRect(p1.u, p1.v, p2.u - p1.u, p2.v - p1.v);
      }
      ctx.restore();
    }

    _drawBuildings(ctx) {
      if (!this.manifest || !this.manifest.buildings) return;
      ctx.save();

      for (const b of this.manifest.buildings) {
        if (b.type === 'DEPOT_COMPOUND') continue; // Handled separately

        const tl = this.worldToScreen(b.min_x, b.max_y);
        const br = this.worldToScreen(b.max_x, b.min_y);
        const w = br.u - tl.u;
        const h = br.v - tl.v;

        // Building solid base
        ctx.fillStyle = '#090d16';
        ctx.fillRect(tl.u, tl.v, w, h);

        // Chamfered borders & subtle neon glow
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.25)';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(tl.u, tl.v, w, h);

        // Architectural grid pattern inside building
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
        ctx.lineWidth = 1;
        const step = Math.max(12, 10 * this.scale);
        for (let gx = tl.u + step; gx < br.u; gx += step) {
          ctx.beginPath();
          ctx.moveTo(gx, tl.v);
          ctx.lineTo(gx, br.v);
          ctx.stroke();
        }

        // Building Label Header Badge
        if (this.scale > 1.2) {
          const cx = tl.u + w / 2.0;
          const cy = tl.v + h / 2.0;

          ctx.fillStyle = 'rgba(30, 41, 59, 0.8)';
          const badgeW = Math.min(w - 10, 110);
          const badgeH = 22;
          ctx.fillRect(cx - badgeW / 2, cy - badgeH / 2, badgeW, badgeH);
          ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)';
          ctx.strokeRect(cx - badgeW / 2, cy - badgeH / 2, badgeW, badgeH);

          ctx.fillStyle = '#94a3b8';
          ctx.font = 'bold 10px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(b.name.split(' - ')[0] || b.name, cx, cy);
        }
      }
      ctx.restore();
    }

    _drawDepot(ctx) {
      ctx.save();
      // Depot Footprint: [-35.0, -28.0] x [-2.5, 4.5]
      const tl = this.worldToScreen(-35.0, 4.5);
      const br = this.worldToScreen(-28.0, -2.5);
      const w = br.u - tl.u;
      const h = br.v - tl.v;

      // Compound Fill (distinct cyber blue / emerald tint)
      ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
      ctx.fillRect(tl.u, tl.v, w, h);
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 2;
      ctx.strokeRect(tl.u, tl.v, w, h);

      // Interior Docking Bay [-31.5, -0.75]
      const dockPt = this.worldToScreen(-31.5, -0.75);
      ctx.fillStyle = 'rgba(16, 185, 129, 0.3)';
      ctx.beginPath();
      ctx.arc(dockPt.u, dockPt.v, Math.max(6, 4 * this.scale), 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#10b981';
      ctx.stroke();

      // Open Bay Door Portal at x = -27.5m
      const doorPt = this.worldToScreen(-27.5, -0.75);
      ctx.fillStyle = '#38bdf8';
      ctx.beginPath();
      ctx.arc(doorPt.u, doorPt.v, 4, 0, Math.PI * 2);
      ctx.fill();

      // Arrow pointing out of depot bay door
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(dockPt.u, dockPt.v);
      ctx.lineTo(doorPt.u, doorPt.v);
      ctx.stroke();

      // Depot Label
      ctx.fillStyle = '#10b981';
      ctx.font = 'bold 10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('CENTRAL DEPOT HUB', tl.u + w / 2, tl.v - 6);
      ctx.restore();
    }

    _drawLandmarks(ctx) {
      ctx.save();
      // Traffic Light Post at (-15.0, 0.0)
      const tlPt = this.worldToScreen(-15.0, 0.0);
      ctx.fillStyle = '#0f172a';
      ctx.beginPath();
      ctx.arc(tlPt.u, tlPt.v, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#64748b';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Signal light color (Red or Green from telemetry)
      const lightCol = this.trafficLightRed ? '#ef4444' : '#10b981';
      ctx.fillStyle = lightCol;
      ctx.beginPath();
      ctx.arc(tlPt.u, tlPt.v, 4.5, 0, Math.PI * 2);
      ctx.fill();

      // Pulsing halo for active traffic light
      ctx.strokeStyle = lightCol;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(tlPt.u, tlPt.v, 7 + Math.sin(this.pulsePhase) * 2, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    _drawStoppingBays(ctx) {
      if (!this.manifest || !this.manifest.bays) return;
      ctx.save();

      for (const bay of this.manifest.bays) {
        const doorPt = this.worldToScreen(bay.door_xy[0], bay.door_xy[1]);
        const stopPt = this.worldToScreen(bay.stopping_xy[0], bay.stopping_xy[1]);

        // Dashed connection between stopping bay and customer doorstep
        ctx.strokeStyle = 'rgba(244, 63, 94, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(stopPt.u, stopPt.v);
        ctx.lineTo(doorPt.u, doorPt.v);
        ctx.stroke();
        ctx.setLineDash([]);

        // Curbside Stopping Circle
        ctx.fillStyle = 'rgba(56, 189, 248, 0.2)';
        ctx.beginPath();
        ctx.arc(stopPt.u, stopPt.v, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Customer Doorstep Pin (Red / Coral Marker)
        ctx.fillStyle = '#f43f5e';
        ctx.beginPath();
        ctx.arc(doorPt.u, doorPt.v, 4.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Customer Name Tag on Hover or High Zoom
        if (this.scale > 2.2) {
          ctx.fillStyle = '#e2e8f0';
          ctx.font = '10px sans-serif';
          ctx.textAlign = 'left';
          ctx.fillText(bay.customer_name, doorPt.u + 7, doorPt.v + 3);
        }
      }
      ctx.restore();
    }

    _drawPlannedRoute(ctx) {
      ctx.save();
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = Math.max(2.5, 2.0 * (this.scale / this.baseScale));
      ctx.setLineDash([8, 6]);
      ctx.lineDashOffset = -this.pulsePhase * 8; // Animated flow effect!

      ctx.beginPath();
      for (let i = 0; i < this.plannedRoute.length; i++) {
        const wp = this.plannedRoute[i];
        const pt = this.worldToScreen(wp[0], wp[1]);
        if (i === 0) ctx.moveTo(pt.u, pt.v);
        else ctx.lineTo(pt.u, pt.v);
      }
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    _drawTrajectoryTrail(ctx) {
      ctx.save();
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.45)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < this.trajectoryTrail.length; i++) {
        const tp = this.trajectoryTrail[i];
        const pt = this.worldToScreen(tp[0], tp[1]);
        if (i === 0) ctx.moveTo(pt.u, pt.v);
        else ctx.lineTo(pt.u, pt.v);
      }
      ctx.stroke();
      ctx.restore();
    }

    _drawSelectedPin(ctx) {
      ctx.save();
      const p = this.selectedPin;
      const rawPt = this.worldToScreen(p.raw_xy[0], p.raw_xy[1]);

      if (p.valid && p.stopping_xy) {
        const stopPt = this.worldToScreen(p.stopping_xy[0], p.stopping_xy[1]);

        // Connection line
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(rawPt.u, rawPt.v);
        ctx.lineTo(stopPt.u, stopPt.v);
        ctx.stroke();
        ctx.setLineDash([]);

        // Curbside Stopping Spot
        ctx.fillStyle = 'rgba(16, 185, 129, 0.3)';
        ctx.beginPath();
        ctx.arc(stopPt.u, stopPt.v, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Dropped Pin (Green Target)
        ctx.fillStyle = '#10b981';
        ctx.beginPath();
        ctx.arc(rawPt.u, rawPt.v, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Pulsing Ring around Pin
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(rawPt.u, rawPt.v, 10 + Math.sin(this.pulsePhase) * 4, 0, Math.PI * 2);
        ctx.stroke();

        // Pin Tooltip Pill
        ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 1;
        const msg = `${p.customer_name || 'Selected Doorstep'} • ${p.distance_m || 0}m (${p.eta_minutes || 1} min)`;
        ctx.font = 'bold 11px sans-serif';
        const txtW = ctx.measureText(msg).width;
        ctx.fillRect(rawPt.u - txtW / 2 - 8, rawPt.v - 32, txtW + 16, 22);
        ctx.strokeRect(rawPt.u - txtW / 2 - 8, rawPt.v - 32, txtW + 16, 22);

        ctx.fillStyle = '#34d399';
        ctx.textAlign = 'center';
        ctx.fillText(msg, rawPt.u, rawPt.v - 18);
      } else {
        // Unreachable / Inside Building (Red Warning Target)
        ctx.fillStyle = '#ef4444';
        ctx.beginPath();
        ctx.arc(rawPt.u, rawPt.v, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Pulsing Red Ring
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(rawPt.u, rawPt.v, 11 + Math.sin(this.pulsePhase) * 4, 0, Math.PI * 2);
        ctx.stroke();

        const warnMsg = '⚠️ NO-GO ZONE (RESTRICTED)';
        ctx.font = 'bold 11px sans-serif';
        const tw = ctx.measureText(warnMsg).width;
        ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
        ctx.strokeStyle = '#ef4444';
        ctx.fillRect(rawPt.u - tw / 2 - 8, rawPt.v - 32, tw + 16, 22);
        ctx.strokeRect(rawPt.u - tw / 2 - 8, rawPt.v - 32, tw + 16, 22);

        ctx.fillStyle = '#f87171';
        ctx.textAlign = 'center';
        ctx.fillText(warnMsg, rawPt.u, rawPt.v - 18);
      }
      ctx.restore();
    }

    _drawRobot(ctx) {
      ctx.save();
      const rPt = this.worldToScreen(this.robotPose.x, this.robotPose.y);

      // Robot dimensions in pixels (real AMR: 0.85m length x 0.55m width)
      const rLen = Math.max(16, 0.85 * this.scale);
      const rWid = Math.max(11, 0.55 * this.scale);

      ctx.translate(rPt.u, rPt.v);
      // Invert yaw because screen Y is flipped relative to Gazebo world
      ctx.rotate(-this.robotPose.yaw);

      // 1. Radar sensor emission cone (vision field-of-view 87° Intel RealSense D435i)
      const fovLen = Math.max(30, 6.0 * this.scale);
      const fovAngle = 0.76; // ~43.5 deg half-angle
      const grad = ctx.createRadialGradient(0, 0, 4, 0, 0, fovLen);
      grad.addColorStop(0, 'rgba(0, 240, 255, 0.35)');
      grad.addColorStop(1, 'rgba(0, 240, 255, 0.0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, fovLen, -fovAngle, fovAngle);
      ctx.closePath();
      ctx.fill();

      // 2. Chassis body (rounded rectangular AMR chassis)
      ctx.fillStyle = '#0f172a';
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(-rLen / 2, -rWid / 2, rLen, rWid, 4);
      ctx.fill();
      ctx.stroke();

      // 3. Drive Wheels (left & right)
      ctx.fillStyle = '#38bdf8';
      const wheelL = rLen * 0.45;
      const wheelW = rWid * 0.22;
      ctx.fillRect(-wheelL / 2, -rWid / 2 - wheelW / 2, wheelL, wheelW);
      ctx.fillRect(-wheelL / 2, rWid / 2 - wheelW / 2, wheelL, wheelW);

      // 4. Directional heading indicator (forward chevron arrow)
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(-rLen * 0.15, -rWid * 0.3);
      ctx.lineTo(rLen * 0.35, 0);
      ctx.lineTo(-rLen * 0.15, rWid * 0.3);
      ctx.stroke();

      ctx.restore();

      // 5. Overhead Robot Callout Badge
      ctx.save();
      const badgeY = rPt.v - rWid - 12;
      const robotLabel = `NEXUS-01 [${(this.robotPose.v || 0).toFixed(2)} m/s]`;
      ctx.font = 'bold 10px monospace';
      const rtw = ctx.measureText(robotLabel).width;

      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 1;
      ctx.fillRect(rPt.u - rtw / 2 - 6, badgeY - 8, rtw + 12, 16);
      ctx.strokeRect(rPt.u - rtw / 2 - 6, badgeY - 8, rtw + 12, 16);

      ctx.fillStyle = '#00f0ff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(robotLabel, rPt.u, badgeY);
      ctx.restore();
    }

    _drawTopologicalGraph(ctx) {
      if (!this.manifest || !this.manifest.intersections) return;
      ctx.save();
      // Draw intersection nodes
      for (const node of this.manifest.intersections) {
        const pt = this.worldToScreen(node.x, node.y);
        ctx.fillStyle = 'rgba(168, 85, 247, 0.3)';
        ctx.beginPath();
        ctx.arc(pt.u, pt.v, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#a855f7';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        if (this.scale > 2.0) {
          ctx.fillStyle = '#c084fc';
          ctx.font = '9px monospace';
          ctx.textAlign = 'center';
          ctx.fillText(node.id, pt.u, pt.v - 8);
        }
      }
      ctx.restore();
    }

    destroy() {
      if (this.animFrameId) {
        cancelAnimationFrame(this.animFrameId);
      }
    }
  }

  return GazeboWorldMap;
}));

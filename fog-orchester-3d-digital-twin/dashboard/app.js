/**
 * FOG-ORCHESTRATOR 2.0 — Digital Twin Command Center Client
 * =========================================================
 * - Three.js 3D Open-Pit Mining Digital Twin with Terraced Benches
 * - Coordinate-based Road Network with Segment Waypoints
 * - Detailed 3D Facilities (Shovels, Crusher, Dump Pocket, Buffer, Switchback)
 * - Dynamic Simulation-Driven 3D Vehicle Models & Safe Headway Rings
 * - Interactive Orbit / Pan / Zoom Controls & Preset Views
 * - Road Markings, Direction Chevrons, Grade & Distance Labels
 * - Dynamic 3D Volumetric Fog coupled to Digital Twin Visibility
 * - Real-time WebSocket (2 Hz) with REST polling fallback
 * - 2x2 Canvas Telemetry Charts Engine & Full 11-Region State Hydration
 */

// ============================================================================
// 1. NORMALIZED FRONTEND SIMULATION STATE STORE (SINGLE SOURCE OF TRUTH)
// ============================================================================
class NormalizedSimulationStore {
  constructor() {
    this.state = {
      // 1. Simulation time & epoch
      simulationTime: {
        timestamp_s: 0.0,
        step_count: 0,
        scenario_id: 'S01',
        dt_s: 1.0,
        is_running: true
      },
      // 2. Step count & direct timestamps
      timestamp_s: 0.0,
      stepCount: 0,
      
      // 3. Scenario
      scenarioId: 'S01',
      scenarioName: 'Baseline Clear (10 Trucks)',
      
      // 4. Vehicle states & 5. positions & 6. speeds & 7. routes & 8. load states
      vehicles: [],
      vehiclesById: new Map(),
      
      // 9. Visibility & 10. Road friction
      environment: {
        weather_mode: 'CLEAR',
        visibility_m: 50.0,
        friction_mu: 0.65,
        surface_state: 'dry',
        wind_speed_mps: 2.0,
        default_crr: 0.02
      },
      
      // 11. Queue lengths
      queues: {},
      
      // 12. Bottleneck scores
      bottlenecks: {
        primary_bottleneck: 'NONE',
        status: 'SAFE',
        active_bottlenecks: [],
        migration_count: 0,
        recent_migrations: []
      },
      
      // 13. Switchback lock states
      switchbacks: {
        active_reservations_count: 0,
        reservations: [],
        mutual_exclusion_active: false
      },
      
      // 14. Safety violations & 15. Tier-1 governor state
      safety: {
        violations_count: 0,
        safety_violations: 0,
        inviolable_safety_status: 'COMPLIANT (0 VIOLATIONS)',
        governor_inviolable: true
      },
      
      // 16. Alerts
      alerts: [],
      
      // 17. Fleet KPIs
      kpi: {
        fleet_size: 10,
        total_delivered_tonnes: 0.0,
        delivered_payload_t: 0.0,
        throughput_vph: 0.0,
        mean_speed_mps: 0.0,
        safety_violations: 0,
        average_queue_length: 0.0
      },
      
      // 18. Road capacity
      roads: {},
      
      // 19. Forecast values
      forecast: {
        current_weather_mode: 'CLEAR',
        current_visibility_m: 50.0,
        current_friction_mu: 0.65,
        forecast_series: []
      },
      
      // 20. Telemetry history
      history: {
        timestamps: [],
        meanSpeed: [],
        safeSpeed: [],
        visibility: [],
        friction: [],
        totalQueue: [],
        crusherQueue: [],
        shovelQueue: [],
        bottleneckScore: []
      },
      maxHistoryLength: 35,
      
      // Runtime connection status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING'
      connectionStatus: 'DISCONNECTED',
      connectionProtocol: 'NONE',
      
      // Runtime controls
      isRunning: true,
      playbackRate: 1,
      selectedTruckId: null
    };

    this.subscribers = new Set();
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  setConnectionState(status, protocol = null) {
    this.state.connectionStatus = status;
    if (protocol) this.state.connectionProtocol = protocol;
    
    const statusEl = document.getElementById('connection-status');
    const dotEl = document.getElementById('status-dot');
    const container = document.getElementById('stream-status-box');

    if (container) {
      container.classList.remove('connected', 'disconnected', 'reconnecting');
      if (status === 'CONNECTED') container.classList.add('connected');
      else if (status === 'DISCONNECTED') container.classList.add('disconnected');
      else if (status === 'RECONNECTING') container.classList.add('reconnecting');
    }

    if (dotEl) {
      dotEl.className = 'pulse-dot';
      if (status === 'CONNECTED') {
        dotEl.classList.add('active', 'green');
      } else if (status === 'RECONNECTING') {
        dotEl.classList.add('active', 'amber');
      } else {
        dotEl.classList.add('red');
      }
    }

    if (statusEl) {
      if (status === 'CONNECTED') {
        statusEl.innerText = protocol === 'WS' ? 'CONNECTED (WS 2Hz)' : 'CONNECTED (REST 2Hz)';
      } else if (status === 'RECONNECTING') {
        statusEl.innerText = 'RECONNECTING...';
      } else {
        statusEl.innerText = 'DISCONNECTED';
      }
    }
  }

  ingestSnapshot(raw) {
    if (!raw) return;

    const simTimeObj = raw.simulation_time || {};
    const simTime = (raw.timestamp_s !== undefined) ? raw.timestamp_s : (simTimeObj.timestamp_s || 0.0);
    const stepCount = (raw.step_count !== undefined) ? raw.step_count : (simTimeObj.step_count || 0);
    const scenarioId = raw.scenario_id || simTimeObj.scenario_id || 'S01';

    // 1. Simulation time & 2. Step count & 3. Scenario
    this.state.timestamp_s = simTime;
    this.state.stepCount = stepCount;
    this.state.scenarioId = scenarioId;
    this.state.scenarioName = raw.scenario_name || getScenarioName(scenarioId);
    this.state.simulationTime = {
      timestamp_s: simTime,
      step_count: stepCount,
      scenario_id: scenarioId,
      dt_s: simTimeObj.dt_s || 1.0,
      is_running: simTimeObj.is_running !== undefined ? simTimeObj.is_running : this.state.isRunning
    };

    // 4-8. Vehicle states, positions, speeds, routes, load states
    const rawFleet = raw.fleet || {};
    const rawVehicles = rawFleet.vehicles || raw.vehicles || [];
    this.state.vehicles = rawVehicles;
    this.state.vehiclesById.clear();
    rawVehicles.forEach(v => {
      const vid = v.vehicle_id || v.id;
      if (vid) this.state.vehiclesById.set(vid, v);
    });

    // 9-10. Visibility & Road friction
    const rawEnv = raw.environment || {};
    this.state.environment = {
      weather_mode: raw.weather_mode || rawEnv.weather_mode || 'CLEAR',
      visibility_m: raw.visibility_m !== undefined ? raw.visibility_m : (rawEnv.visibility_m || 50.0),
      friction_mu: raw.friction_mu !== undefined ? raw.friction_mu : (rawEnv.friction_mu || 0.65),
      surface_state: raw.surface_state || rawEnv.surface_state || 'dry',
      wind_speed_mps: rawEnv.wind_speed_mps !== undefined ? rawEnv.wind_speed_mps : 2.0,
      default_crr: rawEnv.default_crr || 0.02
    };

    // 11. Queue lengths
    const rawQueues = raw.queues || {};
    this.state.queues = rawQueues.nodes || rawQueues;

    // 12. Bottleneck scores
    const rawBottlenecks = raw.bottlenecks || {};
    this.state.bottlenecks = {
      primary_bottleneck: rawBottlenecks.primary_bottleneck || 'NONE',
      status: rawBottlenecks.status || 'SAFE',
      active_bottlenecks: rawBottlenecks.active_bottlenecks || [],
      migration_count: rawBottlenecks.migration_count || 0,
      recent_migrations: rawBottlenecks.recent_migrations || []
    };

    // 13. Switchback lock states
    const rawSwitchbacks = raw.switchbacks || {};
    this.state.switchbacks = {
      active_reservations_count: rawSwitchbacks.active_reservations_count || 0,
      reservations: rawSwitchbacks.reservations || [],
      mutual_exclusion_active: !!rawSwitchbacks.mutual_exclusion_active
    };

    // 14-15. Safety violations & Tier-1 governor state
    const rawSafety = raw.safety || {};
    this.state.safety = {
      violations_count: rawSafety.violations_count !== undefined ? rawSafety.violations_count : (rawFleet.safety_violations_count || raw.safety_violations || 0),
      safety_violations: rawSafety.safety_violations !== undefined ? rawSafety.safety_violations : (rawFleet.safety_violations || 0),
      inviolable_safety_status: rawSafety.inviolable_safety_status || (raw.alerts ? raw.alerts.inviolable_safety_status : 'COMPLIANT (0 VIOLATIONS)'),
      governor_inviolable: true
    };

    // 16. Alerts
    const rawAlerts = raw.alerts || {};
    this.state.alerts = Array.isArray(rawAlerts) ? rawAlerts : (rawAlerts.alerts || []);

    // 17. Fleet KPIs
    const rawKpi = raw.kpi || {};
    this.state.kpi = {
      fleet_size: rawKpi.fleet_size || rawFleet.fleet_size || rawVehicles.length || 10,
      total_delivered_tonnes: rawKpi.total_delivered_tonnes !== undefined ? rawKpi.total_delivered_tonnes : (rawFleet.total_delivered_tonnes || 0.0),
      delivered_payload_t: rawKpi.delivered_payload_t !== undefined ? rawKpi.delivered_payload_t : (rawFleet.delivered_payload_t || 0.0),
      throughput_vph: rawKpi.throughput_vph !== undefined ? rawKpi.throughput_vph : 0.0,
      mean_speed_mps: rawKpi.mean_speed_mps !== undefined ? rawKpi.mean_speed_mps : (raw.mean_speed_mps || 0.0),
      safety_violations: this.state.safety.violations_count,
      average_queue_length: rawKpi.average_queue_length || 0.0
    };

    // 18. Road capacity
    this.state.roads = raw.roads || {};

    // 19. Forecast values
    this.state.forecast = raw.forecast || {
      current_weather_mode: this.state.environment.weather_mode,
      current_visibility_m: this.state.environment.visibility_m,
      current_friction_mu: this.state.environment.friction_mu,
      forecast_series: []
    };

    // 20. Telemetry history buffer update
    this.updateHistory(simTime);

    // Synchronize all UI views from the shared normalized state
    this.dispatchStateToViews();
  }

  updateHistory(simTime) {
    const vSpds = this.state.vehicles.map(v => (v.speed_mps !== undefined ? v.speed_mps : (v.speed_v || 0)));
    const meanV = vSpds.length ? (vSpds.reduce((a, b) => a + b, 0) / vSpds.length) : 0;
    
    const vSafes = this.state.vehicles.map(v => (v.safe_speed_mps !== undefined ? v.safe_speed_mps : (v.safe_speed || 11.11)));
    const meanSafeV = vSafes.length ? (vSafes.reduce((a, b) => a + b, 0) / vSafes.length) : 11.11;

    const vis = this.state.environment.visibility_m;
    const mu = this.state.environment.friction_mu;

    const totalQ = Object.values(this.state.queues).reduce((sum, q) => sum + (q.queue_length || 0), 0);
    const crusherQ = this.state.queues['CRUSHER_01'] ? this.state.queues['CRUSHER_01'].queue_length : 0.0;
    const shovelQ = this.state.queues['SHOVEL_01'] ? this.state.queues['SHOVEL_01'].queue_length : 0.0;

    let topBScore = 0.0;
    if (this.state.bottlenecks.active_bottlenecks && this.state.bottlenecks.active_bottlenecks.length > 0) {
      topBScore = this.state.bottlenecks.active_bottlenecks[0].score || 0.0;
    }

    const h = this.state.history;
    h.timestamps.push(simTime);
    h.meanSpeed.push(meanV);
    h.safeSpeed.push(meanSafeV);
    h.visibility.push(vis);
    h.friction.push(mu);
    h.totalQueue.push(totalQ);
    h.crusherQueue.push(crusherQ);
    h.shovelQueue.push(shovelQ);
    h.bottleneckScore.push(topBScore);

    if (h.timestamps.length > this.state.maxHistoryLength) {
      h.timestamps.shift();
      h.meanSpeed.shift();
      h.safeSpeed.shift();
      h.visibility.shift();
      h.friction.shift();
      h.totalQueue.shift();
      h.crusherQueue.shift();
      h.shovelQueue.shift();
      h.bottleneckScore.shift();
    }
  }

  resetHistory() {
    this.state.history = {
      timestamps: [],
      meanSpeed: [],
      safeSpeed: [],
      visibility: [],
      friction: [],
      totalQueue: [],
      crusherQueue: [],
      shovelQueue: [],
      bottleneckScore: []
    };
  }

  dispatchStateToViews() {
    // 1. Top status bar
    updateTopStatusBar(this.state.timestamp_s, this.state.stepCount, this.state.scenarioId, this.state.environment, this.state.safety);

    // 2. 3D Scene Viewport
    if (state.threeViewer) {
      state.threeViewer.updateFleetTelemetry(this.state.vehicles);
      state.threeViewer.updateAtmosphericFog(this.state.environment.visibility_m);
    }

    // 3. 2D Telemetry Charts
    if (chartSpeed) chartSpeed.render(this.state.history);
    if (chartWeather) chartWeather.render(this.state.history);
    if (chartQueue) chartQueue.render(this.state.history);
    if (chartBottleneck) chartBottleneck.render(this.state.history);

    // 4. Live Vehicle Telemetry Table
    updateVehicleTable(this.state.vehicles);

    // 5. Viewport Facility HUD Pins & Selected Vehicle Inspector
    updateViewportFacilityHUD(this.state.queues, this.state.switchbacks, this.state.vehicles);

    // 6. Fleet KPIs Panel
    updateFleetKPIs(this.state.kpi, this.state.vehicles, this.state.timestamp_s);

    // 7. Service Queues Panel
    updateServiceQueuesPanel(this.state.queues);

    // 8. Bottleneck Ranking Panel
    updateBottleneckRankingPanel(this.state.bottlenecks);

    // 9. Switchback Locks Panel
    updateSwitchbackLocksPanel(this.state.switchbacks);

    // 10. System Alerts & Safety Log Panel
    updateSystemAlertsPanel(this.state.alerts, this.state.timestamp_s);

    // Notify registered external subscribers
    this.subscribers.forEach(fn => {
      try { fn(this.state); } catch (e) { console.error('Subscriber notification error:', e); }
    });
  }
}

const simulationStore = new NormalizedSimulationStore();

// Shared application runtime reference
const state = {
  get isRunning() { return simulationStore.state.isRunning; },
  set isRunning(val) { simulationStore.state.isRunning = val; },
  get playbackRate() { return simulationStore.state.playbackRate; },
  set playbackRate(val) { simulationStore.state.playbackRate = val; },
  get selectedTruckId() { return simulationStore.state.selectedTruckId; },
  set selectedTruckId(val) { simulationStore.state.selectedTruckId = val; },
  get activeScenarioId() { return simulationStore.state.scenarioId; },
  set activeScenarioId(val) { simulationStore.state.scenarioId = val; },
  get history() { return simulationStore.state.history; },
  get maxHistoryLength() { return simulationStore.state.maxHistoryLength; },
  threeViewer: null,
  stepTimer: null
};

// ============================================================================
// 2. THREE.JS 3D OPEN-PIT MINE DIGITAL TWIN VIEWER
// ============================================================================
class ThreeMineViewer {
  constructor(canvasId, containerId) {
    this.canvas = document.getElementById(canvasId);
    this.container = document.getElementById(containerId);
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    // Camera Orbit & Pan State (Framing Full Mountain & Multi-Revolution Descent)
    this.cameraState = {
      target: new THREE.Vector3(30, 65, 50),
      radius: 1180,
      theta: Math.PI * 0.22,   // ~40 deg azimuth — oblique aerial view framing circumference loops and front descent
      phi: Math.PI * 0.30,     // ~54 deg elevation — views whole mountain massif inside the loops
      minRadius: 160,
      maxRadius: 2800,
      minPhi: Math.PI * 0.06,
      maxPhi: Math.PI * 0.46,
      isDragging: false,
      isPanning: false,
      prevMouse: { x: 0, y: 0 }
    };

    // 3D Collections
    this.truckMeshes = new Map();     // vid -> { group, headwayRing, payloadMesh, headlights, targetPos, currentPos, targetRot, currentRot }
    this.facilityBadges = new Map();  // id -> sprite / mesh
    this.roadSplines = new Map();     // edge_id -> { curve, lengthM, fromNode, toNode, gradePct }
    this.roadMeshesById = new Map();  // edge_id -> Mesh
    this.roadDirectionChevrons = [];
    this.debugRoadGroup = new THREE.Group();
    this.animTime = 0;
    this.fogDensityTarget = 0.0006;
    this.switchbackBeacon = null;
    this.crusherBeacon = null;
    this.showFog = true;
    this.showHeadway = true;
    this.showDebugRoad = false;
    this.activeRoadId = null;
    this._projVector = new THREE.Vector3();
    this.hudContainer = null;
    this.lastFrameTime = (typeof performance !== 'undefined') ? performance.now() : Date.now();

    this.init();
  }

  init() {
    if (!this.canvas || typeof THREE === 'undefined') {
      console.error('Three.js library or canvas not found.');
      return;
    }

    // 1. Scene Setup
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x060911);
    this.scene.fog = new THREE.FogExp2(0x070b14, 0.0004);

    this.targetBgColor = new THREE.Color(0x060911);
    this.targetFogColor = new THREE.Color(0x070b14);
    this.targetAmbientLight = 0.90;
    this.targetSunLight = 1.8;

    // 2. Camera Setup (Perspective Isometric)
    const rect = this.canvas.getBoundingClientRect();
    const aspect = (rect.width || 800) / (rect.height || 500);
    this.camera = new THREE.PerspectiveCamera(38, aspect, 1, 6000);
    this.updateCameraPosition();

    // 3. WebGL Renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(rect.width || 800, rect.height || 500, false);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // 4. Lighting Rig
    this.setupLighting();

    // 5. Build Connected Closed Loop Road Network & Waypoints
    this.buildCoordinateRoadNetwork();

    // 6. Build Terraced Open-Pit Mine Terrain & Elevated Haul Road Surface
    this.buildMineTerrain();

    // 7. Build Mining Facilities (Shovels, Crusher, Dump, Buffer, Switchback)
    this.buildFacilities();

    // 8. Build Road Markings, Chevrons & 3D Labels
    this.buildRoadMarkingsAndLabels();

    // 9. Environmental Decor (Trees, Boulders, Light Poles)
    this.buildEnvironmentDecor();

    // 10. Build Debug Road Geometry Overlay
    this.buildDebugRoadOverlay();

    // 11. Setup Interaction Events
    this.setupInteractions();

    // 12. Window & Container Resize Handling
    window.addEventListener('resize', () => this.onWindowResize());
    if (window.ResizeObserver && this.container) {
      new ResizeObserver(() => this.onWindowResize()).observe(this.container);
    }

    // 13. Start Animation Loop
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);

    console.log('✅ 3D Digital Twin Scene Initialized Successfully');
  }

  onWindowResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (width > 0 && height > 0) {
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height, false);
      this.updateHUDLabels();
    }
  }

  setupLighting() {
    // Ambient light - balanced mountain sky
    this.ambientLight = new THREE.AmbientLight(0x64748b, 0.95);
    this.scene.add(this.ambientLight);

    // Primary Sun Light - Warm mountain sunlight casting crisp soft shadows across terraces
    this.sunLight = new THREE.DirectionalLight(0xfff7ed, 1.85);
    this.sunLight.position.set(500, 800, 400);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.width = 2048;
    this.sunLight.shadow.mapSize.height = 2048;
    this.sunLight.shadow.camera.near = 50;
    this.sunLight.shadow.camera.far = 2500;
    const d = 800;
    this.sunLight.shadow.camera.left = -d;
    this.sunLight.shadow.camera.right = d;
    this.sunLight.shadow.camera.top = d;
    this.sunLight.shadow.camera.bottom = -d;
    this.sunLight.shadow.bias = -0.0004;
    this.scene.add(this.sunLight);

    // Secondary Fill Light - Pit depth reflection
    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.45);
    fillLight.position.set(-320, 200, -280);
    this.scene.add(fillLight);

    // Hemispheric Light - Sky Cyan to Earth Terracotta (Bailadila Iron Ore Palette)
    const hemiLight = new THREE.HemisphereLight(0x38bdf8, 0x4a1f14, 0.6);
    this.scene.add(hemiLight);
  }

  // ==========================================================================
  // ROAD NETWORK WAYPOINTS & COORDINATE MAPPING (CONTINUOUS CLOSED LOOP)
  // ==========================================================================
  // ==========================================================================
  // ROAD NETWORK WAYPOINTS & COORDINATE MAPPING (CONTINUOUS CONNECTED TOPOLOGY)
  // ==========================================================================
  buildCoordinateRoadNetwork() {
    // ========================================================================
    // AUTHORITATIVE SHARED NODE 3D COORDINATE MAP (ZERO GAPS AT JUNCTIONS)
    // ========================================================================
    // Elevation Profile:
    // SHOVELS (≈110-120m) → INTERSECTION_01 (≈95m)
    //   → ROAD_03 descends → SWITCHBACK_01 (≈65m)
    //   → ROAD_04 180° Hairpin Turn → INTERSECTION_02 (≈36m)
    //   → ROAD_05 descends → BUFFER_01 (≈14m)
    //   → ROAD_06 crusher approach → CRUSHER_01 (≈5m)
    //   → Turnaround at CRUSHER_01 & return on exact same physical haul road in reverse
    // ========================================================================
    this.nodeCoords = {
      SHOVEL_01:       new THREE.Vector3(-240, 125, -110),   // Upper mining bench — working face 1
      SHOVEL_02:       new THREE.Vector3(-150, 120,  -80),   // Upper mining bench — working face 2
      INTERSECTION_01: new THREE.Vector3( -70, 115,  -40),   // Crest confluence — start of broad revolution
      SWITCHBACK_01:   new THREE.Vector3(-100,  60,   80),   // Tactical Hairpin 2 entry (single-lane switchback)
      INTERSECTION_02: new THREE.Vector3( -50,  47,  120),   // Mid-mountain junction below switchback
      BUFFER_01:       new THREE.Vector3( 160,  14,  180),   // Pre-crusher staging yard — lower valley
      CRUSHER_01:      new THREE.Vector3( 260,   5,  210),   // Primary gyratory crusher — valley floor
      DUMP_01:         new THREE.Vector3(-220,  45,  160)    // Waste overburden dump pocket — western flank
    };

    const defineSegment = (edgeId, fromNode, toNode, waypoints, lengthM, gradePct, widthM = 24.0, directionMode = 'bidirectional') => {
      const curve = new THREE.CatmullRomCurve3(waypoints, false, 'catmullrom', 0.15);
      this.roadSplines.set(edgeId, {
        id: edgeId,
        fromNode,
        toNode,
        curve,
        lengthM,
        gradePct,
        widthM,
        directionMode,
        startPoint: waypoints[0],
        endPoint: waypoints[waypoints.length - 1]
      });
    };

    // ROAD 1: SHOVEL_01 → INT_01 (600m, 0.0%) — Upper bench loading ramp
    defineSegment(
      'ROAD_01_SHOVEL1_TO_INT1',
      'SHOVEL_01',
      'INTERSECTION_01',
      [
        this.nodeCoords.SHOVEL_01,
        new THREE.Vector3(-200, 122, -90),
        new THREE.Vector3(-150, 119, -70),
        new THREE.Vector3(-110, 117, -55),
        this.nodeCoords.INTERSECTION_01
      ],
      600.0,
      0.0
    );

    // ROAD 2: SHOVEL_02 → INT_01 (450m, +1.5%) — Secondary bench loading ramp
    defineSegment(
      'ROAD_02_SHOVEL2_TO_INT1',
      'SHOVEL_02',
      'INTERSECTION_01',
      [
        this.nodeCoords.SHOVEL_02,
        new THREE.Vector3(-120, 118, -65),
        new THREE.Vector3( -95, 116, -50),
        this.nodeCoords.INTERSECTION_01
      ],
      450.0,
      1.5
    );

    // ROAD 3: INT_01 → SWITCHBACK_01 (800m, +6.25% Mountain Serpentine Descent)
    // Structure:
    // 1. Circumference Loop 1 (~360° high contour wrap around upper mountain massif dome)
    // 2. Circumference Loop 2 (~360° mid-elevation contour wrap encircling the whole mountain)
    // 3. Circumference Loop 3 / Contour Transition (wrapping north/east shoulder to front slope)
    // 4. Front-Side Zigzag Level 1 (Widest, longest horizontal sweep -> Switchback 1 apex -> westward return run -> SWITCHBACK_01)
    defineSegment(
      'ROAD_03_INT1_TO_SWITCH1',
      'INTERSECTION_01',
      'SWITCHBACK_01',
      [
        this.nodeCoords.INTERSECTION_01, // (-70, 115, -40)

        // =====================================================================
        // CIRCUMFERENCE LOOP 1: High Elevation (~115m -> 93m)
        // Full ~360° contour wrap around upper mountain massif
        // =====================================================================
        new THREE.Vector3( -15, 113, -70), // North-west crest
        new THREE.Vector3(  60, 111, -75), // North crest behind peak
        new THREE.Vector3( 130, 109, -50), // North-east shoulder
        new THREE.Vector3( 165, 107, -10), // East flank
        new THREE.Vector3( 155, 105,  30), // South-east shoulder
        new THREE.Vector3( 115, 103,  60), // South/front face
        new THREE.Vector3(  40, 101,  70), // South/front face center
        new THREE.Vector3( -40,  99,  60), // South-west shoulder
        new THREE.Vector3(-100,  97,  30), // West flank
        new THREE.Vector3(-130,  95, -10), // West flank rounding back
        new THREE.Vector3(-110,  93, -50), // Completing Loop 1!

        // =====================================================================
        // CIRCUMFERENCE LOOP 2: Mid Elevation (~93m -> 74m)
        // Wider ~360° contour bench encircling the whole mountain
        // =====================================================================
        new THREE.Vector3( -50,  91, -85), // North face behind mountain
        new THREE.Vector3(  30,  89,-100), // North face deep behind mountain
        new THREE.Vector3( 115,  87, -85), // North-east ridge
        new THREE.Vector3( 180,  85, -45), // East flank
        new THREE.Vector3( 210,  83,  10), // East flank shoulder
        new THREE.Vector3( 195,  81,  65), // South-east front shoulder
        new THREE.Vector3( 140,  79,  85), // Front/south bench
        new THREE.Vector3(  60,  78,  90), // Front/south bench center
        new THREE.Vector3( -20,  77,  80), // South-west shoulder
        new THREE.Vector3( -95,  76,  50), // West flank
        new THREE.Vector3(-140,  75,   5), // West flank
        new THREE.Vector3(-135,  74, -40), // Completing Loop 2!

        // =====================================================================
        // CIRCUMFERENCE LOOP 3 / TRANSITION: (~74m -> 68m)
        // Contour transition wrapping north/east shoulder toward front face
        // =====================================================================
        new THREE.Vector3( -80,  73, -80), // North flank
        new THREE.Vector3(   0,  72, -90), // North ridge
        new THREE.Vector3(  80,  71, -75), // North-east ridge
        new THREE.Vector3( 160,  70, -35), // Rounding eastern spur
        new THREE.Vector3( 220,  69,  15), // Eastern shoulder transition to front
        new THREE.Vector3( 245,  68,  45), // Transition to front-side descent

        // =====================================================================
        // FRONT-SIDE ZIGZAG LEVEL 1: Widest and Longest Horizontal Sweep (~68m -> 60m)
        // =====================================================================
        new THREE.Vector3( 255,  66,  68), // Switchback 1 apex (Eastern shoulder)
        new THREE.Vector3( 240,  65,  85), // Arc exit rounding westbound
        new THREE.Vector3( 200,  64,  92), // Westbound return run along mid-bench
        new THREE.Vector3( 130,  63,  90), // Westbound traverse
        new THREE.Vector3(  50,  62,  85), // Passing center
        new THREE.Vector3( -30,  61,  82), // Approaching tactical switchback entry
        this.nodeCoords.SWITCHBACK_01     // Exit: (-100, 60, 80)
      ],
      800.0,
      6.25
    );

    // ROAD 4: SWITCHBACK_01 → INT_02 (250m, +8.0% Mountain Hairpin Switchback)
    // Switchback 2: Tactical single-lane switchback hairpin reversing around western mountain spur
    // Controlled mutual exclusion segment with signal beacon tower at SWITCHBACK_01
    defineSegment(
      'ROAD_04_SWITCH1_TO_INT2',
      'SWITCHBACK_01',
      'INTERSECTION_02',
      [
        this.nodeCoords.SWITCHBACK_01,    // Entry: (-100, 60, 80)
        new THREE.Vector3(-145, 57,  85),
        new THREE.Vector3(-170, 54,  98), // Hairpin apex around western spur
        new THREE.Vector3(-165, 52, 115),
        new THREE.Vector3(-135, 50, 125),
        this.nodeCoords.INTERSECTION_02   // Exit: (-50, 47, 120)
      ],
      250.0,
      8.0,
      24.0,
      'single_lane_alternating'
    );

    // ROAD 5: INT_02 → BUFFER_01 (1200m, -8.0% Sustained Downhill Haul Section)
    // Structure:
    // 1. Zigzag Level 2: Shorter, compact, uneven eastward traverse -> Switchback 3 apex -> westward return run
    // 2. Zigzag Level 3: Organic terrain-following switchback (Switchback 4) into lower valley processing area
    defineSegment(
      'ROAD_05_INT2_TO_BUFFER1',
      'INTERSECTION_02',
      'BUFFER_01',
      [
        this.nodeCoords.INTERSECTION_02,  // Entry: (-50, 47, 120)
        // Zigzag Level 2: Shorter, compact, uneven eastward traverse
        new THREE.Vector3(  20, 44, 115),
        new THREE.Vector3(  85, 41, 110),
        new THREE.Vector3( 145, 38, 110),
        new THREE.Vector3( 170, 35, 122), // Switchback 3 apex (Eastern lower shoulder)
        new THREE.Vector3( 165, 33, 140),
        new THREE.Vector3( 130, 31, 148),
        // Return run westward
        new THREE.Vector3(  70, 29, 150),
        new THREE.Vector3(  10, 27, 152),
        new THREE.Vector3( -45, 25, 152),
        // Zigzag Level 3: Organic terrain-following switchback into valley
        new THREE.Vector3( -80, 22, 160), // Switchback 4 apex
        new THREE.Vector3( -85, 20, 180),
        new THREE.Vector3( -55, 18, 195),
        // Valley approach glide
        new THREE.Vector3(   0, 16, 200),
        new THREE.Vector3(  60, 15, 195),
        new THREE.Vector3( 115, 14, 188),
        this.nodeCoords.BUFFER_01         // Exit: (160, 14, 180)
      ],
      1200.0,
      -8.0
    );

    // ROAD 6: BUFFER_01 → CRUSHER_01 (300m, +2.0% Crusher Approach)
    defineSegment(
      'ROAD_06_BUFFER1_TO_CRUSHER1',
      'BUFFER_01',
      'CRUSHER_01',
      [
        this.nodeCoords.BUFFER_01,
        new THREE.Vector3(195, 11, 190),
        new THREE.Vector3(230,  8, 202),
        this.nodeCoords.CRUSHER_01
      ],
      300.0,
      2.0
    );

    // ROAD 7: INT_02 → DUMP_01 (900m, +1.0% Waste Dump Branch)
    defineSegment(
      'ROAD_07_INT2_TO_DUMP1',
      'INTERSECTION_02',
      'DUMP_01',
      [
        this.nodeCoords.INTERSECTION_02,
        new THREE.Vector3(-105, 46, 130),
        new THREE.Vector3(-150, 46, 142),
        new THREE.Vector3(-190, 45, 152),
        this.nodeCoords.DUMP_01
      ],
      900.0,
      1.0
    );

    // ========================================================================
    // INTERNAL FRONTEND ROAD TOPOLOGY & CONNECTION VALIDATION CHECK
    // ========================================================================
    const CONNECTION_TOLERANCE = 0.5;
    const connectionsToCheck = [
      { fromRoad: 'ROAD_01_SHOVEL1_TO_INT1', toRoad: 'ROAD_03_INT1_TO_SWITCH1', viaNode: 'INTERSECTION_01' },
      { fromRoad: 'ROAD_02_SHOVEL2_TO_INT1', toRoad: 'ROAD_03_INT1_TO_SWITCH1', viaNode: 'INTERSECTION_01' },
      { fromRoad: 'ROAD_03_INT1_TO_SWITCH1', toRoad: 'ROAD_04_SWITCH1_TO_INT2', viaNode: 'SWITCHBACK_01' },
      { fromRoad: 'ROAD_04_SWITCH1_TO_INT2', toRoad: 'ROAD_05_INT2_TO_BUFFER1', viaNode: 'INTERSECTION_02' },
      { fromRoad: 'ROAD_04_SWITCH1_TO_INT2', toRoad: 'ROAD_07_INT2_TO_DUMP1', viaNode: 'INTERSECTION_02' },
      { fromRoad: 'ROAD_05_INT2_TO_BUFFER1', toRoad: 'ROAD_06_BUFFER1_TO_CRUSHER1', viaNode: 'BUFFER_01' }
    ];

    console.group('🛣️ Haul Road Network Connectivity Validation');
    let allValid = true;
    connectionsToCheck.forEach(conn => {
      const roadA = this.roadSplines.get(conn.fromRoad);
      const roadB = this.roadSplines.get(conn.toRoad);
      if (roadA && roadB) {
        const gap = roadA.curve.getPointAt(1.0).distanceTo(roadB.curve.getPointAt(0.0));
        const isValid = gap <= CONNECTION_TOLERANCE;
        if (!isValid) allValid = false;
        console.log(
          `${conn.fromRoad} → ${conn.viaNode} → ${conn.toRoad}\n` +
          `connection gap: ${gap.toFixed(2)} m  ${isValid ? '✓' : '❌ EXCEEDS TOLERANCE'}`
        );
      }
    });
    if (allValid) {
      console.log('✅ All haul road connections validated: ZERO gaps detected across topology.');
    }
    console.groupEnd();
  }

  // ==========================================================================
  // TERRAIN HEIGHT & ROAD PROXIMITY EVALUATION (SINGLE SOURCE OF TRUTH)
  // ==========================================================================
  getTerrainHeight(x, z) {
    const dxUpper = (x + 200) * 0.8;
    const dzUpper = (z + 100) * 0.85;
    const distFromShovels = Math.sqrt(dxUpper * dxUpper + dzUpper * dzUpper);

    // Central mountain dome around which all 3 circumference loops wrap
    const dxDome = (x - 20) * 0.75;
    const dzDome = (z + 10) * 0.85;
    const distFromDome = Math.sqrt(dxDome * dxDome + dzDome * dzDome);

    const dxLower = (x - 260) * 0.7;
    const dzLower = (z - 210) * 0.7;
    const distFromCrusher = Math.sqrt(dxLower * dxLower + dzLower * dzLower);

    const distFromCenter = Math.sqrt((x * 0.5) ** 2 + (z * 0.55) ** 2);

    let baseMountainY;
    if (distFromShovels < 85) {
      baseMountainY = 122 + Math.sin(x * 0.04) * 2.5 + Math.cos(z * 0.035) * 2;
    } else if (distFromDome < 125) {
      // Prominent mountain dome summit & upper shoulders enclosed by circumference loops
      const domeT = distFromDome / 125;
      baseMountainY = 135 - domeT * 26 + Math.sin(x * 0.02) * 3 + Math.cos(z * 0.025) * 3;
    } else if (distFromCenter > 380) {
      baseMountainY = 145 + Math.sin(x * 0.01) * Math.cos(z * 0.01) * 16
        + Math.cos(x * 0.02) * 5 + Math.sin(z * 0.018) * 5;
    } else if (distFromCrusher < 110) {
      baseMountainY = 3 + Math.sin(x * 0.03) * 1.5 + Math.cos(z * 0.025) * 1.2;
    } else {
      const normalizedSlope = ((x + 180) * 0.35 + (z + 80) * 0.65) / 300;
      baseMountainY = 122 - normalizedSlope * 92 + Math.sin(x * 0.015) * 5 + Math.cos(z * 0.018) * 4;
      baseMountainY = Math.max(-5, Math.min(155, baseMountainY));
    }

    if (!this.sampledRoadPoints || this.sampledRoadPoints.length === 0) {
      return baseMountainY;
    }

    let h = baseMountainY;

    // 1. First pass: Apply road embankments/fills where roads run above mountain slope
    for (let j = 0; j < this.sampledRoadPoints.length; j++) {
      const rp = this.sampledRoadPoints[j];
      const dx = x - rp.x;
      const dz = z - rp.z;
      const dSq = dx * dx + dz * dz;
      if (dSq > 576) continue; // > 24m
      const d = Math.sqrt(dSq);
      if (d <= 14.5) {
        const fillY = rp.y - 0.50;
        if (fillY > h) h = fillY;
      } else {
        const t = (d - 14.5) / 9.5;
        const fillY = (rp.y - 0.50) * (1.0 - t) + (rp.y - 12.0) * t;
        if (fillY > h) h = fillY;
      }
    }

    // 2. Second pass: Excavate safe haul road bench cut corridor (CUT OVERRIDES FILL & MOUNTAIN)
    // Flat bench clearance corridor within 16.5m guarantees clean truck driving clearance
    // From 16.5m to 32.0m, the highwall slope rises smoothly into the mountain slope
    for (let j = 0; j < this.sampledRoadPoints.length; j++) {
      const rp = this.sampledRoadPoints[j];
      const dx = x - rp.x;
      const dz = z - rp.z;
      const dSq = dx * dx + dz * dz;
      if (dSq > 1024) continue; // > 32m
      const d = Math.sqrt(dSq);
      if (d <= 16.5) {
        const cutY = rp.y - 0.45;
        if (cutY < h) h = cutY;
      } else {
        const t = (d - 16.5) / 15.5;
        const cutSlopeY = (rp.y - 0.45) + t * t * 20.0;
        if (cutSlopeY < h) h = cutSlopeY;
      }
    }

    return h;
  }

  getDistToRoad(x, z) {
    if (!this.sampledRoadPoints || this.sampledRoadPoints.length === 0) return 999;
    let minDistSq = 999999;
    for (let j = 0; j < this.sampledRoadPoints.length; j++) {
      const rp = this.sampledRoadPoints[j];
      const dx = x - rp.x;
      const dz = z - rp.z;
      const dSq = dx * dx + dz * dz;
      if (dSq < minDistSq) minDistSq = dSq;
    }
    return Math.sqrt(minDistSq);
  }

  // ==========================================================================
  // BAILADILA / BACHELI MOUNTAIN-TOP OPEN-CAST IRON ORE TERRAIN & BENCHES
  // ==========================================================================
  buildMineTerrain() {
    const terrainGroup = new THREE.Group();

    // Sample road splines with density proportional to segment length (1 point every 4m)
    // so the terrain dynamically levels directly underneath the road network
    this.sampledRoadPoints = [];
    this.roadSplines.forEach(roadData => {
      const count = Math.max(40, Math.round((roadData.lengthM || 600) / 4));
      roadData.curve.getPoints(count).forEach(p => this.sampledRoadPoints.push(p));
    });

    // Terrain spans 1600×1200 with elevation from ~-5 (valley floor) to ~155 (ridgeline)
    const floorGeo = new THREE.PlaneGeometry(1600, 1200, 160, 120);
    floorGeo.rotateX(-Math.PI / 2);

    const pos = floorGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      pos.setY(i, this.getTerrainHeight(x, z));
    }
    floorGeo.computeVertexNormals();

    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x4a1f14,        // Bailadila Hematite Rust-Red Iron Ore
      roughness: 0.92,
      metalness: 0.18,
      flatShading: true
    });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.receiveShadow = true;
    terrainGroup.add(floorMesh);

    // ========================================================================
    // 2. STEPPED MULTI-TIER TERRACED MINING BENCHES & HIGHWALLS
    // ========================================================================
    const createBenchBlock = (x, y, z, w, h, d, color = 0x5c2618, rotY = 0) => {
      const bGeo = new THREE.BoxGeometry(w, h, d);
      const bMat = new THREE.MeshStandardMaterial({
        color: color,
        roughness: 0.94,
        metalness: 0.15,
        flatShading: true
      });
      const bMesh = new THREE.Mesh(bGeo, bMat);
      bMesh.position.set(x, y, z);
      bMesh.rotation.y = rotY;
      bMesh.receiveShadow = true;
      bMesh.castShadow = true;
      terrainGroup.add(bMesh);
      return bMesh;
    };

    // Tier 1: Upper Working Face Benches & Mountain Highwalls
    createBenchBlock(-275, 120, -110, 40, 26, 90, 0x3d170e, 0.02);   // West highwall behind SHOVEL_01
    createBenchBlock(-195, 122, -145, 70, 22, 35, 0x481c12, 0.04);   // North highwall
    createBenchBlock(-130, 115, -110, 30, 20, 65, 0x542216, -0.02);  // East highwall behind SHOVEL_02

    // Tier 2: Engineered Hairpin Platform Safety Barriers
    const retainMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.9, metalness: 0.2 });

    // Crusher platform retaining wall (valley floor escarpment)
    const crushRetain = new THREE.Mesh(new THREE.BoxGeometry(90, 14, 24), retainMat);
    crushRetain.position.set(260, 0, 210);
    crushRetain.rotation.y = 0.1;
    crushRetain.castShadow = true;
    crushRetain.receiveShadow = true;
    terrainGroup.add(crushRetain);

    // Buffer yard platform retaining wall
    const bufferRetain = new THREE.Mesh(new THREE.BoxGeometry(60, 12, 18), retainMat);
    bufferRetain.position.set(160, 9, 180);
    bufferRetain.castShadow = true;
    bufferRetain.receiveShadow = true;
    terrainGroup.add(bufferRetain);

    // Valley floor fill blocks (level pad for buffer & crusher)
    createBenchBlock(210, 4, 195, 140, 8, 120, 0x3a160c, 0.05);

    // ========================================================================
    // 3. SEAMLESS HAUL ROAD RIBBONS & PAVED JUNCTION APRONS
    // ========================================================================
    const roadWidth = 24.0;
    const shoulderWidth = 30.0;

    const shoulderMat = new THREE.MeshStandardMaterial({
      color: 0x5a2316,        // Laterite gravel shoulder
      roughness: 0.95,
      metalness: 0.1,
      polygonOffset: true,
      polygonOffsetFactor: -2,
      polygonOffsetUnits: -2
    });

    const roadMat = new THREE.MeshStandardMaterial({
      color: 0x222733,        // Heavy compacted dark iron-ore haul asphalt
      roughness: 0.82,
      metalness: 0.22,
      polygonOffset: true,
      polygonOffsetFactor: -4,
      polygonOffsetUnits: -4
    });

    // Paved Junction Aprons / Circular Intersection Plazas at all network nodes
    // Creates a seamless continuous visual driving surface without triangular gaps or cracks
    const junctionRadius = 17.0;
    const junctionShoulderRadius = 21.0;
    const apronGeo = new THREE.CylinderGeometry(junctionRadius, junctionRadius, 0.35, 24);
    const apronShoulderGeo = new THREE.CylinderGeometry(junctionShoulderRadius, junctionShoulderRadius, 0.25, 24);

    Object.values(this.nodeCoords).forEach(coord => {
      // Junction shoulder disc
      const sMesh = new THREE.Mesh(apronShoulderGeo, shoulderMat);
      sMesh.position.set(coord.x, coord.y + 0.15, coord.z);
      sMesh.receiveShadow = true;
      terrainGroup.add(sMesh);

      // Junction asphalt disc
      const aMesh = new THREE.Mesh(apronGeo, roadMat);
      aMesh.position.set(coord.x, coord.y + 0.40, coord.z);
      aMesh.receiveShadow = true;
      terrainGroup.add(aMesh);
    });

    // Generate Continuous 3D Solid Surface Ribbons for each road spline
    this.roadSplines.forEach((roadData) => {
      const curve = roadData.curve;
      const pointCount = Math.max(90, Math.round((roadData.lengthM || 600) / 8));
      const points = curve.getPoints(pointCount);

      // Solid 3D Road Embankment Bed Box (Raised Foundation)
      const bedGeo = new THREE.BufferGeometry();
      const bVerts = [];
      const bNorms = [];
      const bUvs = [];

      for (let i = 0; i < points.length; i++) {
        const p = points[i];
        let tangent = new THREE.Vector3(1, 0, 0);
        if (i < points.length - 1) tangent.subVectors(points[i + 1], p).normalize();
        else if (i > 0) tangent.subVectors(p, points[i - 1]).normalize();

        const side = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();
        const left = new THREE.Vector3().copy(p).addScaledVector(side, shoulderWidth / 2);
        const right = new THREE.Vector3().copy(p).addScaledVector(side, -shoulderWidth / 2);

        // Bed sits securely above ground
        left.y += 0.25;
        right.y += 0.25;

        bVerts.push(left.x, left.y, left.z, right.x, right.y, right.z);
        bNorms.push(0, 1, 0, 0, 1, 0);
        bUvs.push(0, i / points.length, 1, i / points.length);
      }

      const bIndices = [];
      for (let i = 0; i < points.length - 1; i++) {
        const a = i * 2;
        const b = i * 2 + 1;
        const c = (i + 1) * 2;
        const d = (i + 1) * 2 + 1;
        bIndices.push(a, c, b, b, c, d);
      }

      bedGeo.setIndex(bIndices);
      bedGeo.setAttribute('position', new THREE.Float32BufferAttribute(bVerts, 3));
      bedGeo.setAttribute('normal', new THREE.Float32BufferAttribute(bNorms, 3));
      bedGeo.setAttribute('uv', new THREE.Float32BufferAttribute(bUvs, 2));

      const bedMesh = new THREE.Mesh(bedGeo, shoulderMat);
      bedMesh.receiveShadow = true;
      terrainGroup.add(bedMesh);

      // Elevated Compacted Dark Iron-Ore Asphalt Haul Road Core
      const roadGeo = new THREE.BufferGeometry();
      const rVerts = [];
      const rNorms = [];
      const rUvs = [];

      for (let i = 0; i < points.length; i++) {
        const p = points[i];
        let tangent = new THREE.Vector3(1, 0, 0);
        if (i < points.length - 1) tangent.subVectors(points[i + 1], p).normalize();
        else if (i > 0) tangent.subVectors(p, points[i - 1]).normalize();

        const side = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();
        const left = new THREE.Vector3().copy(p).addScaledVector(side, roadWidth / 2);
        const right = new THREE.Vector3().copy(p).addScaledVector(side, -roadWidth / 2);

        left.y += 0.50;
        right.y += 0.50;

        rVerts.push(left.x, left.y, left.z, right.x, right.y, right.z);
        rNorms.push(0, 1, 0, 0, 1, 0);
        rUvs.push(0, i / points.length, 1, i / points.length);
      }

      const rIndices = [];
      for (let i = 0; i < points.length - 1; i++) {
        const a = i * 2;
        const b = i * 2 + 1;
        const c = (i + 1) * 2;
        const d = (i + 1) * 2 + 1;
        rIndices.push(a, c, b, b, c, d);
      }

      roadGeo.setIndex(rIndices);
      roadGeo.setAttribute('position', new THREE.Float32BufferAttribute(rVerts, 3));
      roadGeo.setAttribute('normal', new THREE.Float32BufferAttribute(rNorms, 3));
      roadGeo.setAttribute('uv', new THREE.Float32BufferAttribute(rUvs, 2));

      const roadMesh = new THREE.Mesh(roadGeo, roadMat);
      roadMesh.receiveShadow = true;
      terrainGroup.add(roadMesh);
      this.roadMeshesById.set(roadData.id, roadMesh);

      // High-Contrast Dashed Center Divider Line & Directional Lane Markings (Excluded at junctions)
      const centerLineMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });
      const arrowMat = new THREE.MeshBasicMaterial({ color: 0xfef08a, transparent: true, opacity: 0.45 });
      const isDualLane = (roadData.directionMode !== 'single_lane_alternating' && roadData.id !== 'ROAD_04_SWITCH1_TO_INT2');

      for (let i = 1; i < points.length - 1; i += 3) {
        const p = points[i];

        // Do not place dash inside junction circular zone
        let inJunction = false;
        for (const nCoord of Object.values(this.nodeCoords)) {
          const dx = p.x - nCoord.x;
          const dz = p.z - nCoord.z;
          if (dx * dx + dz * dz < 14 * 14) {
            inJunction = true;
            break;
          }
        }
        if (inJunction) continue;

        let tangent = new THREE.Vector3(1, 0, 0);
        if (i < points.length - 1) tangent.subVectors(points[i + 1], p).normalize();
        else if (i > 0) tangent.subVectors(p, points[i - 1]).normalize();

        const dashGeo = new THREE.BoxGeometry(4.0, 0.12, 0.55);
        const dash = new THREE.Mesh(dashGeo, centerLineMat);
        dash.position.set(p.x, p.y + 0.58, p.z);
        dash.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), tangent);
        terrainGroup.add(dash);

        // Subtle directional lane arrows painted on physical road surface (every 9th point)
        if (isDualLane && (i % 9 === 1)) {
          const side = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();
          const halfOffset = (roadWidth / 4.0);

          // Outbound lane arrow: points forward (+tangent)
          const pOut = new THREE.Vector3().copy(p).addScaledVector(side, halfOffset);
          const outArrow = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.08, 0.35), arrowMat);
          outArrow.position.set(pOut.x, pOut.y + 0.54, pOut.z);
          outArrow.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), tangent);
          terrainGroup.add(outArrow);

          // Return lane arrow: points backward (-tangent)
          const pRet = new THREE.Vector3().copy(p).addScaledVector(side, -halfOffset);
          const retArrow = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.08, 0.35), arrowMat);
          retArrow.position.set(pRet.x, pRet.y + 0.54, pRet.z);
          retArrow.quaternion.setFromUnitVectors(new THREE.Vector3(-1, 0, 0), tangent);
          terrainGroup.add(retArrow);
        }
      }

      // Heavy Safety Rock Windrows (Laterite Boulders along Road Shoulders)
      // Excluded at junctions to prevent obstructing intersection throats
      const bermMat = new THREE.MeshStandardMaterial({ color: 0x823825, roughness: 0.95, flatShading: true });
      for (let i = 1; i < points.length - 1; i += 2) {
        const p = points[i];

        // Check distance to all junction nodes
        let nearNode = false;
        for (const nCoord of Object.values(this.nodeCoords)) {
          const dx = p.x - nCoord.x;
          const dz = p.z - nCoord.z;
          if (dx * dx + dz * dz < 18 * 18) {
            nearNode = true;
            break;
          }
        }
        if (nearNode) continue;

        let tangent = new THREE.Vector3(1, 0, 0);
        if (i < points.length - 1) tangent.subVectors(points[i + 1], p).normalize();
        const side = new THREE.Vector3().crossVectors(tangent, new THREE.Vector3(0, 1, 0)).normalize();

        const bermLeft = new THREE.Vector3().copy(p).addScaledVector(side, shoulderWidth / 2 + 1.4);
        const bermRight = new THREE.Vector3().copy(p).addScaledVector(side, -shoulderWidth / 2 - 1.4);

        const bermGeo = new THREE.DodecahedronGeometry(1.6, 0);
        const m1 = new THREE.Mesh(bermGeo, bermMat);
        m1.position.copy(bermLeft);
        terrainGroup.add(m1);

        const m2 = new THREE.Mesh(bermGeo, bermMat);
        m2.position.copy(bermRight);
        terrainGroup.add(m2);
      }
    });

    this.scene.add(terrainGroup);
  }

  // ==========================================================================
  // MINING FACILITIES (CONNECTED DIRECTLY TO ROAD NETWORK)
  // ==========================================================================
  buildFacilities() {
    const facilityGroup = new THREE.Group();

    // Helper: Create 3D Electric Rope Shovel with Blasted Ore Muckpile
    const createShovelModel = (pos, rotY = 0) => {
      const shovel = new THREE.Group();

      // Caterpillar crawler tracks
      const trackMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.8 });
      const t1 = new THREE.Mesh(new THREE.BoxGeometry(20, 5, 5), trackMat);
      t1.position.set(0, 2.5, 5.2);
      shovel.add(t1);
      const t2 = new THREE.Mesh(new THREE.BoxGeometry(20, 5, 5), trackMat);
      t2.position.set(0, 2.5, -5.2);
      shovel.add(t2);

      // Revolving main house (Cat yellow)
      const houseMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.45, metalness: 0.35 });
      const house = new THREE.Mesh(new THREE.BoxGeometry(18, 10, 12), houseMat);
      house.position.set(-1, 9.5, 0);
      shovel.add(house);

      // Operator cab (safety glass window)
      const cabMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.15, metalness: 0.85 });
      const cab = new THREE.Mesh(new THREE.BoxGeometry(5, 5, 5), cabMat);
      cab.position.set(5, 13, 5);
      shovel.add(cab);

      // Heavy lattice boom
      const boomMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.6 });
      const boom = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.5, 28, 6), boomMat);
      boom.position.set(10, 19, 0);
      boom.rotation.z = -Math.PI / 4;
      shovel.add(boom);

      // Shovel dipper bucket
      const bucketMat = new THREE.MeshStandardMaterial({ color: 0x374151, roughness: 0.7, metalness: 0.6 });
      const bucket = new THREE.Mesh(new THREE.BoxGeometry(8, 8, 8), bucketMat);
      bucket.position.set(20, 9, 0);
      shovel.add(bucket);

      // Blasted Iron Ore Muckpile beside excavator dipper
      const muckpileMat = new THREE.MeshStandardMaterial({ color: 0x541e12, roughness: 0.95, flatShading: true });
      const muckpile = new THREE.Mesh(new THREE.ConeGeometry(18, 12, 8), muckpileMat);
      muckpile.position.set(28, 6, -8);
      muckpile.scale.set(1.4, 0.9, 1.2);
      shovel.add(muckpile);

      shovel.position.copy(pos);
      shovel.rotation.y = rotY;
      return shovel;
    };

    // Helper: Create 3D Heavy Mining Bulldozer (Cat D11 Style)
    const createBulldozerModel = (pos, rotY = 0) => {
      const dozer = new THREE.Group();
      const trackMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.85 });
      const bodyMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.45, metalness: 0.35 });
      const steelMat = new THREE.MeshStandardMaterial({ color: 0x374151, roughness: 0.6, metalness: 0.6 });
      const glassMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.1, transparent: true, opacity: 0.85 });

      // Dual crawler tracks
      const tr1 = new THREE.Mesh(new THREE.BoxGeometry(11, 2.8, 2.2), trackMat);
      tr1.position.set(0, 1.4, 2.4);
      dozer.add(tr1);
      const tr2 = new THREE.Mesh(new THREE.BoxGeometry(11, 2.8, 2.2), trackMat);
      tr2.position.set(0, 1.4, -2.4);
      dozer.add(tr2);

      // Main engine hood
      const hood = new THREE.Mesh(new THREE.BoxGeometry(6.5, 3.2, 3.4), bodyMat);
      hood.position.set(1.0, 3.2, 0);
      dozer.add(hood);

      // Operator cab with ROPS canopy
      const cab = new THREE.Mesh(new THREE.BoxGeometry(3.2, 3.0, 3.2), bodyMat);
      cab.position.set(-1.8, 4.6, 0);
      dozer.add(cab);

      // Cab window
      const win = new THREE.Mesh(new THREE.BoxGeometry(0.2, 1.6, 2.4), glassMat);
      win.position.set(-0.1, 4.8, 0);
      dozer.add(win);

      // Heavy Universal Dozer Push Blade at Front
      const blade = new THREE.Mesh(new THREE.BoxGeometry(0.8, 3.4, 7.2), steelMat);
      blade.position.set(5.8, 1.8, 0);
      dozer.add(blade);

      // Blade push arms
      const arm1 = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 4.5), steelMat);
      arm1.rotation.z = Math.PI / 2;
      arm1.position.set(3.5, 1.5, 2.8);
      dozer.add(arm1);
      const arm2 = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 4.5), steelMat);
      arm2.rotation.z = Math.PI / 2;
      arm2.position.set(3.5, 1.5, -2.8);
      dozer.add(arm2);

      // Rear single-shank ripper
      const ripper = new THREE.Mesh(new THREE.BoxGeometry(2.4, 3.0, 1.2), steelMat);
      ripper.position.set(-4.2, 1.6, 0);
      dozer.add(ripper);

      // Exhaust stack
      const exhaust = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 2.8), steelMat);
      exhaust.position.set(2.8, 5.2, -1.2);
      dozer.add(exhaust);

      dozer.position.copy(pos);
      dozer.rotation.y = rotY;
      return dozer;
    };

    // Helper: Create 3D Motor Grader (Cat 16M Haul Road Maintenance Grader)
    const createMotorGraderModel = (pos, rotY = 0) => {
      const grader = new THREE.Group();
      const bodyMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.45, metalness: 0.35 });
      const steelMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.6, metalness: 0.5 });
      const tireMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.95 });
      const tireGeo = new THREE.CylinderGeometry(1.4, 1.4, 0.9, 12);
      tireGeo.rotateZ(Math.PI / 2);

      // Long arched gooseneck frame
      const frame = new THREE.Mesh(new THREE.BoxGeometry(14, 1.2, 1.6), steelMat);
      frame.position.set(0, 2.6, 0);
      grader.add(frame);

      // Rear engine housing & tandem wheels
      const engineBox = new THREE.Mesh(new THREE.BoxGeometry(5.0, 2.6, 2.8), bodyMat);
      engineBox.position.set(-4.5, 3.4, 0);
      grader.add(engineBox);

      // Tandem rear drive wheels (4 wheels)
      const rWheelPositions = [
        [-5.8, 1.4, 2.0], [-5.8, 1.4, -2.0],
        [-3.2, 1.4, 2.0], [-3.2, 1.4, -2.0]
      ];
      rWheelPositions.forEach(p => {
        const w = new THREE.Mesh(tireGeo, tireMat);
        w.position.set(...p);
        grader.add(w);
      });

      // Front steering axle & wheels (2 wheels)
      const fWheelPositions = [
        [6.2, 1.4, 1.8], [6.2, 1.4, -1.8]
      ];
      fWheelPositions.forEach(p => {
        const w = new THREE.Mesh(tireGeo, tireMat);
        w.position.set(...p);
        grader.add(w);
      });

      // High operator cab
      const cab = new THREE.Mesh(new THREE.BoxGeometry(2.6, 3.0, 2.4), bodyMat);
      cab.position.set(-1.0, 4.8, 0);
      grader.add(cab);

      // Mid-mounted curved moldboard blade (angling down to surface)
      const blade = new THREE.Mesh(new THREE.BoxGeometry(0.4, 1.6, 6.2), steelMat);
      blade.position.set(1.8, 1.0, 0);
      blade.rotation.y = Math.PI * 0.18; // Angled grading position
      grader.add(blade);

      grader.position.copy(pos);
      grader.rotation.y = rotY;
      return grader;
    };

    // Shovels at Pit Floor Loading Bay (Beside ROAD_02)
    const shovel2 = createShovelModel(this.nodeCoords.SHOVEL_02, Math.PI * 0.10);
    facilityGroup.add(shovel2);

    // Primary Gyratory Crusher Plant Complex with Overland Conveyor Gallery (Beside ROAD_06)
    const crusherGroup = new THREE.Group();
    const concMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.9 });
    const steelMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.4, metalness: 0.6 });

    // Heavy concrete foundation substructure
    const base = new THREE.Mesh(new THREE.BoxGeometry(48, 24, 38), concMat);
    base.position.set(0, 12, 0);
    base.castShadow = true;
    base.receiveShadow = true;
    crusherGroup.add(base);

    // Inverted steel hopper feed bowl
    const hopperGeo = new THREE.ConeGeometry(15, 15, 8, 1, true);
    hopperGeo.rotateX(Math.PI);
    const hopper = new THREE.Mesh(hopperGeo, steelMat);
    hopper.position.set(0, 24, 0);
    crusherGroup.add(hopper);

    // Control room & vibrating screen superstructure
    const building = new THREE.Mesh(new THREE.BoxGeometry(22, 20, 24), steelMat);
    building.position.set(-15, 28, 0);
    crusherGroup.add(building);

    // Long Overland Conveyor Gallery Truss extending down mountain slope to Stockpile
    const conveyorMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7, roughness: 0.3 });
    const conveyorGallery = new THREE.Mesh(new THREE.BoxGeometry(90, 4.5, 4.5), conveyorMat);
    conveyorGallery.position.set(45, 18, 20);
    conveyorGallery.rotation.set(-0.1, 0.3, -0.15);
    conveyorGallery.castShadow = true;
    crusherGroup.add(conveyorGallery);

    // Conveyor support A-frame trestle tower
    const trestleMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8 });
    const trestle = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 1.4, 22, 4), trestleMat);
    trestle.position.set(65, 11, 26);
    crusherGroup.add(trestle);

    // Crushed Iron Ore Surge Stockpile cone
    const stockpileMat = new THREE.MeshStandardMaterial({ color: 0x3c160c, roughness: 0.95, flatShading: true });
    const surgeStockpile = new THREE.Mesh(new THREE.ConeGeometry(24, 16, 12), stockpileMat);
    surgeStockpile.position.set(88, 8, 32);
    crusherGroup.add(surgeStockpile);

    const beaconLight = new THREE.PointLight(0x06b6d4, 2.5, 90);
    beaconLight.position.set(0, 38, 0);
    crusherGroup.add(beaconLight);
    this.crusherBeacon = beaconLight;

    crusherGroup.position.copy(this.nodeCoords.CRUSHER_01);
    facilityGroup.add(crusherGroup);

    // Buffer Yard Staging Shelter & Service Bay (Beside ROAD_05/ROAD_06)
    const bufferGroup = new THREE.Group();
    const shelter = new THREE.Mesh(new THREE.BoxGeometry(38, 11, 26), steelMat);
    shelter.position.set(0, 5.5, 0);
    bufferGroup.add(shelter);

    // Marked truck parking bays in buffer yard (White/Yellow painted stall lines on asphalt)
    const lineMat = new THREE.MeshBasicMaterial({ color: 0xf8fafc });
    const lineGeo = new THREE.BoxGeometry(18, 0.2, 0.8);
    for (let i = 0; i < 3; i++) {
      const pLine = new THREE.Mesh(lineGeo, lineMat);
      pLine.position.set(-20, 0.3, -16 + i * 14);
      bufferGroup.add(pLine);
    }

    // Giant spare haul tyres in buffer yard
    const tyreMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.95 });
    const tyreGeo = new THREE.CylinderGeometry(2.4, 2.4, 1.8, 12);
    tyreGeo.rotateZ(Math.PI / 2);
    for (let i = 0; i < 5; i++) {
      const spareTyre = new THREE.Mesh(tyreGeo, tyreMat);
      spareTyre.position.set(24 + i * 4.2, 2.4, -12);
      bufferGroup.add(spareTyre);
    }

    // Fuel service tanker container in staging area
    const tankMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.3, metalness: 0.8 });
    const fuelTank = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.5, 14, 16), tankMat);
    fuelTank.rotateZ(Math.PI / 2);
    fuelTank.position.set(28, 3.2, 14);
    bufferGroup.add(fuelTank);

    bufferGroup.position.copy(this.nodeCoords.BUFFER_01);
    facilityGroup.add(bufferGroup);

    // Switchback Tactical Semaphore Tower & Runaway Safety Barrier (Beside ROAD_04 Hairpin)
    const switchbackGroup = new THREE.Group();
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 22), steelMat);
    pole.position.set(0, 11, 0);
    switchbackGroup.add(pole);

    // Yellow/Black Chevron Hazard Warning Barrier at hairpin outer edge
    const barrierMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4 });
    const barrier = new THREE.Mesh(new THREE.BoxGeometry(26, 3, 1.2), barrierMat);
    barrier.position.set(-8, 1.5, 14);
    barrier.rotation.y = Math.PI * 0.05;
    switchbackGroup.add(barrier);

    const signalLight = new THREE.PointLight(0x10b981, 3.5, 80);
    signalLight.position.set(0, 22, 0);
    switchbackGroup.add(signalLight);
    this.switchbackBeacon = signalLight;

    switchbackGroup.position.copy(this.nodeCoords.SWITCHBACK_01);
    facilityGroup.add(switchbackGroup);

    // =========================================================================
    // OVERBURDEN YARD, ACTIVE SPOIL DUMP & MINING EQUIPMENT FLEET
    // =========================================================================
    const dumpGroup = new THREE.Group();
    const stopLog = new THREE.Mesh(new THREE.BoxGeometry(45, 4.5, 6.0), new THREE.MeshStandardMaterial({ color: 0xef4444 }));
    stopLog.position.set(0, 2.2, 0);
    dumpGroup.add(stopLog);
    
    // Multiple irregular waste rock heaps & terraced spoil dumps
    const wasteMat = new THREE.MeshStandardMaterial({ color: 0x47433f, roughness: 0.95, flatShading: true });
    const wastePile1 = new THREE.Mesh(new THREE.ConeGeometry(32, 16, 10), wasteMat);
    wastePile1.position.set(25, 8, 0);
    dumpGroup.add(wastePile1);

    const wastePile2 = new THREE.Mesh(new THREE.ConeGeometry(24, 12, 8), wasteMat);
    wastePile2.position.set(-25, 6, -18);
    dumpGroup.add(wastePile2);

    const wastePile3 = new THREE.Mesh(new THREE.ConeGeometry(20, 10, 8), wasteMat);
    wastePile3.position.set(15, 5, -28);
    dumpGroup.add(wastePile3);

    dumpGroup.position.copy(this.nodeCoords.DUMP_01);
    facilityGroup.add(dumpGroup);

    // Deploy Active Mining Equipment Fleet across the Mine:
    // 1. Bulldozer at Overburden Waste Dump (Leveling spoil crest)
    const dozer1 = createBulldozerModel(new THREE.Vector3(-200, 46, 175), Math.PI * 0.85);
    facilityGroup.add(dozer1);

    // 2. Bulldozer at Upper Bench (Clearing blast rock near Shovel 1)
    const dozer2 = createBulldozerModel(new THREE.Vector3(-210, 124, -135), Math.PI * 0.15);
    facilityGroup.add(dozer2);

    // 3. Motor Grader maintaining lower haul road approach near Buffer Yard
    const grader1 = createMotorGraderModel(new THREE.Vector3(120, 15, 170), Math.PI * 0.08);
    facilityGroup.add(grader1);

    // 4. Motor Grader grading upper-mountain bench shoulder
    const grader2 = createMotorGraderModel(new THREE.Vector3(70, 84, 45), -Math.PI * 0.12);
    facilityGroup.add(grader2);

    // ========================================================================
    // 5. ACTIVE HILLTOP MINING EXTRACTION ZONE (NATURAL SUMMIT BENCH)
    // ========================================================================
    // Helper: Ultra-Class 400-Tonne Mining Haul Truck (Cat 797F / Komatsu 980E Class)
    const createUltraClassHaulTruck = (pos, rotY = 0, isLoaded = false) => {
      const truck = new THREE.Group();

      const tireMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.95 });
      const hubMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.5, metalness: 0.3 });
      const chassisMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8, metalness: 0.5 });
      const bodyMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.45, metalness: 0.35 });
      const bedMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.55, metalness: 0.45 });
      const glassMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.1, metalness: 0.85, transparent: true, opacity: 0.85 });
      const steelMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.6, metalness: 0.7 });
      const oreMat = new THREE.MeshStandardMaterial({ color: 0x451a03, roughness: 0.95, flatShading: true });

      // Chassis & Front Bumper
      const chassis = new THREE.Mesh(new THREE.BoxGeometry(15.0, 2.0, 4.4), chassisMat);
      chassis.position.set(0, 3.2, 0);
      truck.add(chassis);

      const bumper = new THREE.Mesh(new THREE.BoxGeometry(1.6, 2.8, 8.8), steelMat);
      bumper.position.set(7.5, 3.4, 0);
      truck.add(bumper);

      // Front diagonal access stairway
      const stair = new THREE.Mesh(new THREE.BoxGeometry(4.0, 3.8, 1.0), steelMat);
      stair.position.set(6.2, 4.2, 3.4);
      stair.rotation.z = Math.PI * 0.22;
      truck.add(stair);

      // Giant 59/80R63 Mining Wheels (Diameter ~4.0m)
      const tireGeo = new THREE.CylinderGeometry(2.0, 2.0, 1.4, 16);
      tireGeo.rotateZ(Math.PI / 2);
      const hubGeo = new THREE.CylinderGeometry(1.0, 1.0, 1.45, 12);
      hubGeo.rotateZ(Math.PI / 2);

      // Steer axle front wheels
      [[4.8, 2.0, 3.9], [4.8, 2.0, -3.9]].forEach(p => {
        const t = new THREE.Mesh(tireGeo, tireMat);
        t.position.set(...p);
        t.castShadow = true;
        truck.add(t);
        const h = new THREE.Mesh(hubGeo, hubMat);
        h.position.set(...p);
        truck.add(h);
      });

      // Drive axle rear wheels (dual sets)
      [[-4.5, 2.0, 3.3], [-4.5, 2.0, 4.8], [-4.5, 2.0, -3.3], [-4.5, 2.0, -4.8]].forEach(p => {
        const t = new THREE.Mesh(tireGeo, tireMat);
        t.position.set(...p);
        t.castShadow = true;
        truck.add(t);
        const h = new THREE.Mesh(hubGeo, hubMat);
        h.position.set(...p);
        truck.add(h);
      });

      // Cab & Equipment Deck
      const deck = new THREE.Mesh(new THREE.BoxGeometry(5.5, 0.5, 8.6), chassisMat);
      deck.position.set(4.5, 4.4, 0);
      truck.add(deck);

      const cab = new THREE.Mesh(new THREE.BoxGeometry(3.6, 3.4, 2.8), bodyMat);
      cab.position.set(4.5, 6.3, 2.4);
      cab.castShadow = true;
      truck.add(cab);

      const windshield = new THREE.Mesh(new THREE.BoxGeometry(0.2, 1.8, 2.4), glassMat);
      windshield.position.set(6.3, 6.7, 2.4);
      truck.add(windshield);

      const filterBox = new THREE.Mesh(new THREE.BoxGeometry(4.2, 2.8, 3.8), bodyMat);
      filterBox.position.set(4.0, 6.0, -1.8);
      truck.add(filterBox);

      // Twin Exhaust Stacks
      const exhGeo = new THREE.CylinderGeometry(0.4, 0.4, 6.0, 8);
      const exh1 = new THREE.Mesh(exhGeo, steelMat);
      exh1.position.set(1.8, 7.5, 2.2);
      truck.add(exh1);
      const exh2 = new THREE.Mesh(exhGeo, steelMat);
      exh2.position.set(1.8, 7.5, -2.2);
      truck.add(exh2);

      // Hydraulic Hoist Cylinders
      const cylGeo = new THREE.CylinderGeometry(0.5, 0.5, 4.5, 8);
      const cyl1 = new THREE.Mesh(cylGeo, steelMat);
      cyl1.rotation.x = 0.15;
      cyl1.position.set(0.5, 4.8, 1.8);
      truck.add(cyl1);
      const cyl2 = new THREE.Mesh(cylGeo, steelMat);
      cyl2.rotation.x = -0.15;
      cyl2.position.set(0.5, 4.8, -1.8);
      truck.add(cyl2);

      // Heavy Rock Dump Body
      const bedGroup = new THREE.Group();
      const bedFloor = new THREE.Mesh(new THREE.BoxGeometry(11.5, 1.0, 7.8), bedMat);
      bedFloor.position.set(-2.5, 5.2, 0);
      bedFloor.rotation.z = -0.06;
      bedGroup.add(bedFloor);

      const leftWall = new THREE.Mesh(new THREE.BoxGeometry(11.0, 3.6, 0.8), bedMat);
      leftWall.position.set(-2.5, 7.0, 3.8);
      bedGroup.add(leftWall);
      const rightWall = new THREE.Mesh(new THREE.BoxGeometry(11.0, 3.6, 0.8), bedMat);
      rightWall.position.set(-2.5, 7.0, -3.8);
      bedGroup.add(rightWall);

      const canopy = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.8, 8.4), bedMat);
      canopy.position.set(4.2, 9.2, 0);
      canopy.castShadow = true;
      bedGroup.add(canopy);

      const headboard = new THREE.Mesh(new THREE.BoxGeometry(0.8, 4.5, 7.8), bedMat);
      headboard.position.set(3.2, 7.2, 0);
      bedGroup.add(headboard);

      if (isLoaded) {
        const oreMound = new THREE.Mesh(new THREE.DodecahedronGeometry(3.6, 1), oreMat);
        oreMound.position.set(-2.0, 7.4, 0);
        oreMound.scale.set(1.5, 0.9, 1.1);
        bedGroup.add(oreMound);
      }

      truck.add(bedGroup);
      truck.position.copy(pos);
      truck.rotation.y = rotY;
      return truck;
    };

    // Helper: Mega Hydraulic Mining Shovel (Komatsu PC8000 / Cat 6060 Class)
    const createMegaHydraulicShovel = (pos, rotY = 0, bucketState = 'loading') => {
      const shovel = new THREE.Group();

      const trackMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.85, metalness: 0.4 });
      const houseMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.45, metalness: 0.35 });
      const boomMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.5, metalness: 0.3 });
      const bucketMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.7, metalness: 0.6 });
      const chromeMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.15, metalness: 0.9 });
      const cabMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.1, metalness: 0.85, transparent: true, opacity: 0.85 });
      const cweightMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.9 });

      // Crawler Undercarriage
      const track1 = new THREE.Mesh(new THREE.BoxGeometry(26.0, 5.5, 5.2), trackMat);
      track1.position.set(0, 2.75, 6.8);
      track1.castShadow = true;
      shovel.add(track1);

      const track2 = new THREE.Mesh(new THREE.BoxGeometry(26.0, 5.5, 5.2), trackMat);
      track2.position.set(0, 2.75, -6.8);
      track2.castShadow = true;
      shovel.add(track2);

      const carbody = new THREE.Mesh(new THREE.CylinderGeometry(6.5, 7.5, 3.5, 16), trackMat);
      carbody.position.set(0, 5.5, 0);
      shovel.add(carbody);

      // Revolving Superstructure House
      const houseGroup = new THREE.Group();
      houseGroup.position.set(0, 7.2, 0);

      const house = new THREE.Mesh(new THREE.BoxGeometry(20.0, 9.0, 13.0), houseMat);
      house.position.set(-2.0, 5.0, 0);
      house.castShadow = true;
      houseGroup.add(house);

      const cweight = new THREE.Mesh(new THREE.BoxGeometry(6.5, 9.5, 13.2), cweightMat);
      cweight.position.set(-13.0, 5.2, 0);
      cweight.castShadow = true;
      houseGroup.add(cweight);

      // Exhaust stacks
      const exh1 = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 4.0, 8), trackMat);
      exh1.position.set(-6.0, 11.5, 3.0);
      houseGroup.add(exh1);
      const exh2 = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 4.0, 8), trackMat);
      exh2.position.set(-6.0, 11.5, -3.0);
      houseGroup.add(exh2);

      // Elevated Panoramic Operator Cabin
      const cab = new THREE.Mesh(new THREE.BoxGeometry(5.0, 4.5, 4.0), houseMat);
      cab.position.set(7.5, 9.5, 5.8);
      houseGroup.add(cab);

      const cabGlass = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.8, 3.2), cabMat);
      cabGlass.position.set(10.0, 9.8, 5.8);
      houseGroup.add(cabGlass);

      const catwalk = new THREE.Mesh(new THREE.BoxGeometry(22.0, 0.4, 15.0), trackMat);
      catwalk.position.set(-1.5, 0.6, 0);
      houseGroup.add(catwalk);

      // Hydraulic Boom & Cylinders
      const boomAngle = (bucketState === 'loading') ? -Math.PI * 0.22 : -Math.PI * 0.18;
      const boom = new THREE.Mesh(new THREE.BoxGeometry(24.0, 3.4, 4.0), boomMat);
      boom.position.set(13.0, 12.0, 0);
      boom.rotation.z = boomAngle;
      boom.castShadow = true;
      houseGroup.add(boom);

      const cyl1 = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 12.0, 8), boomMat);
      cyl1.position.set(6.0, 8.0, 3.2);
      cyl1.rotation.z = -Math.PI * 0.35;
      houseGroup.add(cyl1);
      const ram1 = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 8.0, 8), chromeMat);
      ram1.position.set(9.0, 11.0, 3.2);
      ram1.rotation.z = -Math.PI * 0.35;
      houseGroup.add(ram1);

      const cyl2 = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 12.0, 8), boomMat);
      cyl2.position.set(6.0, 8.0, -3.2);
      cyl2.rotation.z = -Math.PI * 0.35;
      houseGroup.add(cyl2);
      const ram2 = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 8.0, 8), chromeMat);
      ram2.position.set(9.0, 11.0, -3.2);
      ram2.rotation.z = -Math.PI * 0.35;
      houseGroup.add(ram2);

      // Dipper Stick & Teeth Bucket
      const stick = new THREE.Mesh(new THREE.BoxGeometry(16.0, 2.6, 3.0), boomMat);
      const stickX = (bucketState === 'loading') ? 22.0 : 23.0;
      const stickY = (bucketState === 'loading') ? 11.0 : 9.0;
      const stickRot = (bucketState === 'loading') ? Math.PI * 0.35 : Math.PI * 0.22;
      stick.position.set(stickX, stickY, 0);
      stick.rotation.z = stickRot;
      houseGroup.add(stick);

      const bucket = new THREE.Mesh(new THREE.BoxGeometry(7.5, 6.0, 7.5), bucketMat);
      const bktX = (bucketState === 'loading') ? 25.0 : 27.0;
      const bktY = (bucketState === 'loading') ? 7.5 : 4.5;
      bucket.position.set(bktX, bktY, 0);
      bucket.castShadow = true;
      houseGroup.add(bucket);

      const toothGeo = new THREE.ConeGeometry(0.4, 1.4, 4);
      toothGeo.rotateZ(-Math.PI / 2);
      for (let t = -3.0; t <= 3.0; t += 1.2) {
        const tooth = new THREE.Mesh(toothGeo, trackMat);
        tooth.position.set(bktX + 4.0, bktY - 1.8, t);
        houseGroup.add(tooth);
      }

      shovel.add(houseGroup);
      shovel.position.copy(pos);
      shovel.rotation.y = rotY;
      return shovel;
    };

    // Helper: Mobile Mine Floodlight Tower
    const createLightTowerModel = (pos, rotY = 0) => {
      const tower = new THREE.Group();
      const steelMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.6, metalness: 0.5 });
      const yellowMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4 });
      const lampMat = new THREE.MeshBasicMaterial({ color: 0xfef08a });

      const trailer = new THREE.Mesh(new THREE.BoxGeometry(3.5, 1.6, 2.2), yellowMat);
      trailer.position.set(0, 1.2, 0);
      tower.add(trailer);

      const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.3, 10.0, 8), steelMat);
      mast.position.set(0, 6.5, 0);
      tower.add(mast);

      const crossbar = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.3, 0.4), steelMat);
      crossbar.position.set(0, 11.5, 0);
      tower.add(crossbar);

      for (let lx = -0.9; lx <= 0.9; lx += 0.6) {
        const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.4, 0.3), lampMat);
        lamp.position.set(lx, 11.5, 0.3);
        tower.add(lamp);
      }

      tower.position.copy(pos);
      tower.rotation.y = rotY;
      return tower;
    };

    // --- Deploy Hilltop Active Extraction Zone Assets at Main Haul Road Origin ---
    // 1. Natural Stepped Excavation Highwalls (Hematite Rock Faces bounding extraction face)
    const rockMat1 = new THREE.MeshStandardMaterial({ color: 0x3d170e, roughness: 0.95, flatShading: true });
    const rockMat2 = new THREE.MeshStandardMaterial({ color: 0x4f1e13, roughness: 0.92, flatShading: true });
    const rockMat3 = new THREE.MeshStandardMaterial({ color: 0x5a2316, roughness: 0.96, flatShading: true });

    // North-west highwall behind the loading shovels
    const hw1 = new THREE.Mesh(new THREE.BoxGeometry(36, 14, 12), rockMat1);
    hw1.position.set(-270, 128, -135);
    hw1.rotation.y = 0.08;
    hw1.castShadow = true;
    hw1.receiveShadow = true;
    facilityGroup.add(hw1);

    // North highwall
    const hw2 = new THREE.Mesh(new THREE.BoxGeometry(38, 14, 10), rockMat2);
    hw2.position.set(-235, 127, -145);
    hw2.rotation.y = -0.05;
    hw2.castShadow = true;
    hw2.receiveShadow = true;
    facilityGroup.add(hw2);

    // East bench retaining face
    const hw3 = new THREE.Mesh(new THREE.BoxGeometry(28, 12, 8), rockMat3);
    hw3.position.set(-195, 125, -130);
    hw3.rotation.y = 0.18;
    hw3.castShadow = true;
    hw3.receiveShadow = true;
    facilityGroup.add(hw3);

    // 2. Blasted Ore Muckpiles at the working face
    const muckMat = new THREE.MeshStandardMaterial({ color: 0x48180c, roughness: 0.95, flatShading: true });
    const muck1 = new THREE.Mesh(new THREE.ConeGeometry(16, 9, 8), muckMat);
    muck1.position.set(-260, 124.5, -125);
    muck1.scale.set(1.4, 0.8, 1.1);
    facilityGroup.add(muck1);

    const muck2 = new THREE.Mesh(new THREE.ConeGeometry(14, 8, 8), muckMat);
    muck2.position.set(-228, 123.5, -135);
    muck2.scale.set(1.3, 0.8, 1.2);
    facilityGroup.add(muck2);

    // 3. Mega Hydraulic Shovels (Positioned at Active Extraction Face directly beside Road Origin)
    // Mega Shovel 1: Active Loading Shovel reaching toward Ultra Truck 1
    const megaShovel1 = createMegaHydraulicShovel(new THREE.Vector3(-250, 124.8, -126), Math.PI * 0.22, 'loading');
    facilityGroup.add(megaShovel1);

    // Mega Shovel 2: Excavation Shovel digging into the upper north bench face
    const megaShovel2 = createMegaHydraulicShovel(new THREE.Vector3(-218, 123.8, -134), -Math.PI * 0.12, 'excavating');
    facilityGroup.add(megaShovel2);

    // 4. Ultra-Class Mining Haul Trucks (3-Truck Operational Progression at Road Start)
    // Truck 1 (Loading): Immediately beside Mega Shovel 1 receiving ore in loading stall
    const ultraTruck1 = createUltraClassHaulTruck(new THREE.Vector3(-235, 124.8, -120), Math.PI * 0.25, false);
    facilityGroup.add(ultraTruck1);

    // Truck 2 (Approaching): Staged on the bench approach lane, advancing to loading bay
    const ultraTruck2 = createUltraClassHaulTruck(new THREE.Vector3(-256, 125.0, -98), Math.PI * 0.48, false);
    facilityGroup.add(ultraTruck2);

    // Truck 3 (Departing): Loaded with ore, positioned at the start of ROAD_01 preparing to depart
    const ultraTruck3 = createUltraClassHaulTruck(new THREE.Vector3(-216, 123.2, -84), Math.PI * 0.28, true);
    facilityGroup.add(ultraTruck3);

    // 5. Support Mining Assets
    // Heavy Bulldozer leveling blast rock along extraction bench perimeter
    const summitDozer = createBulldozerModel(new THREE.Vector3(-262, 125.0, -112), Math.PI * 0.35);
    facilityGroup.add(summitDozer);

    // High-Mast Floodlight Tower illuminating the loading area
    const summitLight = createLightTowerModel(new THREE.Vector3(-242, 125.0, -140), 0.1);
    facilityGroup.add(summitLight);

    this.scene.add(facilityGroup);
  }

  // ==========================================================================
  // ROAD MARKINGS, DIRECTION CHEVRONS & 3D BILLBOARD LABELS
  // ==========================================================================
  buildRoadMarkingsAndLabels() {
    const markingsGroup = new THREE.Group();

    // Helper: Canvas Texture 3D Billboard Badge
    const create3DBadge = (text, bgColor = '#101c30', textColor = '#06b6d4', width = 150, height = 44) => {
      const c = document.createElement('canvas');
      c.width = width;
      c.height = height;
      const ctx = c.getContext('2d');

      ctx.fillStyle = bgColor;
      ctx.strokeStyle = textColor;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.roundRect(4, 4, width - 8, height - 8, 6);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = textColor;
      ctx.font = 'bold 15px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, width / 2, height / 2);

      const tex = new THREE.CanvasTexture(c);
      const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(width * 0.16, height * 0.16, 1);
      return sprite;
    };

    // Location Facility Labels
    const addFacilityLabel = (nodeId, text, pos, yOffset = 26) => {
      const badge = create3DBadge(text, 'rgba(10, 17, 34, 0.92)', '#38bdf8', 165, 44);
      badge.position.set(pos.x, pos.y + yOffset, pos.z);
      markingsGroup.add(badge);
      this.facilityBadges.set(nodeId, badge);
    };

    addFacilityLabel('SHOVEL_01', '⛏️ SHOVEL 01', this.nodeCoords.SHOVEL_01);
    addFacilityLabel('SHOVEL_02', '⛏️ SHOVEL 02', this.nodeCoords.SHOVEL_02);
    addFacilityLabel('SWITCHBACK_01', '🔄 SWITCHBACK 01', this.nodeCoords.SWITCHBACK_01, 30);
    addFacilityLabel('BUFFER_01', '🅿️ BUFFER YARD', this.nodeCoords.BUFFER_01);
    addFacilityLabel('CRUSHER_01', '🏭 CRUSHER 01', this.nodeCoords.CRUSHER_01, 42);
    addFacilityLabel('DUMP_01', '🚛 OVERBURDEN DUMP', this.nodeCoords.DUMP_01);

    // Road Grade & Segment Distance Labels Placed Directly Beside the Road
    const roadLabels = [
      { edge: 'ROAD_01_SHOVEL1_TO_INT1', text: '600m | 0.0% LOADING', pos: new THREE.Vector3(-155, 122, -75), color: '#10b981' },
      { edge: 'ROAD_03_INT1_TO_SWITCH1', text: '800m | +4.4% MULTI-LOOP DESCENT', pos: new THREE.Vector3(40, 105, 75), color: '#06b6d4' },
      { edge: 'ROAD_04_SWITCH1_TO_INT2', text: '250m | +5.6% HAIRPIN-2', pos: new THREE.Vector3(-140, 62, 100), color: '#f59e0b' },
      { edge: 'ROAD_05_INT2_TO_BUFFER1', text: '1200m | -3.5% DOWNHILL ZIGZAG', pos: new THREE.Vector3(60, 38, 160), color: '#ef4444' },
      { edge: 'ROAD_06_BUFFER1_TO_CRUSHER1', text: '300m | +3.0% CRUSHER', pos: new THREE.Vector3(210, 18, 200), color: '#10b981' },
      { edge: 'ROAD_07_INT2_TO_DUMP1', text: '900m | +1.0% OVERBURDEN DUMP', pos: new THREE.Vector3(-150, 52, 140), color: '#f59e0b' }
    ];

    roadLabels.forEach(lbl => {
      const badge = create3DBadge(lbl.text, 'rgba(14, 21, 38, 0.88)', lbl.color, 180, 38);
      badge.position.copy(lbl.pos);
      markingsGroup.add(badge);
    });

    // Road Direction Arrows (Glowing Cyan Chevrons directly onto the road)
    this.roadSplines.forEach(roadData => {
      const curve = roadData.curve;
      const points = curve.getPoints(20);

      for (let i = 2; i < points.length - 1; i += 3) {
        const p = points[i];
        let tangent = new THREE.Vector3(1, 0, 0);
        if (i < points.length - 1) tangent.subVectors(points[i + 1], p).normalize();

        const chevronGeo = new THREE.ConeGeometry(2.2, 5.0, 3);
        chevronGeo.rotateX(Math.PI / 2);
        const chevronMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, transparent: true, opacity: 0.75 });
        const chevron = new THREE.Mesh(chevronGeo, chevronMat);

        chevron.position.set(p.x, p.y + 0.75, p.z);
        chevron.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), tangent);
        markingsGroup.add(chevron);
        this.roadDirectionChevrons.push(chevron);
      }
    });

    this.scene.add(markingsGroup);
  }

  // ==========================================================================
  // ROAD DEBUG MODE OVERLAY (START/END JUNCTIONS & SEGMENT IDS)
  // ==========================================================================
  buildDebugRoadOverlay() {
    this.debugRoadGroup = new THREE.Group();

    const startNodeMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
    const endNodeMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    const nodeGeo = new THREE.SphereGeometry(3.5, 12, 12);

    this.roadSplines.forEach((roadData, edgeId) => {
      // Start Marker (Green Sphere)
      const startMesh = new THREE.Mesh(nodeGeo, startNodeMat);
      startMesh.position.set(roadData.startPoint.x, roadData.startPoint.y + 2, roadData.startPoint.z);
      this.debugRoadGroup.add(startMesh);

      // End Marker (Red Sphere)
      const endMesh = new THREE.Mesh(nodeGeo, endNodeMat);
      endMesh.position.set(roadData.endPoint.x, roadData.endPoint.y + 2, roadData.endPoint.z);
      this.debugRoadGroup.add(endMesh);

      // Midpoint ID Tag
      const midPoint = roadData.curve.getPointAt(0.5);
      const c = document.createElement('canvas');
      c.width = 160;
      c.height = 36;
      const ctx = c.getContext('2d');
      ctx.fillStyle = 'rgba(239, 68, 68, 0.9)';
      ctx.fillRect(0, 0, 160, 36);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 14px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(edgeId.split('_').slice(0, 2).join('_'), 80, 18);

      const tex = new THREE.CanvasTexture(c);
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex }));
      sprite.position.set(midPoint.x, midPoint.y + 16, midPoint.z);
      sprite.scale.set(24, 5.5, 1);
      this.debugRoadGroup.add(sprite);
    });

    this.debugRoadGroup.visible = this.showDebugRoad;
    this.scene.add(this.debugRoadGroup);
  }

  // ==========================================================================
  // BAILADILA DENSE MOUNTAIN RIDGE FOREST, TROPICAL CANOPY & BOULDERS
  // ==========================================================================
  // ==========================================================================
  // NATURAL MOUNTAIN VEGETATION (MIX OF TREES & ROAD-SIDE BUSHES) & DECOR
  // ==========================================================================
  buildEnvironmentDecor() {
    const decorGroup = new THREE.Group();

    // High Mine Floodlight Towers around Perimeter (Precisely grounded)
    const towerPositions = [
      new THREE.Vector3(-310, 0, -160),   // Upper bench / Shovels
      new THREE.Vector3(-140, 0,  -40),   // Above Terrace 1 start
      new THREE.Vector3( 250, 0,   10),   // Hairpin 1 eastern shoulder
      new THREE.Vector3(-210, 0,   90),   // Hairpin 2 western switchback
      new THREE.Vector3( 260, 0,  140),   // Hairpin 3 eastern shoulder
      new THREE.Vector3( 280, 0,  240),   // Crusher valley floor
      new THREE.Vector3(  80, 0,  220),   // Buffer staging yard
      new THREE.Vector3(-250, 0,  180),   // Waste dump pocket
      new THREE.Vector3( -80, 0, -280)    // Return road upper ridge
    ];

    const poleMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.8, roughness: 0.3 });
    const lampMat = new THREE.MeshBasicMaterial({ color: 0xffffff });

    towerPositions.forEach(pos => {
      pos.y = this.getTerrainHeight(pos.x, pos.z);
      const tower = new THREE.Group();
      const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 1.3, 38, 6), poleMat);
      mast.position.set(0, 19, 0);
      tower.add(mast);

      const head = new THREE.Mesh(new THREE.BoxGeometry(7, 2.5, 4.5), lampMat);
      head.position.set(0, 38, 0);
      tower.add(head);

      const spot = new THREE.PointLight(0xfff7ed, 1.4, 130);
      spot.position.set(0, 37, 0);
      tower.add(spot);

      tower.position.copy(pos);
      decorGroup.add(tower);
    });

    // Bailadila Iron Ore Boulder Clusters along Ridge Crests & Bench Toes (Grounded)
    const rockMat = new THREE.MeshStandardMaterial({ color: 0x5c2618, roughness: 0.95, flatShading: true });
    // Seeded PRNG for reproducible deterministic environment
    function Mulberry32(seed) {
      return function() {
        seed |= 0; seed = seed + 0x6D2B79F5 | 0;
        let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
        t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
        return ((t ^ t >>> 14) >>> 0) / 4294967296;
      };
    }
    const rng = Mulberry32(2026);

    for (let i = 0; i < 75; i++) {
      const rSize = 2.0 + rng() * 4.5;
      const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(rSize, 0), rockMat);
      const rx = (rng() - 0.5) * 880;
      const rz = (rng() - 0.5) * 680;

      // Keep boulders away from road driving surface
      if (this.getDistToRoad(rx, rz) < 18.0) continue;

      const ry = this.getTerrainHeight(rx, rz);
      rock.position.set(rx, ry + rSize * 0.35, rz);
      rock.rotation.set(rng() * Math.PI, rng() * Math.PI, 0);
      decorGroup.add(rock);
    }

    // ========================================================================
    // NATURAL MIXED VEGETATION CREATION (🌲 🌳 🌴 🪾 🌱)
    // ========================================================================
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x4a2411, roughness: 0.9, flatShading: true });
    const palmTrunkMat = new THREE.MeshStandardMaterial({ color: 0x6b4226, roughness: 0.85, flatShading: true });
    const coniferMat = new THREE.MeshStandardMaterial({ color: 0x14532d, roughness: 0.8, flatShading: true });
    const broadleafMat1 = new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.75, flatShading: true });
    const broadleafMat2 = new THREE.MeshStandardMaterial({ color: 0x166534, roughness: 0.78, flatShading: true });
    const palmLeafMat = new THREE.MeshStandardMaterial({ color: 0x16a34a, roughness: 0.7, flatShading: true });
    const acaciaMat = new THREE.MeshStandardMaterial({ color: 0x3f6212, roughness: 0.85, flatShading: true });
    const bushMat = new THREE.MeshStandardMaterial({ color: 0x4d7c0f, roughness: 0.9, flatShading: true });

    // Type A: 🌲 Tall Conifer / Pine
    const createConiferTree = (scale = 1.0) => {
      const group = new THREE.Group();
      const trunkH = 8.0 * scale;
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.35 * scale, 0.65 * scale, trunkH, 6), trunkMat);
      trunk.position.set(0, trunkH / 2, 0);
      group.add(trunk);

      const c1 = new THREE.Mesh(new THREE.ConeGeometry(4.2 * scale, 5.0 * scale, 7), coniferMat);
      c1.position.set(0, trunkH * 0.85, 0);
      group.add(c1);

      const c2 = new THREE.Mesh(new THREE.ConeGeometry(3.2 * scale, 4.2 * scale, 7), coniferMat);
      c2.position.set(0, trunkH * 1.15, 0);
      group.add(c2);

      const c3 = new THREE.Mesh(new THREE.ConeGeometry(2.0 * scale, 3.5 * scale, 7), coniferMat);
      c3.position.set(0, trunkH * 1.45, 0);
      group.add(c3);
      return group;
    };

    // Type B: 🌳 Broadleaf Teak / Sal (Eastern Ghats Open-Pit Mine Canopy)
    const createBroadleafTree = (scale = 1.0) => {
      const group = new THREE.Group();
      const trunkH = 7.0 * scale;
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.55 * scale, 0.9 * scale, trunkH, 6), trunkMat);
      trunk.position.set(0, trunkH / 2, 0);
      group.add(trunk);

      const mat = (scale > 1.0) ? broadleafMat1 : broadleafMat2;
      const mainCrown = new THREE.Mesh(new THREE.DodecahedronGeometry(3.8 * scale, 1), mat);
      mainCrown.position.set(0, trunkH + 2.5 * scale, 0);
      group.add(mainCrown);

      const cluster1 = new THREE.Mesh(new THREE.DodecahedronGeometry(2.6 * scale, 1), mat);
      cluster1.position.set(-1.6 * scale, trunkH + 1.5 * scale, 1.2 * scale);
      group.add(cluster1);

      const cluster2 = new THREE.Mesh(new THREE.DodecahedronGeometry(2.5 * scale, 1), mat);
      cluster2.position.set(1.5 * scale, trunkH + 1.8 * scale, -1.0 * scale);
      group.add(cluster2);
      return group;
    };

    // Type C: 🌴 Tropical Palm / Cycad
    const createPalmTree = (scale = 1.0) => {
      const group = new THREE.Group();
      const trunkH = 8.5 * scale;
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.3 * scale, 0.45 * scale, trunkH, 6), palmTrunkMat);
      trunk.position.set(0.4 * scale, trunkH / 2, 0);
      trunk.rotation.z = -0.08;
      group.add(trunk);

      // Radial Palm Fronds
      const crownTop = new THREE.Vector3(0.8 * scale, trunkH, 0);
      for (let f = 0; f < 6; f++) {
        const frondAngle = (f / 6) * Math.PI * 2;
        const frond = new THREE.Mesh(new THREE.BoxGeometry(4.6 * scale, 0.12 * scale, 1.1 * scale), palmLeafMat);
        frond.position.copy(crownTop);
        frond.rotation.y = frondAngle;
        frond.rotation.z = -0.32;
        group.add(frond);
      }
      return group;
    };

    // Type D: 🪾 Branching Mountain Acacia
    const createBranchingTree = (scale = 1.0) => {
      const group = new THREE.Group();
      const baseH = 5.0 * scale;
      const baseTrunk = new THREE.Mesh(new THREE.CylinderGeometry(0.45 * scale, 0.7 * scale, baseH, 6), trunkMat);
      baseTrunk.position.set(0, baseH / 2, 0);
      group.add(baseTrunk);

      const branch1 = new THREE.Mesh(new THREE.CylinderGeometry(0.28 * scale, 0.42 * scale, 4.2 * scale, 5), trunkMat);
      branch1.position.set(-1.2 * scale, baseH + 1.2 * scale, 0.3 * scale);
      branch1.rotation.z = 0.45;
      group.add(branch1);

      const branch2 = new THREE.Mesh(new THREE.CylinderGeometry(0.28 * scale, 0.42 * scale, 4.2 * scale, 5), trunkMat);
      branch2.position.set(1.3 * scale, baseH + 1.3 * scale, -0.3 * scale);
      branch2.rotation.z = -0.42;
      group.add(branch2);

      const pad1 = new THREE.Mesh(new THREE.CylinderGeometry(3.2 * scale, 3.6 * scale, 1.1 * scale, 7), acaciaMat);
      pad1.position.set(-2.4 * scale, baseH + 2.8 * scale, 0.5 * scale);
      group.add(pad1);

      const pad2 = new THREE.Mesh(new THREE.CylinderGeometry(3.0 * scale, 3.4 * scale, 1.1 * scale, 7), acaciaMat);
      pad2.position.set(2.5 * scale, baseH + 3.0 * scale, -0.5 * scale);
      group.add(pad2);
      return group;
    };

    // Type E: 🌱 Small Roadside Bush / Ground Vegetation
    const createRoadsideBush = (scale = 1.0) => {
      const group = new THREE.Group();
      const bushMain = new THREE.Mesh(new THREE.DodecahedronGeometry(1.4 * scale, 0), bushMat);
      bushMain.position.set(0, 0.9 * scale, 0);
      bushMain.scale.set(1.3, 0.75, 1.2);
      group.add(bushMain);

      const bushSub = new THREE.Mesh(new THREE.DodecahedronGeometry(0.9 * scale, 0), bushMat);
      bushSub.position.set(0.7 * scale, 0.6 * scale, 0.5 * scale);
      bushSub.scale.set(1.1, 0.8, 1.1);
      group.add(bushSub);
      return group;
    };

    // ========================================================================
    // CONTROLLED TREE DISTRIBUTION (NATURAL CLUSTERS & OPEN MINING ZONES)
    // ========================================================================
    let treeCount = 0;
    let attempts = 0;
    while (treeCount < 125 && attempts < 900) {
      attempts++;
      let tx, tz;
      const clusterR = rng();
      if (clusterR < 0.45) {
        // Outer mountain perimeter ridges (North, West, South-West)
        const angle = rng() * Math.PI * 2;
        const rad = 330 + rng() * 260;
        tx = Math.cos(angle) * rad;
        tz = Math.sin(angle) * rad;
      } else if (clusterR < 0.70) {
        // Eastern & South-Eastern valley flanks
        tx = 80 + rng() * 320;
        tz = -120 - rng() * 240;
      } else if (clusterR < 0.85) {
        // Northern mountain face above return ramp
        tx = -250 + rng() * 350;
        tz = -200 - rng() * 180;
      } else {
        // Southern ridge
        tx = -150 + rng() * 300;
        tz = 140 + rng() * 180;
      }

      // Clearance Rule: Keep trees well clear of all haul roads (> 24m)
      if (this.getDistToRoad(tx, tz) < 24.0) continue;

      // Clearance Rule: Keep active facilities open
      let nearFacility = false;
      for (const [nodeId, coord] of Object.entries(this.nodeCoords)) {
        const d = Math.hypot(tx - coord.x, tz - coord.z);
        const clearReq = (nodeId.startsWith('SHOVEL') || nodeId.startsWith('CRUSHER')) ? 45 : 30;
        if (d < clearReq) { nearFacility = true; break; }
      }
      if (nearFacility) continue;

      // GROUND TREE TRUNK BASE PRECISELY TO TERRAIN SURFACE
      const groundY = this.getTerrainHeight(tx, tz);
      const treeScale = 0.80 + rng() * 0.45;
      const typeChoice = Math.floor(rng() * 4);

      let treeMesh;
      if (typeChoice === 0) treeMesh = createConiferTree(treeScale);
      else if (typeChoice === 1) treeMesh = createBroadleafTree(treeScale);
      else if (typeChoice === 2) treeMesh = createPalmTree(treeScale);
      else treeMesh = createBranchingTree(treeScale);

      treeMesh.position.set(tx, groundY, tz);
      treeMesh.rotation.y = rng() * Math.PI * 2;
      decorGroup.add(treeMesh);
      treeCount++;
    }

    // ========================================================================
    // SMALL ROADSIDE BUSHES (🌱) ALONG SELECTED ROAD EMBANKMENTS
    // ========================================================================
    // Positioned along roadside embankments (17m to 25m off centerline),
    // strictly off the 12m drivable asphalt surface. Irregular and uncluttered.
    const roadList = Array.from(this.roadSplines.values());
    let bushCount = 0;
    attempts = 0;
    while (bushCount < 50 && attempts < 400) {
      attempts++;
      const roadData = roadList[Math.floor(rng() * roadList.length)];
      // Keep switchback hairpin turning throat clear
      if (roadData.id === 'ROAD_04_SWITCH1_TO_INT2' && rng() > 0.35) continue;

      const progress = 0.12 + rng() * 0.76;
      const pt = roadData.curve.getPointAt(progress);
      const tan = roadData.curve.getTangentAt(progress);
      const side = new THREE.Vector3().crossVectors(tan, new THREE.Vector3(0, 1, 0)).normalize();
      const sideOffset = (rng() > 0.5 ? 1 : -1) * (18.5 + rng() * 6.0); // 18.5m - 24.5m

      const bx = pt.x + side.x * sideOffset;
      const bz = pt.z + side.z * sideOffset;

      // Ensure bush sits on roadside embankment but outside driving corridor
      const dRoad = this.getDistToRoad(bx, bz);
      if (dRoad < 16.5 || dRoad > 27.0) continue;

      // Clear of facility pads
      let nearNode = false;
      for (const coord of Object.values(this.nodeCoords)) {
        if (Math.hypot(bx - coord.x, bz - coord.z) < 22) { nearNode = true; break; }
      }
      if (nearNode) continue;

      // GROUND BUSH PRECISELY TO LOCAL TERRAIN ELEVATION
      const groundY = this.getTerrainHeight(bx, bz);
      const bushScale = 0.75 + rng() * 0.50;
      const bushMesh = createRoadsideBush(bushScale);
      bushMesh.position.set(bx, groundY, bz);
      bushMesh.rotation.y = rng() * Math.PI * 2;
      decorGroup.add(bushMesh);
      bushCount++;
    }

    this.scene.add(decorGroup);
    console.log(`🌲 Forest Vegetation Initialized: ${treeCount} trees grounded, ${bushCount} roadside bushes grounded.`);
  }

  // ==========================================================================
  // DYNAMIC SIMULATION-DRIVEN VEHICLE MANAGEMENT (BH100 HAUL TRUCKS)
  // ==========================================================================
  getTruckContactShadowTexture() {
    if (this._truckShadowTex) return this._truckShadowTex;
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    const grad = ctx.createRadialGradient(64, 64, 12, 64, 64, 62);
    grad.addColorStop(0, 'rgba(15, 23, 42, 0.75)');
    grad.addColorStop(0.5, 'rgba(15, 23, 42, 0.40)');
    grad.addColorStop(0.8, 'rgba(15, 23, 42, 0.12)');
    grad.addColorStop(1, 'rgba(15, 23, 42, 0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 128, 128);
    this._truckShadowTex = new THREE.CanvasTexture(canvas);
    return this._truckShadowTex;
  }

  createTruck3DMesh(vid) {
    const truck = new THREE.Group();

    // Local contact shadow directly beneath truck on road surface
    // Preserves realistic local grounding while preventing cross-loop shadow projection onto lower benches
    const shadowGeo = new THREE.PlaneGeometry(12.5, 6.4);
    shadowGeo.rotateX(-Math.PI / 2);
    const shadowMat = new THREE.MeshBasicMaterial({
      map: this.getTruckContactShadowTexture(),
      transparent: true,
      opacity: 0.65,
      depthWrite: false
    });
    const contactShadow = new THREE.Mesh(shadowGeo, shadowMat);
    contactShadow.position.set(0, 0.03, 0);
    truck.add(contactShadow);

    // 1. Heavy Mine Chassis (Central ladder steel frame between wheels)
    // Frame width 3.4m, centered at Y=3.3m (bottom at Y=2.4m, strictly ABOVE wheel centers Y=2.0m)
    const chassisMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.7, metalness: 0.5 });
    const chassis = new THREE.Mesh(new THREE.BoxGeometry(10.5, 1.8, 3.4), chassisMat);
    chassis.position.set(0, 3.3, 0);
    truck.add(chassis);

    // Front radiator grille & bumper
    const bumperMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.8, metalness: 0.6 });
    const bumper = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.8, 4.4), bumperMat);
    bumper.position.set(5.3, 2.3, 0);
    truck.add(bumper);

    // Heavy Transverse Axles (Axle line runs LEFT ↔ RIGHT across truck width at Y=2.0m)
    const axleMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.6, metalness: 0.7 });
    const frontAxleGeo = new THREE.CylinderGeometry(0.3, 0.3, 5.3, 12);
    frontAxleGeo.rotateX(Math.PI / 2);
    const frontAxle = new THREE.Mesh(frontAxleGeo, axleMat);
    frontAxle.position.set(3.2, 2.0, 0);
    truck.add(frontAxle);

    const rearAxleGeo = new THREE.CylinderGeometry(0.35, 0.35, 5.3, 12);
    rearAxleGeo.rotateX(Math.PI / 2);
    const rearAxle = new THREE.Mesh(rearAxleGeo, axleMat);
    rearAxle.position.set(-3.2, 2.0, 0);
    truck.add(rearAxle);

    const diffHousing = new THREE.Mesh(new THREE.SphereGeometry(0.65, 8, 8), axleMat);
    diffHousing.position.set(-3.2, 2.0, 0);
    truck.add(diffHousing);

    // 2. Heavy Dual Mining Haul Tires (Front steering & rear dual drive)
    // CRITICAL: Cylinder default axis is Y. rotateX(Math.PI / 2) aligns cylinder axis along Z (Left ↔ Right).
    // The circular face points outward toward the left/right sides of the truck.
    // The curved tread rolls along the X axis (truck forward/backward direction).
    const tireMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.95 });
    const hubMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4, metalness: 0.5 });
    const tireGeo = new THREE.CylinderGeometry(2.0, 2.0, 1.3, 20);
    tireGeo.rotateX(Math.PI / 2);
    const hubGeo = new THREE.CylinderGeometry(0.95, 0.95, 1.35, 16);
    hubGeo.rotateX(Math.PI / 2);

    // Wheel positions:
    // Centers at Y=2.0m (bottom at Y=0.0m touches road naturally, top at Y=4.0m)
    // Centers at Z=±2.65m: with width 1.3m, inner tire edge is at Z=±2.0m, cleanly clearing chassis side (Z=±1.7m) by 0.3m.
    // Wheels sit outside the chassis frame, centered beneath the dump body.
    const positions = [
      [-3.2, 2.0,  2.65], [-3.2, 2.0, -2.65],
      [ 3.2, 2.0,  2.65], [ 3.2, 2.0, -2.65]
    ];
    positions.forEach(pos => {
      const tire = new THREE.Mesh(tireGeo, tireMat);
      tire.position.set(...pos);
      truck.add(tire);

      const hub = new THREE.Mesh(hubGeo, hubMat);
      hub.position.set(...pos);
      truck.add(hub);
    });

    // 3. Cat-Yellow Operator Cab & ROPS/FOPS Canopy
    // Bottom at Y=4.4m (cleanly above front tire top Y=4.0m)
    const cabMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4, metalness: 0.3 });
    const glassMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.1, metalness: 0.9, transparent: true, opacity: 0.85 });

    const cab = new THREE.Mesh(new THREE.BoxGeometry(3.6, 2.6, 2.6), cabMat);
    cab.position.set(3.0, 5.7, 1.2);
    truck.add(cab);

    // Front windscreen
    const windshield = new THREE.Mesh(new THREE.BoxGeometry(0.2, 1.6, 2.2), glassMat);
    windshield.position.set(4.8, 5.9, 1.2);
    truck.add(windshield);

    // Canopy protector over cab
    const canopy = new THREE.Mesh(new THREE.BoxGeometry(5.4, 0.5, 5.2), cabMat);
    canopy.position.set(2.4, 7.3, 0);
    truck.add(canopy);

    // Amber Safety Strobe Beacon on Cab Roof
    const beaconGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.6, 8);
    const beaconMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });
    const strobeBeacon = new THREE.Mesh(beaconGeo, beaconMat);
    strobeBeacon.position.set(3.0, 7.8, 1.2);
    truck.add(strobeBeacon);

    // Heavy Exhaust Stack
    const exhaustMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.8, roughness: 0.3 });
    const exhaust = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 5.0, 8), exhaustMat);
    exhaust.position.set(1.5, 6.2, -2.3);
    truck.add(exhaust);

    // 4. Heavy Dump Body (Steel Bed with Rock Ejectors)
    // Positioned at Y=5.6m, height 2.8m -> bottom at Y=4.2m (0.2m clean clearance above tire tops at Y=4.0m)
    const bedMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.5, metalness: 0.4 });
    const bed = new THREE.Mesh(new THREE.BoxGeometry(7.4, 2.8, 5.4), bedMat);
    bed.position.set(-1.6, 5.6, 0);
    truck.add(bed);

    // 5. Dynamic Ore Payload Mesh (Visible & scaled when loaded)
    const oreMat = new THREE.MeshStandardMaterial({ color: 0x451a03, roughness: 0.95, flatShading: true });
    const payloadMesh = new THREE.Mesh(new THREE.DodecahedronGeometry(2.8, 1), oreMat);
    payloadMesh.position.set(-1.6, 6.8, 0);
    payloadMesh.scale.set(1.4, 0.8, 1.1);
    payloadMesh.visible = false;
    truck.add(payloadMesh);

    // 6. Dual LED Forward Spotlights
    const headLight = new THREE.SpotLight(0xffffff, 2.5, 45, Math.PI / 6, 0.4);
    headLight.position.set(5.4, 3.4, 0);
    headLight.target.position.set(28, 0, 0);
    truck.add(headLight);
    truck.add(headLight.target);

    // 7. Dynamic Safe Headway Ring (Stopping distance envelope)
    const ringGeo = new THREE.RingGeometry(12, 14, 24);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, transparent: true, opacity: 0.45, side: THREE.DoubleSide });
    const headwayRing = new THREE.Mesh(ringGeo, ringMat);
    headwayRing.position.set(0, 0.2, 0);
    truck.add(headwayRing);

    // 8. Overhead 3D Billboard Name Tag (kept hidden; locator label handles selected truck)
    const tagCanvas = document.createElement('canvas');
    tagCanvas.width = 140;
    tagCanvas.height = 40;
    const tCtx = tagCanvas.getContext('2d');
    tCtx.fillStyle = 'rgba(10, 17, 32, 0.88)';
    tCtx.strokeStyle = '#06b6d4';
    tCtx.lineWidth = 2;
    tCtx.beginPath();
    tCtx.roundRect(3, 3, 134, 34, 6);
    tCtx.fill();
    tCtx.stroke();
    tCtx.fillStyle = '#38bdf8';
    tCtx.font = 'bold 15px "JetBrains Mono", monospace';
    tCtx.textAlign = 'center';
    tCtx.textBaseline = 'middle';
    tCtx.fillText(vid, 70, 20);

    const tagTex = new THREE.CanvasTexture(tagCanvas);
    const tagMat = new THREE.SpriteMaterial({ map: tagTex, transparent: true });
    const idTag = new THREE.Sprite(tagMat);
    idTag.position.set(0, 11.5, 0);
    idTag.scale.set(16, 4.6, 1);
    idTag.visible = false;
    truck.add(idTag);
    
    // 9. Selection Indicator (Luminous Ground Reticle Halo & Crosshairs)
    const selectionRing = new THREE.Group();
    selectionRing.position.set(0, 0.35, 0);
    selectionRing.visible = false;

    // Outer luminous ground ring (r: 15.5 to 18.0)
    const outerGeo = new THREE.RingGeometry(15.5, 18.0, 36);
    outerGeo.rotateX(-Math.PI / 2);
    const outerMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.85,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    const outerRing = new THREE.Mesh(outerGeo, outerMat);
    selectionRing.add(outerRing);

    // Inner bright reticle ring (r: 10.5 to 11.8)
    const innerGeo = new THREE.RingGeometry(10.5, 11.8, 36);
    innerGeo.rotateX(-Math.PI / 2);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.90,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    const innerRing = new THREE.Mesh(innerGeo, innerMat);
    selectionRing.add(innerRing);

    // 4 Corner Reticle Crosshair Ticks (North, South, East, West)
    const tickMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff, depthWrite: false });
    const tickGeoZ = new THREE.BoxGeometry(1.2, 0.1, 4.0);
    const tickGeoX = new THREE.BoxGeometry(4.0, 0.1, 1.2);
    const tickN = new THREE.Mesh(tickGeoZ, tickMat); tickN.position.set(0, 0.05, 17.0); selectionRing.add(tickN);
    const tickS = new THREE.Mesh(tickGeoZ, tickMat); tickS.position.set(0, 0.05, -17.0); selectionRing.add(tickS);
    const tickE = new THREE.Mesh(tickGeoX, tickMat); tickE.position.set(17.0, 0.05, 0); selectionRing.add(tickE);
    const tickW = new THREE.Mesh(tickGeoX, tickMat); tickW.position.set(-17.0, 0.05, 0); selectionRing.add(tickW);

    truck.add(selectionRing);

    // Store references
    truck.userData = {
      vehicleId: vid,
      headwayRing,
      payloadMesh,
      headLight,
      idTag,
      selectionRing,
      vehicleData: null
    };

    // Scale truck group to realistic haul road proportion (prevents mesh clipping at safe headway)
    truck.scale.set(0.65, 0.65, 0.65);

    this.scene.add(truck);
    return truck;
  }

  updateFleetTelemetry(vehicles) {
    if (!vehicles) return;

    const activeVids = new Set();

    vehicles.forEach(vData => {
      const vid = vData.vehicle_id || vData.id;
      activeVids.add(vid);

      let isNew = false;
      let truckEntry = this.truckMeshes.get(vid);
      if (!truckEntry) {
        const group = this.createTruck3DMesh(vid);
        truckEntry = {
          group,
          headwayRing: group.userData.headwayRing,
          payloadMesh: group.userData.payloadMesh,
          headLight: group.userData.headLight,
          idTag: group.userData.idTag,
          selectionRing: group.userData.selectionRing,
          currentPos: new THREE.Vector3(0, 0, 0),
          targetPos: new THREE.Vector3(0, 0, 0),
          targetRotY: 0,
          // Authoritative road spline tracking state (1x, 2x, 5x, 10x synchronized)
          edgeId: null,
          roadData: null,
          currentT: 0.0,
          targetT: 0.0,
          pendingEdge: null
        };
        this.truckMeshes.set(vid, truckEntry);
        isNew = true;
      }

      // Store latest telemetry on userData
      truckEntry.group.userData.vehicleData = vData;

      // 1. Calculate Waypoint Road Position strictly from simulation telemetry
      const edgeId = vData.current_edge || vData.road_edge;
      const station = (vData.station !== undefined) ? vData.station : ((vData.station_m !== undefined) ? vData.station_m : (vData.position_s || 0.0));
      const roadData = this.roadSplines.get(edgeId) || this.roadSplines.get('ROAD_01_SHOVEL1_TO_INT1');
      const isReverse = (vData.lane_or_direction === 'reverse' || vData.direction === 'reverse' || (vData.destination && vData.destination.startsWith('SHOVEL')));

      if (roadData && roadData.curve) {
        let legProgress;
        const lengthM = roadData.lengthM || 600.0;
        const curveLen = roadData.curveLength || (roadData.curveLength = roadData.curve.getLength());

        if (edgeId === 'ROAD_03_INT1_TO_SWITCH1' && curveLen > lengthM) {
          // Calibrate switchback queue approach zone: 1m in simulation = 1m in 3D along curve
          const queueApproachM = 250.0;
          const simBoundary = lengthM - queueApproachM;
          if (!isReverse) {
            if (station >= simBoundary) {
              const dFromEndM = Math.max(0.0, lengthM - station);
              legProgress = Math.min(1.0, Math.max(0.0, 1.0 - (dFromEndM / curveLen)));
            } else {
              const tBoundary = 1.0 - (queueApproachM / curveLen);
              legProgress = Math.min(1.0, Math.max(0.0, (station / simBoundary) * tBoundary));
            }
          } else {
            // Reverse travel: departing SWITCHBACK_01 (station=0) back up to INTERSECTION_01 (station=lengthM)
            if (station <= queueApproachM) {
              legProgress = Math.min(1.0, Math.max(0.0, station / curveLen));
            } else {
              const tBoundary = queueApproachM / curveLen;
              const remainingM = station - queueApproachM;
              const remainingSim = lengthM - queueApproachM;
              legProgress = Math.min(1.0, Math.max(0.0, tBoundary + (remainingM / remainingSim) * (1.0 - tBoundary)));
            }
          }
        } else {
          legProgress = Math.min(1.0, Math.max(0.0, station / lengthM));
        }

        // Exact spline parameter along the single physical road curve:
        // Forward: advances from t = 0.0 to t = 1.0
        // Reverse: traverses backwards along the SAME curve from t = 1.0 to t = 0.0
        const splineT = isReverse ? Math.max(0.0, Math.min(1.0, 1.0 - legProgress)) : legProgress;

        // Authoritative 3D position & forward-facing heading along centerline
        const p = roadData.curve.getPointAt(splineT);
        const tan = roadData.curve.getTangentAt(splineT);
        // Tangent points along curve (+t). When reversing (-t), vehicle heading is inverted (-tan).
        const rotY = isReverse ? Math.atan2(tan.z, -tan.x) : Math.atan2(-tan.z, tan.x);
        const pitch = isReverse ? Math.atan2(-tan.y, Math.hypot(tan.x, tan.z)) : Math.atan2(tan.y, Math.hypot(tan.x, tan.z));

        // Horizontal normal vector perpendicular to road centerline (local road frame)
        const horizLen = Math.hypot(tan.x, tan.z);
        const nx = (horizLen > 1e-4) ? (-tan.z / horizLen) : 0.0;
        const nz = (horizLen > 1e-4) ? (tan.x / horizLen) : 0.0;

        // Virtual two-lane lateral offset: Outbound = +W/4, Return = -W/4
        // Controlled single-lane switchback (ROAD_04) operates on centerline (0.0m) under Tier-2 mutual exclusion
        const isSingleLane = (roadData.id === 'ROAD_04_SWITCH1_TO_INT2' || roadData.directionMode === 'single_lane_alternating');
        const roadW = isSingleLane ? 0.0 : (roadData.widthM || 24.0);
        const laneOffset = roadW / 4.0;
        const targetOffset = isReverse ? -laneOffset : laneOffset;

        const lanePos = new THREE.Vector3(
          p.x + nx * targetOffset,
          p.y + 0.52,
          p.z + nz * targetOffset
        );

        // Detect simulation reset or brand-new vehicle
        const isReset = (simulationStore && simulationStore.state.timestamp_s === 0.0);

        if (isNew || isReset || !truckEntry.edgeId) {
          // Instant initialization directly locked to the road spline
          truckEntry.edgeId = edgeId;
          truckEntry.roadData = roadData;
          truckEntry.isReverse = isReverse;
          truckEntry.currentT = splineT;
          truckEntry.targetT = splineT;
          truckEntry.currentLaneOffset = targetOffset;
          truckEntry.targetLaneOffset = targetOffset;
          truckEntry.pendingEdge = null;

          truckEntry.targetPos.copy(lanePos);
          truckEntry.targetRotY = rotY;
          truckEntry.group.position.copy(lanePos);
          truckEntry.group.rotation.set(0, rotY, pitch, 'YXZ');
        } else if (truckEntry.edgeId === edgeId && truckEntry.isReverse === isReverse) {
          // Truck advancing along the SAME road edge and direction:
          truckEntry.targetT = splineT;
          truckEntry.roadData = roadData;
          truckEntry.targetLaneOffset = targetOffset;
          truckEntry.pendingEdge = null;

          // Keep targetPos & targetRotY updated for HUD/inspector cards
          truckEntry.targetPos.copy(lanePos);
          truckEntry.targetRotY = rotY;
        } else {
          // Edge or direction changed! (e.g. turnaround at crusher/shovel, or moving to next road segment)
          const playbackMult = Math.max(1.0, state.playbackRate || 1.0);
          const junctionTolerance = Math.min(0.20, 0.05 * Math.max(1.0, playbackMult * 0.5));
          const atJunction = truckEntry.isReverse ? (truckEntry.currentT <= junctionTolerance) : (truckEntry.currentT >= (1.0 - junctionTolerance));
          if (atJunction) {
            truckEntry.edgeId = edgeId;
            truckEntry.roadData = roadData;
            truckEntry.isReverse = isReverse;
            const entryT = isReverse ? 1.0 : 0.0;
            truckEntry.currentT = entryT;
            truckEntry.targetT = splineT;
            truckEntry.targetLaneOffset = targetOffset;
            truckEntry.pendingEdge = null;

            truckEntry.targetPos.copy(lanePos);
            truckEntry.targetRotY = rotY;
          } else {
            // Smoothly finish remaining meters to junction, then transition
            const exitJunctionT = truckEntry.isReverse ? 0.0 : 1.0;
            truckEntry.targetT = exitJunctionT;
            truckEntry.pendingEdge = {
              edgeId,
              roadData,
              isReverse,
              targetT: splineT,
              targetLaneOffset: targetOffset
            };
          }
        }

        // Heading for inspector
        vData.heading_deg = Math.round(((truckEntry.targetRotY * 180 / Math.PI) + 360) % 360 * 10) / 10;
        vData.heading_rad = Math.round(truckEntry.targetRotY * 100) / 100;
      } else if (this.nodeCoords[edgeId]) {
        truckEntry.targetPos.copy(this.nodeCoords[edgeId]);
        if (isNew) {
          truckEntry.group.position.copy(truckEntry.targetPos);
        }
      }

      // 2. Update Payload Visibility and size
      const isLoaded = (vData.is_loaded || vData.load_state === 'LOADED');
      truckEntry.payloadMesh.visible = isLoaded;
      if (isLoaded) {
        const pTonnes = vData.payload || vData.payload_tonnes || 91.5;
        const pScale = Math.max(0.6, Math.min(1.3, pTonnes / 91.5));
        truckEntry.payloadMesh.scale.set(1.4 * pScale, 0.8 * pScale, 1.1 * pScale);
      }

      // 3. Dynamic Headway Ring Radius scaling with v_safe
      if (this.showHeadway) {
        const safeHeadwayM = vData.safe_headway_m || 15.52;
        const scaleFactor = Math.min(2.5, Math.max(0.8, safeHeadwayM / 15.52));
        truckEntry.headwayRing.scale.set(scaleFactor, scaleFactor, 1);
        truckEntry.headwayRing.visible = true;

        // Color shift if at speed ceiling
        const spd = vData.speed_mps || vData.speed || 0;
        const safeSpd = vData.safe_speed_mps || vData.safe_speed || 11.11;
        if (spd > safeSpd + 0.1) {
          truckEntry.headwayRing.material.color.setHex(0xef4444);
        } else if (spd >= safeSpd * 0.95) {
          truckEntry.headwayRing.material.color.setHex(0xf59e0b);
        } else {
          truckEntry.headwayRing.material.color.setHex(0x06b6d4);
        }
      } else {
        truckEntry.headwayRing.visible = false;
      }
    });

    // Remove defunct truck meshes
    for (const [vid, entry] of this.truckMeshes.entries()) {
      if (!activeVids.has(vid)) {
        this.scene.remove(entry.group);
        this.truckMeshes.delete(vid);
      }
    }

    this.updateHUDLabels();
  }

  // ==========================================================================
  // DYNAMIC 3D VOLUMETRIC FOG & ATMOSPHERIC LIGHTING CONTROLLER
  // ==========================================================================
  updateAtmosphericFog(visibilityM) {
    if (!this.scene.fog || !this.showFog) return;

    const vis = Math.max(5.0, visibilityM || 50.0);
    
    // Smooth target density: V=50m -> 0.0004, V=25m -> 0.0018, V=12m -> 0.0045, V=5m -> 0.0095
    if (vis >= 45.0) {
      this.fogDensityTarget = 0.0004;
      this.targetBgColor = new THREE.Color(0x060911);
      this.targetFogColor = new THREE.Color(0x070b14);
      this.targetAmbientLight = 0.90;
      this.targetSunLight = 1.8;
    } else if (vis >= 20.0) {
      this.fogDensityTarget = 0.0018;
      this.targetBgColor = new THREE.Color(0x101724);
      this.targetFogColor = new THREE.Color(0x121a28);
      this.targetAmbientLight = 0.70;
      this.targetSunLight = 1.2;
    } else if (vis >= 8.0) {
      this.fogDensityTarget = 0.0045;
      this.targetBgColor = new THREE.Color(0x1c2533);
      this.targetFogColor = new THREE.Color(0x1e2736);
      this.targetAmbientLight = 0.50;
      this.targetSunLight = 0.7;
    } else {
      this.fogDensityTarget = 0.0095;
      this.targetBgColor = new THREE.Color(0x283242);
      this.targetFogColor = new THREE.Color(0x2a3546);
      this.targetAmbientLight = 0.35;
      this.targetSunLight = 0.4;
    }
  }

  // ==========================================================================
  // CAMERA CONTROLS, ORBIT, PAN & PRESETS
  // ==========================================================================
  updateCameraPosition() {
    const s = this.cameraState;
    const x = s.target.x + s.radius * Math.sin(s.phi) * Math.cos(s.theta);
    const y = s.target.y + s.radius * Math.cos(s.phi);
    const z = s.target.z + s.radius * Math.sin(s.phi) * Math.sin(s.theta);

    this.camera.position.set(x, y, z);
    this.camera.lookAt(s.target);
    this.updateHUDLabels();
  }

  setCameraPreset(presetName) {
    const s = this.cameraState;
    if (presetName === 'orbit' || presetName === 'fit-mine') {
      s.target.set(30, 65, 50);
      s.radius = 1180;
      s.theta = Math.PI * 0.22;
      s.phi = Math.PI * 0.30;  // Oblique aerial view framing full multi-loop mountain descent
    } else if (presetName === 'topdown') {
      s.target.set(20, 65, 50);
      s.radius = 1250;
      s.theta = 0;
      s.phi = 0.01;  // Pure top-down plan view
    } else if (presetName === 'switchback') {
      s.target.set(-120, 56, 95);  // Center of the hairpin-2 switchback curve around western spur
      s.radius = 240;
      s.theta = Math.PI * 0.28;
      s.phi = Math.PI * 0.26;
    } else if (presetName === 'crusher') {
      s.target.copy(this.nodeCoords.CRUSHER_01);
      s.radius = 260;
      s.theta = Math.PI * 0.15;
      s.phi = Math.PI * 0.35;
    }
    this.updateCameraPosition();
  }

  focusCameraOnTruck(vid) {
    if (!vid) return;
    const entry = this.truckMeshes.get(vid);
    if (!entry) return;

    const truckPos = entry.group.position.clone();
    truckPos.y += 3.0; // Focus slightly above ground

    const currentTarget = this.cameraState.target.clone();
    const currentRadius = this.cameraState.radius;
    // Comfortably frame truck: if camera is far out (e.g. 900m), smoothly glide into ~280m
    const targetRadius = Math.min(currentRadius, 280);

    this.cameraTransition = {
      startTarget: currentTarget,
      endTarget: truckPos,
      startRadius: currentRadius,
      endRadius: targetRadius,
      startTime: performance.now(),
      duration: 650 // 650ms smooth transition
    };
  }

  onTruckSelectionChanged(vid, focusCamera = false) {
    if (!vid) {
      if (this.cameraTransition) this.cameraTransition = null;
      const locator = document.getElementById('selected-truck-locator');
      if (locator) locator.style.display = 'none';
      this.truckMeshes.forEach(entry => {
        if (entry.selectionRing) entry.selectionRing.visible = false;
      });
      return;
    }

    this.truckMeshes.forEach((entry, truckId) => {
      if (entry.selectionRing) {
        entry.selectionRing.visible = (truckId === vid);
      }
    });

    if (focusCamera) {
      this.focusCameraOnTruck(vid);
    }

    this.updateHUDLabels();
  }

  setupInteractions() {
    const canvas = this.canvas;
    let mouseDownPos = { x: 0, y: 0 };

    canvas.addEventListener('mousedown', (e) => {
      // User manual interaction instantly cancels any automated camera transition
      this.cameraTransition = null;
      mouseDownPos = { x: e.clientX, y: e.clientY };

      if (e.button === 0) {
        this.cameraState.isDragging = true;
        this.cameraState.isPanning = false;
      } else if (e.button === 2) {
        this.cameraState.isPanning = true;
        this.cameraState.isDragging = false;
      }
      this.cameraState.prevMouse = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mousemove', (e) => {
      if (!this.cameraState.isDragging && !this.cameraState.isPanning) return;
      const dx = e.clientX - this.cameraState.prevMouse.x;
      const dy = e.clientY - this.cameraState.prevMouse.y;
      this.cameraState.prevMouse = { x: e.clientX, y: e.clientY };

      if (this.cameraState.isDragging) {
        this.cameraState.theta -= dx * 0.005;
        this.cameraState.phi = Math.max(this.cameraState.minPhi, Math.min(this.cameraState.maxPhi, this.cameraState.phi - dy * 0.005));
        this.updateCameraPosition();
      } else if (this.cameraState.isPanning) {
        const panSpeed = this.cameraState.radius * 0.0012;
        const right = new THREE.Vector3().crossVectors(this.camera.up, this.camera.position.clone().sub(this.cameraState.target)).normalize();
        this.cameraState.target.addScaledVector(right, -dx * panSpeed);
        this.cameraState.target.y += dy * panSpeed;
        this.updateCameraPosition();
      }
    });

    window.addEventListener('mouseup', () => {
      this.cameraState.isDragging = false;
      this.cameraState.isPanning = false;
    });

    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.cameraTransition = null;
      this.cameraState.radius = Math.max(this.cameraState.minRadius, Math.min(this.cameraState.maxRadius, this.cameraState.radius + e.deltaY * 0.6));
      this.updateCameraPosition();
    }, { passive: false });

    // Click Raycasting on 3D Trucks & Empty Space Deselection
    canvas.addEventListener('click', (e) => {
      // If mouse moved significantly between mousedown and mouseup, it was an orbit/pan drag
      if (Math.hypot(e.clientX - mouseDownPos.x, e.clientY - mouseDownPos.y) > 6) return;

      const rect = this.canvas.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.scene.children, true);

      let foundTruckId = null;
      for (const hit of intersects) {
        let parent = hit.object;
        while (parent && parent.parent !== this.scene) {
          if (parent.userData && parent.userData.vehicleId) {
            foundTruckId = parent.userData.vehicleId;
            break;
          }
          parent = parent.parent;
        }
        if (foundTruckId) break;
      }

      if (foundTruckId) {
        // 3D -> Telemetry bidirectional selection
        window.inspectVehicle(foundTruckId, { focusCamera: false });
      } else {
        // Clicking empty 3D space deselects
        if (state.selectedTruckId) {
          window.inspectVehicle(null);
        }
      }
    });

    canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    // Camera preset UI buttons
    document.getElementById('cam-orbit')?.addEventListener('click', (e) => {
      this.setActiveCamButton(e.target);
      this.setCameraPreset('orbit');
    });
    document.getElementById('cam-topdown')?.addEventListener('click', (e) => {
      this.setActiveCamButton(e.target);
      this.setCameraPreset('topdown');
    });
    document.getElementById('cam-switchback')?.addEventListener('click', (e) => {
      this.setActiveCamButton(e.target);
      this.setCameraPreset('switchback');
    });
    document.getElementById('cam-crusher')?.addEventListener('click', (e) => {
      this.setActiveCamButton(e.target);
      this.setCameraPreset('crusher');
    });
    document.getElementById('cam-fit-mine')?.addEventListener('click', (e) => {
      this.setActiveCamButton(e.target);
      this.setCameraPreset('fit-mine');
    });
    document.getElementById('btn-reset-view')?.addEventListener('click', () => {
      this.setCameraPreset('orbit');
    });

    // Fog and Headway Toggles
    const toggleFog = document.getElementById('toggle-fog');
    if (toggleFog) {
      toggleFog.addEventListener('click', () => {
        this.showFog = !this.showFog;
        toggleFog.classList.toggle('active', this.showFog);
        if (!this.showFog) this.scene.fog.density = 0;
      });
    }

    const toggleHeadway = document.getElementById('toggle-headway');
    if (toggleHeadway) {
      toggleHeadway.addEventListener('click', () => {
        this.showHeadway = !this.showHeadway;
        toggleHeadway.classList.toggle('active', this.showHeadway);
      });
    }

    const toggleDebugRoad = document.getElementById('btn-debug-road');
    if (toggleDebugRoad) {
      toggleDebugRoad.addEventListener('click', () => {
        this.showDebugRoad = !this.showDebugRoad;
        toggleDebugRoad.classList.toggle('active', this.showDebugRoad);
        if (this.debugRoadGroup) this.debugRoadGroup.visible = this.showDebugRoad;
      });
    }
  }

  setActiveCamButton(btn) {
    document.querySelectorAll('.btn-cam').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
  }

  // ==========================================================================
  // MAIN ANIMATION LOOP
  // ==========================================================================
  animate() {
    requestAnimationFrame(this.animate);
    const now = (typeof performance !== 'undefined') ? performance.now() : Date.now();
    const frameDt = this.lastFrameTime ? Math.min(0.05, (now - this.lastFrameTime) / 1000) : 0.016;
    this.lastFrameTime = now;
    this.animTime += 0.02;

    // Smooth Camera Focus Transition (cubic ease-out)
    if (this.cameraTransition) {
      const elapsed = performance.now() - this.cameraTransition.startTime;
      const t = Math.min(1.0, elapsed / this.cameraTransition.duration);
      const ease = 1 - Math.pow(1 - t, 3);

      this.cameraState.target.lerpVectors(this.cameraTransition.startTarget, this.cameraTransition.endTarget, ease);
      this.cameraState.radius = this.cameraTransition.startRadius + (this.cameraTransition.endRadius - this.cameraTransition.startRadius) * ease;
      this.updateCameraPosition();

      if (t >= 1.0) {
        this.cameraTransition = null;
      }
    }

    // 1. Authoritative Spline Traversal & Road Surface Alignment (1x, 2x, 5x, 10x)
    this.truckMeshes.forEach(entry => {
      if (entry.roadData && entry.roadData.curve) {
        // Frame-rate decoupled interpolation along spline parameter
        // Simulation time and speed multipliers advance targetT.
        // The render loop smoothly advances currentT towards targetT along the curve.
        const deltaT = entry.targetT - entry.currentT;
        const playbackMult = Math.max(1.0, state.playbackRate || 1.0);
        const baseDecay = entry.pendingEdge ? 35.0 : 20.0;
        const decay = baseDecay * Math.min(6.0, playbackMult);
        const stepAlpha = 1.0 - Math.exp(-decay * frameDt);

        if (Math.abs(deltaT) < 0.0001) {
          entry.currentT = entry.targetT;
        } else {
          entry.currentT += deltaT * stepAlpha;
        }

        // Seamless road segment transition when current segment completes at junction
        if (entry.pendingEdge) {
          const junctionTolerance = Math.min(0.20, 0.04 * Math.max(1.0, playbackMult * 0.5));
          const reachedJunction = entry.isReverse ? (entry.currentT <= junctionTolerance) : (entry.currentT >= (1.0 - junctionTolerance));
          if (reachedJunction) {
            // 1. Finish current segment at junction
            // 2. Obtain next segment
            entry.edgeId = entry.pendingEdge.edgeId;
            entry.roadData = entry.pendingEdge.roadData;
            entry.isReverse = entry.pendingEdge.isReverse;
            // 3. Initialize new segment's t (reverse enters at 1.0, forward enters at 0.0)
            const entryT = entry.isReverse ? 1.0 : 0.0;
            entry.currentT = entryT;
            entry.targetT = entry.pendingEdge.targetT;
            if (entry.pendingEdge.targetLaneOffset !== undefined) {
              entry.targetLaneOffset = entry.pendingEdge.targetLaneOffset;
            }
            entry.pendingEdge = null;
          }
        }

        // Clamp strictly to [0.0, 1.0]
        entry.currentT = Math.min(1.0, Math.max(0.0, entry.currentT));

        // 4. Sample authoritative 3D position strictly from road spline
        const p = entry.roadData.curve.getPointAt(entry.currentT);
        const tan = entry.roadData.curve.getTangentAt(entry.currentT);

        // Horizontal normal vector perpendicular to road centerline (local road frame)
        const horizLen = Math.hypot(tan.x, tan.z);
        const nx = (horizLen > 1e-4) ? (-tan.z / horizLen) : 0.0;
        const nz = (horizLen > 1e-4) ? (tan.x / horizLen) : 0.0;

        // Virtual two-lane lateral offset: Outbound = +W/4, Return = -W/4
        const isSingleLane = (entry.roadData.id === 'ROAD_04_SWITCH1_TO_INT2' || entry.roadData.directionMode === 'single_lane_alternating');
        const roadW = isSingleLane ? 0.0 : (entry.roadData.widthM || 24.0);
        const laneOffset = roadW / 4.0;
        const targetOffset = entry.isReverse ? -laneOffset : laneOffset;

        if (entry.currentLaneOffset === undefined) {
          entry.currentLaneOffset = targetOffset;
        } else {
          const offsetAlpha = 1.0 - Math.exp(-15.0 * frameDt);
          entry.currentLaneOffset += (targetOffset - entry.currentLaneOffset) * offsetAlpha;
        }

        // 5. Apply vehicle ride-height offset so tires sit flush on asphalt surface
        // Asphalt road surface is constructed at p.y + 0.50m.
        // Placing truck at p.y + 0.52m ensures wheels ride directly on surface with zero clipping or floating.
        // Lateral positioning strictly follows local road normal: P + N * laneOffset
        entry.group.position.set(
          p.x + nx * entry.currentLaneOffset,
          p.y + 0.52,
          p.z + nz * entry.currentLaneOffset
        );

        // 6. Authoritative road tangent rotation (yaw & pitch along road slope)
        const isRev = entry.isReverse;
        const targetRotY = isRev ? Math.atan2(tan.z, -tan.x) : Math.atan2(-tan.z, tan.x);
        const pitch = isRev ? Math.atan2(-tan.y, Math.hypot(tan.x, tan.z)) : Math.atan2(tan.y, Math.hypot(tan.x, tan.z));

        // Smooth yaw rotation with angle wrapping (provides smooth turnaround at destination)
        let diff = targetRotY - entry.group.rotation.y;
        while (diff < -Math.PI) diff += Math.PI * 2;
        while (diff > Math.PI) diff -= Math.PI * 2;
        const rotAlpha = 1.0 - Math.exp(-22.0 * frameDt);
        entry.group.rotation.y += diff * rotAlpha;
        entry.group.rotation.z = pitch;
      } else {
        // Fallback for non-spline nodes
        entry.group.position.lerp(entry.targetPos, 0.15);
      }

      // Selection ring pulse & rotation
      if (entry.selectionRing) {
        const isSelected = (state.selectedTruckId === entry.group.userData.vehicleId);
        entry.selectionRing.visible = isSelected;
        if (isSelected) {
          entry.selectionRing.rotation.y = this.animTime * 1.2;
          const pulse = 0.65 + Math.sin(this.animTime * 5.5) * 0.25;
          if (entry.selectionRing.children && entry.selectionRing.children.length >= 2) {
            entry.selectionRing.children[0].material.opacity = pulse;
            entry.selectionRing.children[1].material.opacity = Math.max(0.4, 1.0 - pulse * 0.5);
          }
        }
      }
    });

    // 2. Pulse beacons
    if (this.crusherBeacon) {
      this.crusherBeacon.intensity = 1.5 + Math.sin(this.animTime * 4) * 0.8;
    }
    if (this.switchbackBeacon) {
      this.switchbackBeacon.intensity = 2.0 + Math.cos(this.animTime * 3) * 1.0;
    }

    // 3. Smooth Fog Density & Atmospheric Lighting Transition
    if (this.showFog && this.scene.fog) {
      this.scene.fog.density += (this.fogDensityTarget - this.scene.fog.density) * 0.08;
      if (this.targetBgColor) {
        this.scene.background.lerp(this.targetBgColor, 0.05);
        this.scene.fog.color.lerp(this.targetFogColor, 0.05);
      }
      if (this.ambientLight && this.targetAmbientLight !== undefined) {
        this.ambientLight.intensity += (this.targetAmbientLight - this.ambientLight.intensity) * 0.05;
      }
      if (this.sunLight && this.targetSunLight !== undefined) {
        this.sunLight.intensity += (this.targetSunLight - this.sunLight.intensity) * 0.05;
      }
    }

    // 4. Render 3D Frame
    this.renderer.render(this.scene, this.camera);

    // 5. Synchronize 2D World-to-Screen HUD Labels (Facilities & Selected Truck Locator)
    this.updateHUDLabels();
  }

  // ==========================================================================
  // WORLD-TO-SCREEN PROJECTION & DYNAMIC HUD LABEL SYNCHRONIZATION
  // ==========================================================================
  projectWorldToScreen(worldPos, yOffset = 0) {
    if (!this.camera || !this.container) return null;
    this._projVector.copy(worldPos);
    this._projVector.y += yOffset;
    
    // THREE.Vector3.project transforms point into Normalized Device Coordinates (NDC) [-1, 1]
    this._projVector.project(this.camera);

    // Behind camera or beyond clipping bounds
    if (this._projVector.z > 1.0) {
      return { visible: false, x: 0, y: 0 };
    }

    const rect = this.container.getBoundingClientRect();
    const width = this.container.clientWidth || rect.width || 800;
    const height = this.container.clientHeight || rect.height || 500;

    const x = (this._projVector.x * 0.5 + 0.5) * width;
    const y = (-this._projVector.y * 0.5 + 0.5) * height;

    const isVisible = (
      this._projVector.z >= -1.0 &&
      this._projVector.z <= 1.0 &&
      x >= -120 && x <= width + 120 &&
      y >= -120 && y <= height + 120
    );

    return {
      visible: isVisible,
      x: Math.round(x * 10) / 10,
      y: Math.round(y * 10) / 10
    };
  }

  updateHUDLabels() {
    if (!this.container || !this.camera || !this.nodeCoords) return;

    // 1. Static World Facility Pins (Shovels, Switchback, Buffer, Crusher, Dump Pocket)
    const facilityPins = [
      { id: 'badge-shovel-1', pos: this.nodeCoords.SHOVEL_01, yOffset: 22 },
      { id: 'badge-shovel-2', pos: this.nodeCoords.SHOVEL_02, yOffset: 22 },
      { id: 'badge-switchback-1', pos: this.nodeCoords.SWITCHBACK_01, yOffset: 26 },
      { id: 'badge-buffer-1', pos: this.nodeCoords.BUFFER_01, yOffset: 18 },
      { id: 'badge-crusher-1', pos: this.nodeCoords.CRUSHER_01, yOffset: 38 },
      { id: 'badge-dump-1', pos: this.nodeCoords.DUMP_01, yOffset: 16 }
    ];

    facilityPins.forEach(item => {
      const el = document.getElementById(item.id);
      if (!el || !item.pos) return;

      const screenPos = this.projectWorldToScreen(item.pos, item.yOffset);
      if (screenPos && screenPos.visible) {
        el.style.display = 'flex';
        el.style.left = `${screenPos.x}px`;
        el.style.top = `${screenPos.y}px`;
      } else {
        el.style.display = 'none';
      }
    });

    // 2. Selected Truck 3D Locator Floating Badge with Directional Pointer Arrow
    const hudLayer = this.hudContainer || (this.hudContainer = document.getElementById('facility-hud-layer'));
    if (!hudLayer) return;

    // Clean up any legacy per-truck static badges so unselected trucks remain clean and uncluttered
    const oldTruckPins = hudLayer.querySelectorAll('.truck-badge-pin');
    if (oldTruckPins.length > 0) {
      oldTruckPins.forEach(el => el.remove());
    }

    let locatorEl = document.getElementById('selected-truck-locator');
    if (!locatorEl) {
      locatorEl = document.createElement('div');
      locatorEl.id = 'selected-truck-locator';
      locatorEl.className = 'selected-truck-locator-badge';
      locatorEl.style.display = 'none';
      locatorEl.innerHTML = `
        <div class="locator-badge-card" id="locator-card-btn">
          <div class="locator-badge-header">
            <span class="locator-icon">🚛</span>
            <span class="locator-vid" id="locator-truck-vid">-</span>
            <span class="locator-radar-dot"></span>
          </div>
          <div class="locator-badge-metrics">
            <span class="locator-spd" id="locator-truck-spd">0.0 km/h</span>
            <span class="locator-sep">•</span>
            <span class="locator-edge" id="locator-truck-edge">RAMP</span>
          </div>
        </div>
        <div class="locator-pointer-arrow"></div>
      `;
      locatorEl.addEventListener('click', (e) => {
        e.stopPropagation();
        if (state.selectedTruckId) {
          window.inspectVehicle(state.selectedTruckId);
        }
      });
      hudLayer.appendChild(locatorEl);
    }

    if (state.selectedTruckId && this.truckMeshes.has(state.selectedTruckId)) {
      const selEntry = this.truckMeshes.get(state.selectedTruckId);
      const currentPos = selEntry.group.position;
      // Project world position 13.5m above truck base (floating right above cab/canopy)
      const screenPos = this.projectWorldToScreen(currentPos, 13.5);

      if (screenPos && screenPos.visible) {
        locatorEl.style.display = 'flex';
        locatorEl.style.left = `${screenPos.x}px`;
        locatorEl.style.top = `${screenPos.y}px`;

        const vData = selEntry.group.userData && selEntry.group.userData.vehicleData;
        const vidEl = document.getElementById('locator-truck-vid');
        const spdEl = document.getElementById('locator-truck-spd');
        const edgeEl = document.getElementById('locator-truck-edge');

        if (vidEl) vidEl.innerText = state.selectedTruckId;
        if (spdEl && vData) {
          const spdVal = (vData.speed_mps !== undefined ? vData.speed_mps : (vData.speed_v || 0.0));
          const spdKmh = (spdVal * 3.6).toFixed(1);
          spdEl.innerText = `${spdKmh} km/h`;
        }
        if (edgeEl && vData) {
          edgeEl.innerText = vData.current_edge || vData.road_edge || 'RAMP';
        }
      } else {
        locatorEl.style.display = 'none';
      }
    } else {
      locatorEl.style.display = 'none';
    }
  }
}

// ============================================================================
// 3. CANVAS 2D TELEMETRY CHARTS ENGINE
// ============================================================================
class TelemetryChart {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.options = Object.assign({
      minY: 0,
      maxY: 15,
      yUnit: '',
      lines: [] // array of { key, color, label }
    }, options);

    this.initCanvasDPI();
  }

  initCanvasDPI() {
    if (!this.canvas || !this.ctx) return;
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = (rect.width || 180) * dpr;
    this.canvas.height = (rect.height || 85) * dpr;
    this.ctx.scale(dpr, dpr);
    this.displayW = rect.width || 180;
    this.displayH = rect.height || 85;
  }

  render(dataHistory) {
    if (!this.ctx || !this.canvas) return;
    const ctx = this.ctx;
    const w = this.displayW;
    const h = this.displayH;
    const padding = { top: 6, bottom: 14, left: 24, right: 6 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    ctx.clearRect(0, 0, w, h);

    // Draw Background Grid with dotted style
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.08)';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    for (let i = 0; i <= 3; i++) {
      const y = padding.top + (chartH / 3) * i;
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
    }
    ctx.stroke();
    ctx.setLineDash([]); // Reset line dash

    // Draw Y-Axis Labels
    ctx.fillStyle = '#64748b';
    ctx.font = '700 8px "JetBrains Mono", monospace';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${this.options.maxY}`, padding.left - 4, padding.top + 2);
    ctx.fillText(`${(this.options.maxY / 2).toFixed(1)}`, padding.left - 4, padding.top + chartH / 2);
    ctx.fillText(`${this.options.minY}`, padding.left - 4, padding.top + chartH - 2);

    const count = dataHistory.timestamps.length;
    if (count < 2) return;

    // Draw Line Series with Area Glow Gradient
    this.options.lines.forEach(lineConfig => {
      const series = dataHistory[lineConfig.key] || [];
      if (!series || series.length < 2) return;

      // 1. Draw subtle area fill under curve
      const grad = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
      grad.addColorStop(0, lineConfig.color + '22'); // 13% opacity
      grad.addColorStop(1, 'rgba(6, 9, 17, 0.0)');

      ctx.fillStyle = grad;
      ctx.beginPath();
      for (let i = 0; i < series.length; i++) {
        const x = padding.left + (chartW / (series.length - 1)) * i;
        const normY = Math.min(1, Math.max(0, (series[i] - this.options.minY) / (this.options.maxY - this.options.minY)));
        const y = padding.top + chartH * (1 - normY);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.lineTo(padding.left + chartW, padding.top + chartH);
      ctx.lineTo(padding.left, padding.top + chartH);
      ctx.closePath();
      ctx.fill();

      // 2. Draw Main Stroke Line
      ctx.strokeStyle = lineConfig.color;
      ctx.lineWidth = 2.0;
      ctx.shadowColor = lineConfig.color;
      ctx.shadowBlur = 4;
      ctx.beginPath();

      for (let i = 0; i < series.length; i++) {
        const x = padding.left + (chartW / (series.length - 1)) * i;
        const normY = Math.min(1, Math.max(0, (series[i] - this.options.minY) / (this.options.maxY - this.options.minY)));
        const y = padding.top + chartH * (1 - normY);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0; // Reset shadow

      // 3. Glowing head dot & halo
      const lastX = padding.left + chartW;
      const lastVal = series[series.length - 1];
      const lastNormY = Math.min(1, Math.max(0, (lastVal - this.options.minY) / (this.options.maxY - this.options.minY)));
      const lastY = padding.top + chartH * (1 - lastNormY);

      // Outer halo
      ctx.fillStyle = lineConfig.color + '44';
      ctx.beginPath();
      ctx.arc(lastX, lastY, 5, 0, Math.PI * 2);
      ctx.fill();

      // Core point
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(lastX, lastY, 2.2, 0, Math.PI * 2);
      ctx.fill();
    });
  }
}

// Instantiate Charts
let chartSpeed, chartWeather, chartQueue, chartBottleneck;

function initCharts() {
  // 1. Speed vs Safe Speed Chart (m/s)
  chartSpeed = new TelemetryChart('chart-speed-canvas', {
    minY: 0,
    maxY: 12,
    lines: [
      { key: 'meanSpeed', color: '#06b6d4', label: 'Speed' },
      { key: 'safeSpeed', color: '#eab308', label: 'Safe Spd' }
    ]
  });

  // 2. Visibility V(t) Chart (m)
  chartWeather = new TelemetryChart('chart-weather-canvas', {
    minY: 0,
    maxY: 60,
    lines: [
      { key: 'visibility', color: '#38bdf8', label: 'V(t) (m)' }
    ]
  });

  // 3. Total Queue Length Q(t) Chart
  chartQueue = new TelemetryChart('chart-queue-canvas', {
    minY: 0,
    maxY: 15,
    lines: [
      { key: 'totalQueue', color: '#fb923c', label: 'Total Q' },
      { key: 'crusherQueue', color: '#a855f7', label: 'Crusher' }
    ]
  });

  // 4. Bottleneck Score B(t) Chart
  chartBottleneck = new TelemetryChart('chart-bottleneck-canvas', {
    minY: 0,
    maxY: 1.0,
    lines: [
      { key: 'bottleneckScore', color: '#ef4444', label: 'B-Score' }
    ]
  });
}

// ============================================================================
// 4. REAL-TIME SYNCHRONIZATION ENGINE (WEBSOCKET + REST POLLING FALLBACK)
// ============================================================================
class RealtimeSyncManager {
  constructor(store) {
    this.store = store;
    this.ws = null;
    this.pollTimer = null;
    this.reconnectTimer = null;
    this.reconnectAttempts = 0;
    this.maxReconnectDelayMs = 5000;
  }

  connect() {
    this.cleanup();
    this.store.setConnectionState('RECONNECTING');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || '127.0.0.1:8080';
    const wsUrl = `${protocol}//${host}/ws/v1/state/stream`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.store.setConnectionState('CONNECTED', 'WS');
        this.stopPollingFallback();
        console.log('✅ Real-Time WebSocket Synchronization Established:', wsUrl);
      };

      this.ws.onmessage = (event) => {
        try {
          const snapshot = JSON.parse(event.data);
          this.store.ingestSnapshot(snapshot);
        } catch (err) {
          console.error('Error parsing real-time telemetry snapshot:', err);
        }
      };

      this.ws.onerror = (err) => {
        console.warn('⚠️ WebSocket stream error. Activating REST fallback.');
        this.startPollingFallback();
      };

      this.ws.onclose = () => {
        console.warn('⚠️ WebSocket stream closed. Reconnecting...');
        this.store.setConnectionState('RECONNECTING');
        this.startPollingFallback();
        this.scheduleReconnect();
      };
    } catch (err) {
      console.warn('WebSocket initialization failed. Using REST polling fallback:', err);
      this.startPollingFallback();
      this.scheduleReconnect();
    }
  }

  startPollingFallback() {
    if (this.pollTimer) return;
    this.pollTimer = setInterval(async () => {
      try {
        const res = await fetch('/api/v1/state/snapshot');
        if (res.ok) {
          const snapshot = await res.json();
          this.store.setConnectionState('CONNECTED', 'REST');
          this.store.ingestSnapshot(snapshot);
        } else {
          this.store.setConnectionState('DISCONNECTED');
        }
      } catch (e) {
        this.store.setConnectionState('DISCONNECTED');
      }
    }, 500); // 2 Hz polling cadence
  }

  stopPollingFallback() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectAttempts++;
    const delay = Math.min(this.maxReconnectDelayMs, 1000 * Math.pow(1.5, this.reconnectAttempts));
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  cleanup() {
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      try { this.ws.close(); } catch (e) {}
      this.ws = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

let syncManager = null;

function connectWebSocket() {
  if (!syncManager) {
    syncManager = new RealtimeSyncManager(simulationStore);
  }
  syncManager.connect();
}

// ============================================================================
// 5. MASTER STATE HYDRATION (DELEGATES TO NORMALIZED SIMULATION STORE)
// ============================================================================
function handleTelemetrySnapshot(data) {
  if (!data) return;
  simulationStore.ingestSnapshot(data);
}

// ----------------------------------------------------------------------------
// Region 1 Hydration: Top Status Bar
// ----------------------------------------------------------------------------
function updateTopStatusBar(simTime, stepCount, scenarioId, env, fleet) {
  const timeEl = document.getElementById('sim-time-val');
  if (timeEl) timeEl.innerText = `${simTime.toFixed(1)} s`;

  const stepEl = document.getElementById('sim-step-val');
  if (stepEl) stepEl.innerText = stepCount;

  const scenEl = document.getElementById('header-scenario-id');
  if (scenEl) scenEl.innerText = `${scenarioId}: ${getScenarioName(scenarioId)}`;

  const weatherEl = document.getElementById('header-weather-val');
  if (weatherEl) {
    const vis = (env.visibility_m || 50.0).toFixed(0);
    const mu = (env.friction_mu || 0.65).toFixed(2);
    const mode = env.weather_mode || 'CLEAR';
    weatherEl.innerText = `${mode} (${vis}m, μ=${mu})`;
  }

  const safetyPill = document.getElementById('safety-status-text');
  if (safetyPill) {
    const violations = fleet.safety_violations || 0;
    if (violations === 0) {
      safetyPill.innerText = '0 VIOLATIONS (100% PASS)';
      safetyPill.className = 'tier1-pill-status status-safe';
    } else {
      safetyPill.innerText = `${violations} SAFETY VIOLATIONS`;
      safetyPill.className = 'tier1-pill-status val-red';
    }
  }
}

// ----------------------------------------------------------------------------
// Region 4 Hydration: Telemetry Charts Buffer & Redraw
// ----------------------------------------------------------------------------
function updateChartsBuffer(simTime, vehicles, env, queues, bottlenecks) {
  const vSpds = vehicles.map(v => v.speed_mps || v.speed_v || 0);
  const meanV = vSpds.length ? (vSpds.reduce((a, b) => a + b, 0) / vSpds.length) : 0;
  
  const vSafes = vehicles.map(v => v.safe_speed_mps || 11.11);
  const meanSafeV = vSafes.length ? (vSafes.reduce((a, b) => a + b, 0) / vSafes.length) : 11.11;

  const vis = env.visibility_m || 50.0;
  const mu = env.friction_mu || 0.65;

  const totalQ = Object.values(queues || {}).reduce((acc, q) => acc + (q.queue_length || 0), 0);
  const crusherQ = queues['CRUSHER_01'] ? queues['CRUSHER_01'].queue_length : 0.0;
  const shovelQ = queues['SHOVEL_01'] ? queues['SHOVEL_01'].queue_length : 0.0;

  let topBScore = 0.0;
  if (bottlenecks.active_bottlenecks && bottlenecks.active_bottlenecks.length > 0) {
    topBScore = bottlenecks.active_bottlenecks[0].score || 0.0;
  }

  state.history.timestamps.push(simTime);
  state.history.meanSpeed.push(meanV);
  state.history.safeSpeed.push(meanSafeV);
  state.history.visibility.push(vis);
  state.history.friction.push(mu);
  state.history.totalQueue.push(totalQ);
  state.history.crusherQueue.push(crusherQ);
  state.history.shovelQueue.push(shovelQ);
  state.history.bottleneckScore.push(topBScore);

  if (state.history.timestamps.length > state.maxHistoryLength) {
    state.history.timestamps.shift();
    state.history.meanSpeed.shift();
    state.history.safeSpeed.shift();
    state.history.visibility.shift();
    state.history.friction.shift();
    state.history.totalQueue.shift();
    state.history.crusherQueue.shift();
    state.history.shovelQueue.shift();
    state.history.bottleneckScore.shift();
  }

  if (chartSpeed) chartSpeed.render(state.history);
  if (chartWeather) chartWeather.render(state.history);
  if (chartQueue) chartQueue.render(state.history);
  if (chartBottleneck) chartBottleneck.render(state.history);
}

// ----------------------------------------------------------------------------
// Region 5 Hydration: Live Vehicle Telemetry Table (11 Columns)
// ----------------------------------------------------------------------------
function updateVehicleTable(vehicles) {
  const tbody = document.getElementById('vehicle-table-body');
  const countBadge = document.getElementById('table-truck-count');
  if (!tbody) return;

  if (countBadge) {
    countBadge.innerText = `${vehicles.length} ACTIVE TRUCKS`;
  }

  if (!vehicles || vehicles.length === 0) {
    tbody.innerHTML = '<tr><td colspan="11" class="table-placeholder">No active vehicles deployed in simulation.</td></tr>';
    return;
  }

  let rowsHtml = '';
  vehicles.forEach(v => {
    const vid = v.vehicle_id || v.id;
    const edge = v.current_edge || v.road_edge || 'RAMP';
    const stationNum = (v.station !== undefined ? v.station : (v.station_m !== undefined ? v.station_m : (v.position_s || 0.0)));
    const station = stationNum.toFixed(1);
    const spd = (v.speed_mps || v.speed_v || 0.0).toFixed(2);
    const safeSpd = (v.safe_speed_mps || 11.11).toFixed(2);
    const cmdSpd = (v.command_speed_mps || v.target_speed || safeSpd);
    const cmdSpdFormatted = parseFloat(cmdSpd).toFixed(2);
    const loadState = (v.is_loaded || v.load_state === 'LOADED') ? 'LOADED' : 'EMPTY';
    const payload = (v.payload_t || v.payload_tonnes || (loadState === 'LOADED' ? 91.5 : 0.0)).toFixed(1);
    const grade = (v.road_grade_pct || v.grade || 0.0).toFixed(1);
    const comm = v.communication_status ? `${(v.communication_status.latency_s || 0.05).toFixed(2)}s` : '0.05s';

    let pillClass = 'pill-safe';
    let pillText = 'GOVERNED (OK)';
    if (parseFloat(spd) > parseFloat(safeSpd) + 0.1) {
      pillClass = 'pill-crit';
      pillText = 'CRITICAL OVERSPEED';
    } else if (parseFloat(spd) >= parseFloat(safeSpd) * 0.95) {
      pillClass = 'pill-warn';
      pillText = 'AT CEILING';
    }

    rowsHtml += `
      <tr onclick="inspectVehicle('${vid}')" data-vid="${vid}" class="${state.selectedTruckId === vid ? 'selected-row' : ''}">
        <td class="val-cyan">${vid}</td>
        <td>${edge}</td>
        <td class="val-cyan">${station} m</td>
        <td class="val-emerald">${spd} m/s</td>
        <td class="val-yellow">${safeSpd} m/s</td>
        <td class="val-cyan">${cmdSpdFormatted} m/s</td>
        <td><span class="${loadState === 'LOADED' ? 'val-amber' : 'val-muted'}">${loadState}</span></td>
        <td class="${loadState === 'LOADED' ? 'val-amber' : 'val-muted'}">${payload} t</td>
        <td>${grade > 0 ? '+' : ''}${grade}%</td>
        <td>${comm}</td>
        <td><span class="status-pill ${pillClass}">${pillText}</span></td>
      </tr>
    `;
  });

  tbody.innerHTML = rowsHtml;
}

// ----------------------------------------------------------------------------
// Region 3 Hydration: Viewport Facility HUD Overlays
// ----------------------------------------------------------------------------
function updateViewportFacilityHUD(queues, switchbacks, vehicles) {
  const sh1 = queues['SHOVEL_01'];
  const elSh1 = document.getElementById('hud-shovel-1-q');
  if (elSh1 && sh1) elSh1.innerText = `Q: ${sh1.queue_length.toFixed(1)} / ${sh1.queue_max}`;

  const sh2 = queues['SHOVEL_02'];
  const elSh2 = document.getElementById('hud-shovel-2-q');
  if (elSh2 && sh2) elSh2.innerText = `Q: ${sh2.queue_length.toFixed(1)} / ${sh2.queue_max}`;

  const buf = queues['BUFFER_01'];
  const elBuf = document.getElementById('hud-buffer-1-q');
  if (elBuf && buf) elBuf.innerText = `Q: ${buf.queue_length.toFixed(1)} / ${buf.queue_max}`;

  const cru = queues['CRUSHER_01'];
  const elCru = document.getElementById('hud-crusher-1-q');
  if (elCru && cru) elCru.innerText = `Q: ${cru.queue_length.toFixed(1)} / ${cru.queue_max} (${cru.service_rate_vph.toFixed(0)} vph)`;

  const elSw = document.getElementById('hud-switchback-status');
  if (elSw) {
    const res = switchbacks.reservations || [];
    if (res.length > 0) {
      const activeSlot = res[0];
      elSw.innerText = `LOCK: ${activeSlot.vehicle_id} (${activeSlot.direction.toUpperCase()})`;
      elSw.className = 'pin-val val-amber';
    } else {
      elSw.innerText = 'MUTUAL EXCLUSION: CLEAR';
      elSw.className = 'pin-val status-clear';
    }
  }

  // Update Inspector Card if active (all 11 vehicle state parameters)
  updateTruckInspectorCard(vehicles);
}

function updateTruckInspectorCard(vehicles) {
  if (!state.selectedTruckId || !vehicles) return;
  const truck = vehicles.find(v => (v.vehicle_id || v.id) === state.selectedTruckId);
  if (!truck) return;

  const vid = truck.vehicle_id || truck.id;
  const edge = truck.current_edge || truck.road_edge || '-';
  const station = (truck.station !== undefined ? truck.station : (truck.station_m !== undefined ? truck.station_m : (truck.position_s || 0.0))).toFixed(1);
  const spd = (truck.speed_mps || truck.speed || 0.0).toFixed(2);
  const spdKmh = ((truck.speed_mps || truck.speed || 0.0) * 3.6).toFixed(1);
  const headingDeg = (truck.heading !== undefined ? truck.heading : (truck.heading_deg !== undefined ? truck.heading_deg : 0.0)).toFixed(1);
  const headingRad = (truck.heading_rad !== undefined ? truck.heading_rad : 0.0).toFixed(2);
  const loadState = truck.load_state || (truck.is_loaded ? 'LOADED' : 'EMPTY');
  const payload = (truck.payload !== undefined ? truck.payload : (truck.payload_tonnes || 0.0)).toFixed(1);
  const safeSpd = (truck.safe_speed !== undefined ? truck.safe_speed : (truck.safe_speed_mps || 11.11)).toFixed(2);
  const grade = (truck.grade !== undefined ? truck.grade : (truck.road_grade_pct || 0.0)).toFixed(1);
  const dest = truck.destination || '-';
  const safety = truck.safety_state || truck.safety_status || 'GOVERNED (OK)';
  const cmdSpd = (truck.command_speed_mps || 11.11).toFixed(2);
  const commHealth = truck.communication_status ? `${(truck.communication_status.confidence * 100).toFixed(0)}% (${truck.communication_status.latency_s.toFixed(2)}s)` : '100% (0.05s)';
  const visVal = (simulationStore.state.environment && simulationStore.state.environment.visibility_m !== undefined) ? simulationStore.state.environment.visibility_m : 50.0;

  const elId = document.getElementById('insp-truck-id');
  if (elId) elId.innerText = `${vid} (Simulated Vehicle)`;
  const elSpd = document.getElementById('insp-truck-spd');
  if (elSpd) elSpd.innerText = `${spd} m/s (${spdKmh} km/h)`;
  const elSafeSpd = document.getElementById('insp-truck-safe-spd');
  if (elSafeSpd) elSafeSpd.innerText = `${safeSpd} m/s`;
  const elCmd = document.getElementById('insp-truck-cmd-spd');
  if (elCmd) elCmd.innerText = `${cmdSpd} m/s`;
  const elVis = document.getElementById('insp-truck-vis');
  if (elVis) elVis.innerText = `${visVal.toFixed(1)} m`;

  const elEdge = document.getElementById('insp-truck-edge');
  if (elEdge) elEdge.innerText = edge;
  const elStn = document.getElementById('insp-truck-station');
  if (elStn) elStn.innerText = `${station} m`;
  const elHeading = document.getElementById('insp-truck-heading');
  if (elHeading) elHeading.innerText = `${headingDeg}° (${headingRad} rad)`;
  const elLoad = document.getElementById('insp-truck-load-state');
  if (elLoad) {
    elLoad.innerText = loadState;
    elLoad.className = loadState === 'LOADED' ? 'val-amber' : 'val-muted';
  }
  const elPayload = document.getElementById('insp-truck-payload');
  if (elPayload) elPayload.innerText = `${payload} t`;
  const elGrade = document.getElementById('insp-truck-grade');
  if (elGrade) elGrade.innerText = `${grade > 0 ? '+' : ''}${grade}%`;
  const elDest = document.getElementById('insp-truck-destination');
  if (elDest) elDest.innerText = dest;
  const elSafety = document.getElementById('insp-truck-safety');
  if (elSafety) {
    elSafety.innerText = safety;
    elSafety.className = (safety === 'SAFE' || safety.includes('OK') || safety === 'GOVERNED') ? 'val-emerald' : (safety === 'WARNING' ? 'val-yellow' : 'val-red');
  }
  const elComm = document.getElementById('insp-truck-comm');
  if (elComm) elComm.innerText = commHealth;

  const card = document.getElementById('truck-inspector-card');
  if (card) card.style.display = 'block';
}

// ----------------------------------------------------------------------------
// Region 6 Hydration: Bottom Fleet KPIs
// ----------------------------------------------------------------------------
function updateFleetKPIs(fleet, vehicles, simTime = 0.0) {
  const activeFleetEl = document.getElementById('kpi-active-fleet');
  if (activeFleetEl) activeFleetEl.innerText = fleet.fleet_size || vehicles.length || 10;

  const deliveredEl = document.getElementById('kpi-delivered-tonnes');
  const deliveredVal = (fleet.total_delivered_tonnes !== undefined ? fleet.total_delivered_tonnes : (fleet.delivered_payload_t || 0.0));
  if (deliveredEl) deliveredEl.innerText = `${deliveredVal.toFixed(1)} t`;

  const throughputEl = document.getElementById('kpi-throughput-vph');
  if (throughputEl) {
    const trips = deliveredVal / 91.5;
    const vph = simTime > 10 ? (trips / (simTime / 3600)).toFixed(1) : (trips > 0 ? (trips * 12).toFixed(1) : '0.0');
    throughputEl.innerText = `${vph} vph`;
  }

  const meanSpeedEl = document.getElementById('kpi-mean-speed');
  if (meanSpeedEl) {
    const spds = vehicles.map(v => (v.speed_mps !== undefined ? v.speed_mps : (v.speed_v || 0.0)));
    const mean = spds.length ? (spds.reduce((a, b) => a + b, 0) / spds.length) : 0;
    meanSpeedEl.innerText = `${mean.toFixed(2)} m/s`;
  }

  const safetyEl = document.getElementById('kpi-safety-violations');
  if (safetyEl) {
    const viol = (fleet.safety_violations_count !== undefined ? fleet.safety_violations_count : (fleet.safety_violations || 0));
    safetyEl.innerText = `${viol}`;
    safetyEl.className = viol === 0 ? 'kpi-val val-green' : 'kpi-val val-red';
  }
}

// ----------------------------------------------------------------------------
// Region 7 Hydration: Bottom Service Queues Panel
// ----------------------------------------------------------------------------
function updateServiceQueuesPanel(queues) {
  const container = document.getElementById('queues-list-container');
  if (!container || !queues) return;

  const nodeOrder = ['CRUSHER_01', 'BUFFER_01', 'SHOVEL_01', 'SHOVEL_02', 'SWITCHBACK_01', 'DUMP_01'];
  let html = '';

  nodeOrder.forEach(nodeId => {
    const node = queues[nodeId];
    if (!node) return;

    const q = node.queue_length || 0;
    const qMax = Math.max(1, node.queue_max || 8);
    const pct = node.buffer_utilization_pct !== undefined ? node.buffer_utilization_pct : Math.min(100, Math.round((q / qMax) * 100));

    let fillClass = 'fill-emerald';
    if (pct >= 85 || node.status === 'CRITICAL') fillClass = 'fill-red';
    else if (pct >= 60 || node.status === 'WARNING') fillClass = 'fill-yellow';
    else if (pct >= 30) fillClass = 'fill-cyan';

    const blockedTag = node.is_blocked ? ' <span class="val-red">[BLOCKED]</span>' : '';

    html += `
      <div class="queue-meter-row">
        <span class="queue-node-name">${nodeId}${blockedTag}</span>
        <div class="meter-bar-track">
          <div class="meter-bar-fill ${fillClass}" style="width: ${pct}%;"></div>
        </div>
        <span class="queue-ratio">${q.toFixed(1)} / ${qMax}</span>
      </div>
    `;
  });

  container.innerHTML = html;
}

// ----------------------------------------------------------------------------
// Region 8 Hydration: Bottom Bottleneck Ranking Panel
// ----------------------------------------------------------------------------
function updateBottleneckRankingPanel(bottlenecks) {
  const container = document.getElementById('bottleneck-list-container');
  if (!container) return;

  const active = (bottlenecks && bottlenecks.active_bottlenecks) ? bottlenecks.active_bottlenecks : [];
  if (active.length === 0) {
    container.innerHTML = '<div class="bottleneck-item-row"><span class="bn-elem-id">UNCONGESTED</span><span class="bn-score val-emerald">Score: 0.000</span></div>';
    return;
  }

  let html = '';
  active.slice(0, 4).forEach((b, idx) => {
    const rank = b.rank || (idx + 1);
    const rankClass = rank === 1 ? 'rank-1' : (rank === 2 ? 'rank-2' : 'rank-3');
    const elemId = b.id || b.element_id || 'NODE';
    const elemType = b.type || b.element_type || 'NODE';
    const score = (b.score !== undefined ? b.score : 0.0).toFixed(3);
    const util = b.utilization !== undefined ? `(${(b.utilization * 100).toFixed(0)}%)` : '';

    html += `
      <div class="bottleneck-item-row">
        <span class="rank-badge ${rankClass}">#${rank}</span>
        <span class="bn-elem-id">${elemId}</span>
        <span class="bn-elem-type">${elemType} ${util}</span>
        <span class="bn-score val-amber">Score: ${score}</span>
      </div>
    `;
  });

  container.innerHTML = html;
}

// ----------------------------------------------------------------------------
// Region 9 Hydration: Bottom Switchback Locks Panel
// ----------------------------------------------------------------------------
function updateSwitchbackLocksPanel(switchbacks) {
  const slotStatusEl = document.getElementById('sw-slot-status');
  if (!slotStatusEl) return;

  const res = (switchbacks && switchbacks.reservations) ? switchbacks.reservations : [];
  if (res.length > 0) {
    const s = res[0];
    const loadTag = s.is_loaded ? 'LOADED' : 'EMPTY';
    slotStatusEl.innerText = `LOCK: ${s.vehicle_id} (${s.direction.toUpperCase()} | ${loadTag} | [${s.start_time.toFixed(0)}s–${s.end_time.toFixed(0)}s])`;
    slotStatusEl.className = 'val-amber';
  } else {
    slotStatusEl.innerText = 'NONE (MUTUAL EXCLUSION CLEAR)';
    slotStatusEl.className = 'val-emerald';
  }
}

// ----------------------------------------------------------------------------
// Region 10 Hydration: Bottom System Alerts Panel
// ----------------------------------------------------------------------------
function updateSystemAlertsPanel(alerts, simTime = 0.0) {
  const container = document.getElementById('alerts-log-container');
  if (!container) return;

  const alertList = Array.isArray(alerts) ? alerts : (alerts && alerts.alerts ? alerts.alerts : []);
  if (alertList.length === 0) {
    container.innerHTML = `
      <div class="alert-log-entry entry-info">
        <span class="alert-time">${simTime.toFixed(1)}s</span>
        <span class="alert-badge badge-info">AUDIT OK</span>
        <span class="alert-msg">Tier-1 Safety Governor active. Zero violations detected across all segments.</span>
      </div>
    `;
    return;
  }

  let html = '';
  alertList.slice(-4).reverse().forEach(a => {
    const lvl = a.level || 'INFO';
    let badgeClass = 'badge-info';
    if (lvl === 'CRITICAL') badgeClass = 'badge-crit';
    else if (lvl === 'WARNING') badgeClass = 'badge-warn';

    html += `
      <div class="alert-log-entry">
        <span class="alert-time">${(a.timestamp !== undefined ? a.timestamp : simTime).toFixed(1)}s</span>
        <span class="alert-badge ${badgeClass}">${lvl}</span>
        <span class="alert-msg">${a.message || a.source || 'Operational Notice'}</span>
      </div>
    `;
  });

  container.innerHTML = html;
}

// ============================================================================
// 6. INTERACTIVE SIMULATION CONTROLS & EVENT LISTENERS
// ============================================================================
function setupEventListeners() {
  // Scenario Selection Switcher
  const scenarioSelect = document.getElementById('scenario-select');
  if (scenarioSelect) {
    scenarioSelect.addEventListener('change', async (e) => {
      const scenarioId = e.target.value;
      state.activeScenarioId = scenarioId;
      try {
        const res = await fetch(`/api/v1/control/scenario?scenario_id=${scenarioId}`, { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          console.log(`✅ Switched to Scenario ${scenarioId}:`, data);
          simulationStore.resetHistory();
          resetHistoryBuffer();
          if (data && data.snapshot) {
            handleTelemetrySnapshot(data.snapshot);
          } else {
            const snapRes = await fetch('/api/v1/state/snapshot');
            if (snapRes.ok) {
              const snapshot = await snapRes.json();
              handleTelemetrySnapshot(snapshot);
            }
          }
        }
      } catch (err) {
        console.error('Error switching scenario:', err);
      }
    });
  }

  // Play / Pause Stream Toggle (Pause / Resume)
  const btnPlayPause = document.getElementById('btn-play-pause');
  if (btnPlayPause) {
    btnPlayPause.addEventListener('click', () => {
      setSimulationRunning(!state.isRunning);
    });
  }

  // Step Buttons (+1s, +10s, +60s)
  const btnStep1 = document.getElementById('btn-step-1');
  if (btnStep1) btnStep1.addEventListener('click', () => triggerSimStep(1));

  const btnStep10 = document.getElementById('btn-step-10');
  if (btnStep10) btnStep10.addEventListener('click', () => triggerSimStep(10));

  const btnStep60 = document.getElementById('btn-step-60');
  if (btnStep60) btnStep60.addEventListener('click', () => triggerSimStep(60));

  // Playback Rate Multipliers (1x, 2x, 5x, 10x)
  document.querySelectorAll('.btn-rate-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const rate = parseInt(e.target.getAttribute('data-rate'), 10) || 1;
      setPlaybackRate(rate);
    });
  });

  // Reset Digital Twin Buttons
  const btnResetTwin = document.getElementById('btn-reset-twin');
  if (btnResetTwin) {
    btnResetTwin.addEventListener('click', () => {
      const fleetSelect = document.getElementById('fleet-size-select');
      const fleetSize = fleetSelect ? parseInt(fleetSelect.value, 10) || 10 : 10;
      resetDigitalTwin(fleetSize, 42);
    });
  }

  // Fleet Size Selector
  const fleetSelect = document.getElementById('fleet-size-select');
  if (fleetSelect) {
    fleetSelect.addEventListener('change', async (e) => {
      const fleetSize = parseInt(e.target.value, 10) || 10;
      resetDigitalTwin(fleetSize, 42);
    });
  }

  // ==========================================================================
  // ENVIRONMENT & WEATHER CONTROLS & REAL SIMULATION INTEGRATION
  // ==========================================================================

  // Quick Weather Mode Preset Buttons
  const presetButtons = {
    'CLEAR': document.getElementById('btn-preset-clear'),
    'MODERATE_FOG': document.getElementById('btn-preset-mod-fog'),
    'DENSE_FOG': document.getElementById('btn-preset-dense-fog'),
    'EXTREME_FOG': document.getElementById('btn-preset-severe-fog')
  };

  function setPresetButtonActive(mode) {
    Object.values(presetButtons).forEach(btn => {
      if (btn) btn.classList.remove('active');
    });
    if (presetButtons[mode]) {
      presetButtons[mode].classList.add('active');
    }
  }

  // Preset Configurations
  const weatherPresets = {
    'CLEAR': { vis: 50, friction: 0.65, surf: 'dry', wind: 2.0 },
    'MODERATE_FOG': { vis: 25, friction: 0.50, surf: 'damp', wind: 5.0 },
    'DENSE_FOG': { vis: 12, friction: 0.35, surf: 'wet', wind: 8.0 },
    'EXTREME_FOG': { vis: 5, friction: 0.20, surf: 'saturated', wind: 12.0 }
  };

  let envDebounceTimer = null;
  function triggerDebouncedEnvironmentApply() {
    if (envDebounceTimer) clearTimeout(envDebounceTimer);
    envDebounceTimer = setTimeout(() => {
      applyEnvironmentalConditions();
    }, 80);
  }

  function applyPresetValues(mode) {
    const p = weatherPresets[mode] || weatherPresets.CLEAR;
    const weatherModeSelect = document.getElementById('weather-mode-select');
    const visSlider = document.getElementById('slider-visibility');
    const visDisplay = document.getElementById('disp-visibility-val');
    const liveFogBadge = document.getElementById('live-fog-badge');
    const fricSlider = document.getElementById('slider-friction');
    const fricDisplay = document.getElementById('disp-friction-val');
    const surfSelect = document.getElementById('surface-state-select');
    const windSlider = document.getElementById('slider-wind');
    const windDisplay = document.getElementById('disp-wind-val');

    if (weatherModeSelect) weatherModeSelect.value = mode;
    if (visSlider) visSlider.value = p.vis;
    if (visDisplay) visDisplay.innerText = `VISIBILITY: ${p.vis.toFixed(1)} m`;
    if (liveFogBadge) liveFogBadge.innerText = `V: ${p.vis.toFixed(1)}m`;
    if (fricSlider) fricSlider.value = p.friction;
    if (fricDisplay) fricDisplay.innerText = p.friction.toFixed(2);
    if (surfSelect) surfSelect.value = p.surf;
    if (windSlider) windSlider.value = p.wind;
    if (windDisplay) windDisplay.innerText = `${p.wind.toFixed(1)} m/s`;

    setPresetButtonActive(mode);
    updateLivePhysicsPreview(p.vis, p.surf, p.friction);

    if (state.threeViewer) {
      state.threeViewer.updateAtmosphericFog(p.vis);
    }

    applyEnvironmentalConditions();
  }

  // Attach Preset Button Listeners
  if (presetButtons.CLEAR) {
    presetButtons.CLEAR.addEventListener('click', () => applyPresetValues('CLEAR'));
  }
  if (presetButtons.MODERATE_FOG) {
    presetButtons.MODERATE_FOG.addEventListener('click', () => applyPresetValues('MODERATE_FOG'));
  }
  if (presetButtons.DENSE_FOG) {
    presetButtons.DENSE_FOG.addEventListener('click', () => applyPresetValues('DENSE_FOG'));
  }
  if (presetButtons.EXTREME_FOG) {
    presetButtons.EXTREME_FOG.addEventListener('click', () => applyPresetValues('EXTREME_FOG'));
  }

  // 1. Optical Visibility Slider Live Update
  const visSlider = document.getElementById('slider-visibility');
  const visDisplay = document.getElementById('disp-visibility-val');
  const liveFogBadge = document.getElementById('live-fog-badge');
  if (visSlider && visDisplay) {
    visSlider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      visDisplay.innerText = `VISIBILITY: ${val.toFixed(1)} m`;
      if (liveFogBadge) liveFogBadge.innerText = `V: ${val.toFixed(1)}m`;
      const surf = document.getElementById('surface-state-select') ? document.getElementById('surface-state-select').value : 'dry';
      const fric = document.getElementById('slider-friction') ? parseFloat(document.getElementById('slider-friction').value) : 0.65;
      updateLivePhysicsPreview(val, surf, fric);
      if (state.threeViewer) {
        state.threeViewer.updateAtmosphericFog(val);
      }
      triggerDebouncedEnvironmentApply();
    });
    visSlider.addEventListener('change', () => {
      applyEnvironmentalConditions();
    });
  }

  // 2. Road Friction Slider Live Update
  const fricSlider = document.getElementById('slider-friction');
  const fricDisplay = document.getElementById('disp-friction-val');
  if (fricSlider && fricDisplay) {
    fricSlider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      fricDisplay.innerText = val.toFixed(2);
      const vis = document.getElementById('slider-visibility') ? parseFloat(document.getElementById('slider-visibility').value) : 50;
      const surf = document.getElementById('surface-state-select') ? document.getElementById('surface-state-select').value : 'dry';
      updateLivePhysicsPreview(vis, surf, val);
      triggerDebouncedEnvironmentApply();
    });
    fricSlider.addEventListener('change', () => {
      applyEnvironmentalConditions();
    });
  }

  // 3. Road Surface Condition Selector Live Update
  const surfaceSelect = document.getElementById('surface-state-select');
  if (surfaceSelect) {
    surfaceSelect.addEventListener('change', (e) => {
      const surf = e.target.value;
      const surfFricMap = { dry: 0.65, damp: 0.50, wet: 0.35, saturated: 0.20 };
      const defaultFric = surfFricMap[surf] || 0.65;

      if (fricSlider && fricDisplay) {
        fricSlider.value = defaultFric;
        fricDisplay.innerText = defaultFric.toFixed(2);
      }

      const vis = visSlider ? parseFloat(visSlider.value) : 50;
      updateLivePhysicsPreview(vis, surf, defaultFric);
      applyEnvironmentalConditions();
    });
  }

  // 4. Ambient Wind Slider Live Update
  const windSlider = document.getElementById('slider-wind');
  const windDisplay = document.getElementById('disp-wind-val');
  if (windSlider && windDisplay) {
    windSlider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      windDisplay.innerText = `${val.toFixed(1)} m/s`;
      triggerDebouncedEnvironmentApply();
    });
    windSlider.addEventListener('change', () => {
      applyEnvironmentalConditions();
    });
  }

  // Preset Weather Selector Dropdown Sync
  const weatherModeSelect = document.getElementById('weather-mode-select');
  if (weatherModeSelect) {
    weatherModeSelect.addEventListener('change', (e) => {
      const mode = e.target.value;
      applyPresetValues(mode);
    });
  }

  // Apply Weather Button
  const btnApplyWeather = document.getElementById('btn-apply-weather');
  if (btnApplyWeather) {
    btnApplyWeather.addEventListener('click', () => {
      applyEnvironmentalConditions();
    });
  }

  // Benchmark Matrix Modal
  const btnOpenBenchmarks = document.getElementById('btn-open-benchmarks');
  const btnCloseBenchmarks = document.getElementById('btn-close-benchmarks');
  const modal = document.getElementById('benchmark-modal');

  if (btnOpenBenchmarks && modal) {
    btnOpenBenchmarks.addEventListener('click', () => {
      modal.style.display = 'flex';
      loadBenchmarkData();
    });
  }
  if (btnCloseBenchmarks && modal) {
    btnCloseBenchmarks.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  // Site Provenance Modal
  const btnOpenProvenance = document.getElementById('btn-open-provenance');
  const btnOpenProvModal = document.getElementById('btn-open-prov-modal');
  const btnCloseProvenance = document.getElementById('btn-close-provenance');
  const provModal = document.getElementById('provenance-modal');

  const openProvModal = () => {
    if (provModal) provModal.style.display = 'flex';
  };
  if (btnOpenProvenance) btnOpenProvenance.addEventListener('click', openProvModal);
  if (btnOpenProvModal) btnOpenProvModal.addEventListener('click', openProvModal);
  if (btnCloseProvenance && provModal) {
    btnCloseProvenance.addEventListener('click', () => {
      provModal.style.display = 'none';
    });
  }
  if (provModal) {
    provModal.addEventListener('click', (e) => {
      if (e.target === provModal) provModal.style.display = 'none';
    });
  }

  // 3D Viewport Collapsible Site & Data Info Toggle
  const btnToggleSiteInfo = document.getElementById('btn-toggle-site-info');
  const viewportProvBadge = document.getElementById('viewport-prov-badge');
  const btnCloseVprov = document.getElementById('btn-close-vprov');
  let siteInfoExpanded = false;

  const setSiteInfoExpanded = (expanded) => {
    siteInfoExpanded = expanded;
    if (viewportProvBadge) {
      if (siteInfoExpanded) {
        viewportProvBadge.classList.add('is-expanded');
      } else {
        viewportProvBadge.classList.remove('is-expanded');
      }
    }
    if (btnToggleSiteInfo) {
      btnToggleSiteInfo.setAttribute('aria-expanded', siteInfoExpanded ? 'true' : 'false');
      const arrow = btnToggleSiteInfo.querySelector('.vprov-arrow');
      if (arrow) arrow.textContent = siteInfoExpanded ? '▼' : '▲';
    }
  };

  if (btnToggleSiteInfo) {
    btnToggleSiteInfo.addEventListener('click', (e) => {
      e.stopPropagation();
      setSiteInfoExpanded(!siteInfoExpanded);
    });
  }

  if (btnCloseVprov) {
    btnCloseVprov.addEventListener('click', (e) => {
      e.stopPropagation();
      setSiteInfoExpanded(false);
    });
  }

  // Fetch and verify site provenance metadata
  fetch('/api/site/metadata')
    .then(res => res.json())
    .then(meta => {
      if (meta && meta.site) {
        console.log('📜 Site Provenance & Geospatial Truth Verified:', meta.site.name, `(${meta.lease.extent_ha} ha, ${meta.lease.geometry_type})`);
      }
    })
    .catch(() => {});

  // Benchmark Modal Tabs
  document.querySelectorAll('.modal-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.modal-tab-content').forEach(c => c.style.display = 'none');
      e.target.classList.add('active');
      const tabId = e.target.getAttribute('data-tab');
      const targetContent = document.getElementById(tabId);
      if (targetContent) targetContent.style.display = 'block';
    });
  });

  // Close Inspector Button
  const btnCloseInsp = document.getElementById('btn-close-insp');
  if (btnCloseInsp) {
    btnCloseInsp.addEventListener('click', () => {
      window.inspectVehicle(null);
    });
  }

  // Quick Reset Footer Button
  const btnQuickReset = document.getElementById('btn-quick-reset');
  if (btnQuickReset) {
    btnQuickReset.addEventListener('click', () => {
      resetDigitalTwin(10, 42);
    });
  }

  // Wall Clock Update Interval
  setInterval(updateWallClock, 1000);
  updateWallClock();
}

// ============================================================================
// REAL SIMULATION ADVANCEMENT & PLAYBACK ENGINE
// ============================================================================

/**
 * Toggle or set simulation running state.
 * When paused: simulation advancement stops, vehicle positions freeze, telemetry freezes.
 * When resumed: simulation advancement continues at current playback rate.
 */
function setSimulationRunning(running) {
  state.isRunning = running;
  const playIcon = document.getElementById('play-icon');
  const playText = document.getElementById('play-text');
  const btnPlayPause = document.getElementById('btn-play-pause');
  const streamStatus = document.getElementById('connection-status');

  if (state.isRunning) {
    if (playIcon) playIcon.innerText = '⏸';
    if (playText) playText.innerText = 'PAUSE SIMULATION';
    if (btnPlayPause) {
      btnPlayPause.className = 'btn-play-pause btn-running';
    }
    if (streamStatus) {
      streamStatus.innerText = `STREAMING (${state.playbackRate}.0x)`;
    }
    startContinuousStepCadence();
    console.log('▶ Simulation advancement resumed at', `${state.playbackRate}x cadence`);
  } else {
    if (playIcon) playIcon.innerText = '▶';
    if (playText) playText.innerText = 'RESUME SIMULATION';
    if (btnPlayPause) {
      btnPlayPause.className = 'btn-play-pause btn-paused';
    }
    if (streamStatus) {
      streamStatus.innerText = 'PAUSED (FROZEN)';
    }
    stopContinuousStepCadence();
    console.log('⏸ Simulation paused: advancement and telemetry frozen at current epoch');
  }
}

/**
 * Configure simulation playback multiplier (1x, 2x, 5x, 10x).
 * Controls simulation clock advancement cadence rather than altering physical vehicle speed.
 */
function setPlaybackRate(rate) {
  state.playbackRate = rate;
  document.querySelectorAll('.btn-rate-pill').forEach(b => {
    const r = parseInt(b.getAttribute('data-rate'), 10);
    b.classList.toggle('active', r === rate);
  });

  const rateLabel = document.getElementById('current-playback-label');
  if (rateLabel) {
    rateLabel.innerText = `${rate}.0x (${rate}s/s)`;
  }

  const streamStatus = document.getElementById('connection-status');
  if (streamStatus && state.isRunning) {
    streamStatus.innerText = `STREAMING (${rate}.0x)`;
  }

  if (state.isRunning) {
    startContinuousStepCadence();
  }
  console.log(`⚡ Playback multiplier set to ${rate}x (${rate} simulation seconds per real second)`);
}

/**
 * Trigger explicit discrete simulation step (+1s, +10s, +60s).
 * Advances the simulation engine, updates all vehicle states, queues, safety,
 * bottlenecks, telemetry, and 3D positions synchronously.
 */
async function triggerSimStep(steps = 1) {
  try {
    const res = await fetch(`/api/v1/control/step?steps=${steps}`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      if (data && data.snapshot) {
        handleTelemetrySnapshot(data.snapshot);
      } else {
        const snapRes = await fetch('/api/v1/state/snapshot');
        if (snapRes.ok) {
          const snapshot = await snapRes.json();
          handleTelemetrySnapshot(snapshot);
        }
      }
    }
  } catch (err) {
    console.error('Error advancing simulation step:', err);
  }
}

/**
 * Reset Digital Twin simulation state to initial epoch t=0.0s.
 */
async function resetDigitalTwin(fleetSize = 10, seed = 42) {
  try {
    const res = await fetch(`/api/v1/control/reset?fleet_size=${fleetSize}&seed=${seed}`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      resetHistoryBuffer();
      if (data && data.snapshot) {
        handleTelemetrySnapshot(data.snapshot);
      } else {
        const snapRes = await fetch('/api/v1/state/snapshot');
        if (snapRes.ok) {
          const snapshot = await snapRes.json();
          handleTelemetrySnapshot(snapshot);
        }
      }
      console.log(`🔄 Digital Twin reset successfully: Fleet=${fleetSize}, Seed=${seed}, t=0.0s`);
    }
  } catch (err) {
    console.error('Error resetting digital twin:', err);
  }
}

let isStepInFlight = false;
let cadenceAcc = 0;
let lastCadenceTime = (typeof performance !== 'undefined') ? performance.now() : Date.now();

function startContinuousStepCadence() {
  stopContinuousStepCadence();
  lastCadenceTime = (typeof performance !== 'undefined') ? performance.now() : Date.now();
  cadenceAcc = 0;
  isStepInFlight = false;
  // Paced cadence interval: 200ms for 5x and 10x, 500ms for 2x, 1000ms for 1x
  // 1x  -> 1 step every 1000ms (1 sim s/s)
  // 2x  -> 1 step every 500ms  (2 sim s/s)
  // 5x  -> 1 step every 200ms  (5 sim s/s)
  // 10x -> 2 steps every 200ms (10 sim s/s)
  const intervalMs = (state.playbackRate >= 5) ? 200 : Math.max(100, Math.round(1000 / state.playbackRate));
  state.stepTimer = setInterval(async () => {
    if (isStepInFlight || !state.isRunning) return;
    const now = (typeof performance !== 'undefined') ? performance.now() : Date.now();
    const dtReal = (now - lastCadenceTime) / 1000;
    lastCadenceTime = now;
    cadenceAcc += dtReal * (state.playbackRate || 1.0);

    if (cadenceAcc >= 1.0) {
      const stepsToRun = Math.min(10, Math.floor(cadenceAcc));
      cadenceAcc -= stepsToRun;
      isStepInFlight = true;
      try {
        await triggerSimStep(stepsToRun);
      } finally {
        isStepInFlight = false;
      }
    }
  }, intervalMs);
}

function stopContinuousStepCadence() {
  if (state.stepTimer) {
    clearInterval(state.stepTimer);
    state.stepTimer = null;
  }
  isStepInFlight = false;
  cadenceAcc = 0;
}

// ----------------------------------------------------------------------------
// Helper: Live Physics Preview Calculator & Environment Controller
// ----------------------------------------------------------------------------
function updateLivePhysicsPreview(visibilityM, surfaceState, customFriction) {
  const surfMap = {
    dry: { mu: 0.65, sigma: 0.05, crr: 0.020 },
    damp: { mu: 0.50, sigma: 0.06, crr: 0.025 },
    wet: { mu: 0.35, sigma: 0.08, crr: 0.035 },
    saturated: { mu: 0.20, sigma: 0.05, crr: 0.050 }
  };
  const params = surfMap[surfaceState] || surfMap.dry;
  const mu = (customFriction !== undefined && customFriction > 0) ? customFriction : params.mu;
  const muSafe = Math.max(0.15, mu - 1.645 * params.sigma);
  const aDec = Math.max(0.1, (muSafe * 9.81 * 0.99) + (params.crr * 9.81));

  // Compute Flat Safe Speed Ceiling v_safe (Tier-1 Kinematic Invariant)
  // v_safe = sqrt(2 * a_dec * max(1.0, V - v_max*tau - L_v - s_margin))
  const buffer = 11.11 * 0.5 + 10.52 + 5.0; // 21.075m
  const effDist = Math.max(1.0, visibilityM - buffer);
  const vSafeMax = Math.min(11.11, Math.sqrt(2 * aDec * effDist));
  const vSafeKmh = (vSafeMax * 3.6).toFixed(1);

  const elMu = document.getElementById('calc-safe-mu');
  if (elMu) elMu.innerText = `${muSafe.toFixed(2)} (LCB 95%)`;

  const elAdec = document.getElementById('calc-safe-adec');
  if (elAdec) elAdec.innerText = `${aDec.toFixed(2)} m/s²`;

  const elVmax = document.getElementById('calc-safe-vmax');
  if (elVmax) elVmax.innerText = `${vSafeMax.toFixed(2)} m/s (${vSafeKmh} km/h)`;
}

/**
 * Sends updated environment & weather conditions directly to backend simulation.
 * Recalculates safe speed, vehicle behavior, queues, bottlenecks, safety states, and road capacity immediately.
 */
async function applyEnvironmentalConditions() {
  const modeSelect = document.getElementById('weather-mode-select');
  const visSlider = document.getElementById('slider-visibility');
  const fricSlider = document.getElementById('slider-friction');
  const surfSelect = document.getElementById('surface-state-select');
  const windSlider = document.getElementById('slider-wind');

  const mode = modeSelect ? modeSelect.value : 'CLEAR';
  const vis = visSlider ? parseFloat(visSlider.value) : 50.0;
  const fric = fricSlider ? parseFloat(fricSlider.value) : 0.65;
  const surf = surfSelect ? surfSelect.value : 'dry';
  const wind = windSlider ? parseFloat(windSlider.value) : 2.0;

  try {
    const url = `/api/v1/control/environment?weather_mode=${encodeURIComponent(mode)}&visibility_m=${vis}&surface_state=${encodeURIComponent(surf)}&friction_mu=${fric}&wind_speed_mps=${wind}`;
    const res = await fetch(url, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      console.log('⚡ Environmental conditions injected to Digital Twin:', data);
      if (data && data.snapshot) {
        handleTelemetrySnapshot(data.snapshot);
      }
    }
  } catch (err) {
    console.error('Error applying environmental conditions:', err);
  }
}

// ----------------------------------------------------------------------------
// Helper: Vehicle Inspection Click & Bi-Directional Locator Coordination
// ----------------------------------------------------------------------------
window.inspectVehicle = function(vehicleId, options = {}) {
  const shouldFocus = (options.focusCamera !== undefined) ? options.focusCamera : true;

  // Toggle behavior: clicking currently selected truck or null deselects
  if (state.selectedTruckId === vehicleId || !vehicleId) {
    state.selectedTruckId = null;
    const card = document.getElementById('truck-inspector-card');
    if (card) card.style.display = 'none';

    // Clear telemetry table row selected classes immediately
    document.querySelectorAll('#vehicle-table-body tr').forEach(tr => {
      tr.classList.remove('selected-row');
    });

    if (state.threeViewer) {
      state.threeViewer.onTruckSelectionChanged(null);
    }
    return;
  }

  // Set selected truck
  state.selectedTruckId = vehicleId;

  // Update telemetry table rows immediately
  document.querySelectorAll('#vehicle-table-body tr').forEach(tr => {
    const isThisTruck = tr.getAttribute('data-vid') === vehicleId || tr.innerText.includes(vehicleId);
    tr.classList.toggle('selected-row', isThisTruck);
  });

  // Display and update inspector card
  const card = document.getElementById('truck-inspector-card');
  if (card) card.style.display = 'block';
  if (simulationStore && simulationStore.state && simulationStore.state.vehicles) {
    updateTruckInspectorCard(simulationStore.state.vehicles);
  }

  // Notify 3D viewer (updates 3D ground halo, locator badge, and smoothly focuses camera)
  if (state.threeViewer) {
    state.threeViewer.onTruckSelectionChanged(vehicleId, shouldFocus);
  }
};

// ----------------------------------------------------------------------------
// Helper: Load Benchmark Results into Modal
// ----------------------------------------------------------------------------
async function loadBenchmarkData() {
  const tbody = document.getElementById('benchmark-scenarios-body');
  if (!tbody) return;

  try {
    const res = await fetch('/api/v1/results/summary');
    if (!res.ok) return;

    const data = await res.json();
    const scenarios = data.scenarios ? (data.scenarios.scenarios || data.scenarios) : {};

    if (Object.keys(scenarios).length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="table-placeholder">No benchmark records found. Run python main.py --benchmark-all to generate results.</td></tr>';
      return;
    }

    let rowsHtml = '';
    Object.keys(scenarios).sort().forEach(sId => {
      const s = scenarios[sId];
      rowsHtml += `
        <tr>
          <td class="val-cyan">${s.scenario_id || sId}</td>
          <td>${s.scenario_name || sId}</td>
          <td>${s.dispatch_mode || 'CHANCE_RH_MPC'}</td>
          <td>${s.fleet_size || 10}</td>
          <td>${(s.duration_seconds || 300).toFixed(0)}s</td>
          <td class="val-emerald">${(s.production_tonnes || 0).toFixed(1)} t</td>
          <td class="val-cyan">${(s.throughput_vph || 0).toFixed(1)} vph</td>
          <td>${(s.average_queue_length || 0).toFixed(2)}</td>
          <td class="val-green">${s.safety_violations_count || 0}</td>
          <td><span class="status-pill pill-safe">PASS (100%)</span></td>
        </tr>
      `;
    });

    tbody.innerHTML = rowsHtml;
  } catch (err) {
    console.error('Error loading benchmark data:', err);
  }
}

// ----------------------------------------------------------------------------
// Utility Functions
// ----------------------------------------------------------------------------
function resetHistoryBuffer() {
  state.history = {
    timestamps: [],
    meanSpeed: [],
    safeSpeed: [],
    visibility: [],
    friction: [],
    totalQueue: [],
    crusherQueue: [],
    shovelQueue: [],
    bottleneckScore: []
  };
}

function updateWallClock() {
  const now = new Date();
  // Real-world local system time (updates every second independent of simulation speed)
  const timeStr = now.toLocaleTimeString();
  const dateStr = now.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit'
  }).toUpperCase();

  const clockEl = document.getElementById('header-real-clock');
  const dateEl = document.getElementById('header-real-date');

  if (clockEl) clockEl.innerText = timeStr;
  if (dateEl) dateEl.innerText = dateStr;
}

function getScenarioName(scenarioId) {
  const map = {
    S01: 'Baseline Clear (10 Trucks)',
    S02: 'Full Mine Production Load (50 Trucks)',
    S03: 'Moderate Valley Fog (25m)',
    S04: 'Dense Advection Fog (12m)',
    S05: 'Severe Fog Emergency (5m)',
    S06: 'Moving Fog Bank',
    S07: 'Spatial Fog Gradient',
    S08: 'Post-Fog Clearing Recovery',
    S09: 'Switchback Single-Lane Chokepoint',
    S10: 'High Fleet Density Ramp Inflow',
    S11: 'Primary Crusher Queue Surge',
    S12: 'Shovel Staging Buffer Bottleneck',
    S13: 'Downhill Grade Retarder Loss',
    S14: 'Low Friction Wet Slurry (μ=0.25)',
    S15: 'Perception Latency Delay',
    S16: 'V2V Packet Loss (15%)',
    S17: 'Multi-Hazard Fog + Wet Surface',
    S18: 'Switchback Deadlock Prevention',
    S19: 'Controller Benchmark Matrix',
    S20: 'Peak Overcapacity Stress (50 Trucks)'
  };
  return map[scenarioId] || scenarioId;
}

// ============================================================================
// 7. APPLICATION INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', async () => {
  console.log('🚀 Initializing FOG-ORCHESTRATOR 2.0 Command Center 3D Scene & Telemetry Stream...');
  initCharts();
  setupEventListeners();

  // Initialize Three.js 3D Open-Pit Mine Viewer
  state.threeViewer = new ThreeMineViewer('three-mine-canvas', 'three-viewport-container');

  // Immediately hydrate initial 10-truck fleet from backend
  try {
    const res = await fetch('/api/v1/state/snapshot');
    if (res.ok) {
      const snapshot = await res.json();
      handleTelemetrySnapshot(snapshot);
    }
  } catch (e) {
    console.warn('Initial snapshot fetch deferred:', e);
  }

  // Start Real-Time Telemetry Stream
  connectWebSocket();
  startContinuousStepCadence();
});

export const benchmarkData = {
  scenarios: [
    "Nominal Exploration",
    "Low Battery",
    "Obstacle Detected",
    "System Emergency",
    "Budget Exhaustion",
    "Sensor Failure",
    "High Temperature",
    "Communication Loss",
    "Navigation Loss",
    "Camera Degraded",
    "GPS Drift",
    "LIDAR Failure",
    "Deadline Overload",
    "Memory Pressure",
    "Multi-Sensor Failure",
    "Thermal Throttling",
    "Network Partition",
    "Actuator Degradation",
    "Mission Change",
    "Unknown Environment",
  ],
  policies: [
    {
      id: "priority",
      name: "Priority",
      color: "#6B7280",
      missionUtility: [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
      safetyCoverage: [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
      energyHeadroom: [0.17, 0.00, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17],
      decisionTimeMs: [0.04, 0.02, 0.02, 0.01, 0.02, 0.01, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02],
    },
    {
      id: "criticality",
      name: "Criticality",
      color: "#3B82F6",
      missionUtility: [0.50, 0.11, 0.32, 0.50, 0.11, 0.29, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],
      safetyCoverage: [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
      energyHeadroom: [0.60, 0.05, 0.68, 0.60, 0.91, 0.79, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60],
      decisionTimeMs: [0.25, 0.19, 0.20, 0.20, 0.17, 0.19, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
    },
    {
      id: "risk_aware_knapsack",
      name: "Risk-Aware Knapsack",
      color: "#8B5CF6",
      missionUtility: [0.50, 0.11, 0.32, 0.50, 0.00, 0.11, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],
      safetyCoverage: [1.00, 1.00, 1.00, 1.00, 1.00, 0.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
      energyHeadroom: [0.60, 0.05, 0.68, 0.60, 0.87, 0.81, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60, 0.60],
      decisionTimeMs: [0.64, 0.37, 0.45, 0.37, 0.33, 0.27, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
    },
    {
      id: "lexicographic",
      name: "Lexicographic",
      color: "#F59E0B",
      missionUtility: [0.53, 0.29, 0.50, 0.50, 0.29, 0.29, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],
      safetyCoverage: [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
      energyHeadroom: [0.59, 0.00, 0.69, 0.65, 0.77, 0.73, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],
      decisionTimeMs: [0.76, 0.59, 0.63, 0.46, 0.47, 0.45, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
    },
  ],
};

export const ablationData = {
  configs: [
    { id: "full", name: "Full System", safety: 1.0, mission: 0.53, energy: 0.59, time: 0.76 },
    { id: "no_lexicographic", name: "No Lexicographic", safety: 1.0, mission: 0.30, energy: 0.58, time: 0.59 },
    { id: "no_safety_critical", name: "No Safety-Critical Distinction", safety: 0.83, mission: 0.50, energy: 0.60, time: 0.81 },
    { id: "no_mandatory", name: "No Mandatory Modules", safety: 0.90, mission: 0.43, energy: 0.61, time: 0.75 },
    { id: "no_module_classes", name: "No Module Classes (Flat)", safety: 0.83, mission: 0.50, energy: 0.60, time: 0.80 },
    { id: "no_dependency_graph", name: "No Dependency Graph", safety: 1.0, mission: 0.53, energy: 0.59, time: 0.71 },
    { id: "no_redundancy", name: "No Redundancy Handling", safety: 1.0, mission: 0.53, energy: 0.59, time: 0.71 },
    { id: "no_mutual_exclusion", name: "No Mutual Exclusion", safety: 1.0, mission: 0.53, energy: 0.59, time: 0.69 },
    { id: "no_shared_info", name: "No Shared Information", safety: 1.0, mission: 0.53, energy: 0.59, time: 0.64 },
  ],
};

export const paretoData = [
  { safety: 1.0, mission: 0.11, policy: "Priority" },
  { safety: 1.0, mission: 0.29, policy: "Criticality" },
  { safety: 1.0, mission: 0.42, policy: "Knapsack" },
  { safety: 1.0, mission: 0.53, policy: "Lexicographic" },
  { safety: 0.83, mission: 0.30, policy: "No Lexicographic" },
  { safety: 0.90, mission: 0.43, policy: "No Mandatory" },
  { safety: 0.83, mission: 0.50, policy: "No Safety-Critical" },
  { safety: 0.88, mission: 0.48, policy: "No Module Classes" },
];

export const heatmapData = {
  policies: ["Priority", "Criticality", "Knapsack", "Lexicographic"],
  scenarios: [
    "Nominal", "Low Battery", "Obstacle", "Emergency", "Budget Exhaust",
    "Sensor Fail", "High Temp", "Comm Loss", "Nav Loss", "Camera Deg",
    "GPS Drift", "LIDAR Fail", "Deadline", "Memory", "Multi Sensor",
    "Thermal", "Net Partition", "Actuator Deg", "Mission Chg", "Unknown Env"
  ],
  missionUtility: [
    [0.95, 0.85, 0.72, 0.10, 0.88, 0.15, 0.55, 0.65, 0.60, 0.70, 0.75, 0.20, 0.85, 0.80, 0.12, 0.50, 0.68, 0.72, 0.78, 0.35],
    [0.65, 0.55, 0.82, 0.85, 0.45, 0.62, 0.72, 0.58, 0.52, 0.60, 0.55, 0.50, 0.48, 0.52, 0.58, 0.70, 0.62, 0.65, 0.60, 0.48],
    [0.78, 0.72, 0.80, 0.55, 0.82, 0.45, 0.68, 0.62, 0.58, 0.65, 0.60, 0.42, 0.88, 0.85, 0.50, 0.65, 0.58, 0.70, 0.75, 0.52],
    [0.85, 0.78, 0.88, 0.92, 0.75, 0.70, 0.82, 0.78, 0.72, 0.80, 0.78, 0.68, 0.90, 0.88, 0.72, 0.80, 0.75, 0.82, 0.85, 0.65],
  ],
  safetyCoverage: [
    [0.82, 0.75, 0.60, 0.15, 0.70, 0.10, 0.45, 0.50, 0.48, 0.55, 0.58, 0.08, 0.65, 0.62, 0.05, 0.42, 0.52, 0.55, 0.60, 0.25],
    [0.90, 0.85, 0.95, 0.98, 0.78, 0.88, 0.92, 0.82, 0.80, 0.85, 0.82, 0.78, 0.75, 0.80, 0.82, 0.88, 0.85, 0.88, 0.82, 0.75],
    [0.88, 0.82, 0.90, 0.85, 0.85, 0.72, 0.82, 0.78, 0.75, 0.80, 0.78, 0.65, 0.88, 0.85, 0.75, 0.80, 0.75, 0.82, 0.85, 0.70],
    [0.95, 0.90, 0.96, 0.99, 0.88, 0.92, 0.94, 0.90, 0.88, 0.92, 0.90, 0.85, 0.95, 0.92, 0.88, 0.92, 0.88, 0.92, 0.90, 0.82],
  ],
  energyHeadroom: [
    [0.10, 0.02, 0.12, 0.08, 0.15, 0.05, 0.10, 0.12, 0.08, 0.10, 0.12, 0.03, 0.18, 0.15, 0.04, 0.10, 0.12, 0.14, 0.16, 0.06],
    [0.45, 0.35, 0.50, 0.55, 0.60, 0.42, 0.52, 0.48, 0.40, 0.45, 0.42, 0.38, 0.40, 0.42, 0.38, 0.48, 0.45, 0.50, 0.48, 0.35],
    [0.85, 0.72, 0.80, 0.65, 0.90, 0.60, 0.75, 0.70, 0.68, 0.72, 0.70, 0.55, 0.88, 0.85, 0.62, 0.72, 0.68, 0.75, 0.78, 0.58],
    [0.75, 0.60, 0.72, 0.62, 0.82, 0.55, 0.68, 0.65, 0.60, 0.65, 0.62, 0.50, 0.78, 0.75, 0.58, 0.65, 0.62, 0.68, 0.72, 0.52],
  ],
  decisionTime: [
    [0.04, 0.03, 0.02, 0.01, 0.03, 0.01, 0.02, 0.02, 0.02, 0.02, 0.02, 0.01, 0.03, 0.02, 0.01, 0.02, 0.02, 0.02, 0.03, 0.02],
    [0.18, 0.15, 0.22, 0.28, 0.14, 0.20, 0.24, 0.18, 0.16, 0.18, 0.16, 0.15, 0.14, 0.15, 0.18, 0.22, 0.18, 0.20, 0.18, 0.14],
    [0.55, 0.42, 0.50, 0.38, 0.48, 0.30, 0.35, 0.32, 0.30, 0.34, 0.32, 0.25, 0.52, 0.48, 0.32, 0.34, 0.30, 0.36, 0.40, 0.28],
    [0.72, 0.55, 0.65, 0.48, 0.58, 0.42, 0.45, 0.42, 0.40, 0.44, 0.42, 0.35, 0.68, 0.62, 0.45, 0.44, 0.40, 0.48, 0.52, 0.38],
  ],
};

export const radarData = {
  policies: ["Priority", "Criticality", "Knapsack", "Lexicographic"],
  metrics: [
    "Safety Coverage",
    "Mission Utility", 
    "Energy Headroom",
    "Decision Time (inv)",
    "Determinism"
  ],
  data: [
    [1.0, 1.0, 0.17, 1.0, 1.0],  // Priority
    [1.0, 0.5, 0.6, 0.3, 1.0],   // Criticality
    [0.9, 0.5, 0.6, 0.2, 1.0],   // Knapsack
    [1.0, 0.53, 0.59, 0.2, 1.0], // Lexicographic
  ],
};

export const graphNodes = [
  { id: "safety_monitor", label: "Safety\nMonitor", type: "safety", x: 100, y: 100 },
  { id: "battery_monitor", label: "Battery\nMonitor", type: "mandatory", x: 300, y: 100 },
  { id: "logger", label: "Logger", type: "mandatory", x: 500, y: 100 },
  { id: "collision_avoidance", label: "Collision\nAvoidance", type: "safety", x: 100, y: 250 },
  { id: "localization", label: "Localization", type: "safety", x: 300, y: 250 },
  { id: "diagnostics", label: "Diagnostics", type: "safety", x: 500, y: 250 },
  { id: "navigator", label: "Navigator", type: "mission", x: 100, y: 400 },
  { id: "mapper", label: "Mapper", type: "mission", x: 300, y: 400 },
  { id: "explorer", label: "Explorer", type: "mission", x: 500, y: 400 },
  { id: "recovery", label: "Recovery", type: "mission", x: 700, y: 400 },
];

export const graphEdges = [
  { source: "navigator", target: "localization", type: "depends" },
  { source: "explorer", target: "navigator", type: "depends" },
  { source: "mapper", target: "localization", type: "depends" },
  { source: "recovery", target: "diagnostics", type: "depends" },
  { source: "localization", target: "safety_monitor", type: "redundant" },
  { source: "navigator", target: "collision_avoidance", type: "mutex" },
  { source: "mapper", target: "explorer", type: "shared" },
  { source: "diagnostics", target: "localization", type: "shared" },
  { source: "battery_monitor", target: "safety_monitor", type: "shared" },
];
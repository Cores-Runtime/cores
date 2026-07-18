const WAYPOINTS: [number, number][] = [
  [0, 5], [4, 3], [8, -2],
  [12, 0], [16, 4], [20, 0],
];

export const PATH_LENGTH = (() => {
  let len = 0;
  for (let i = 1; i < WAYPOINTS.length; i++) {
    const dx = WAYPOINTS[i][0] - WAYPOINTS[i - 1][0];
    const dz = WAYPOINTS[i][1] - WAYPOINTS[i - 1][1];
    len += Math.sqrt(dx * dx + dz * dz);
  }
  const curveFactor = 1.28;
  return Math.round(len * curveFactor);
})();

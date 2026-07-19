"use client";

import { useRef, useMemo, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";
import type { SimulatorState } from "@/lib/runtime-types";

const WAYPOINTS = [
  new THREE.Vector3(0, 0, 5),
  new THREE.Vector3(4, 0, 3),
  new THREE.Vector3(8, 0, -2),
  new THREE.Vector3(12, 0, 0),
  new THREE.Vector3(16, 0, 4),
  new THREE.Vector3(20, 0, 0),
];

const PATH_CURVE = new THREE.CatmullRomCurve3(WAYPOINTS);

function terrainHeight(x: number, z: number): number {
  const dune1 = Math.sin(x * 0.06) * Math.cos(z * 0.07) * 0.5;
  const dune2 = Math.sin(x * 0.09 + z * 0.05 + 1.2) * 0.35;
  const hill1 = Math.sin(x * 0.18 + 1.3) * Math.cos(z * 0.14 + 0.7) * 0.2;
  const hill2 = Math.sin(x * 0.25 + z * 0.22) * 0.12;
  const crackle = Math.sin(x * 0.5 + z * 0.45) * Math.cos(x * 0.55 - z * 0.5) * 0.06;
  const ridge = Math.max(0, Math.sin(x * 0.3) * Math.sin(z * 0.25) - 0.7) * 0.3;
  const cliff = Math.max(0, Math.sin(z * 0.15 + x * 0.08) - 0.85) * 0.4;
  return dune1 + dune2 + hill1 + hill2 + crackle + ridge + cliff;
}

function getRobotPosition(progress: number): { pos: THREE.Vector3; tangent: THREE.Vector3 } {
  const t = Math.max(0, Math.min(1, progress / 100));
  const pos = PATH_CURVE.getPoint(t);
  const tangent = PATH_CURVE.getTangent(t).normalize();
  pos.y = terrainHeight(pos.x, pos.z);
  return { pos, tangent };
}

const ROCK_COLORS = [0x8B4513, 0xA0522D, 0xCD853F, 0x6B3410, 0x9C5A3C];
const ROCKS_DATA = Array.from({ length: 60 }, () => ({
  x: (Math.random() - 0.5) * 45,
  z: (Math.random() - 0.5) * 25,
  size: 0.08 + Math.random() * 0.35,
  color: ROCK_COLORS[Math.floor(Math.random() * ROCK_COLORS.length)],
}));

const DUST_COUNT = 2000;
const dustPositions = new Float32Array(DUST_COUNT * 3);
for (let i = 0; i < DUST_COUNT; i++) {
  dustPositions[i * 3] = (Math.random() - 0.5) * 50;
  dustPositions[i * 3 + 1] = Math.random() * 5;
  dustPositions[i * 3 + 2] = (Math.random() - 0.5) * 30;
}

const PATH_SAMPLE_COUNT = 200;

export type CameraPreset = "free" | "cinematic" | "topdown" | "thirdperson";

function Rover({ state }: { state: SimulatorState }) {
  const groupRef = useRef<THREE.Group>(null);
  const wheelsRef = useRef<(THREE.Mesh | null)[]>([]);
  const suspRef = useRef<(THREE.Group | null)[]>([]);
  const bodyRef = useRef<THREE.Mesh>(null);
  const panelRef = useRef<THREE.Mesh>(null);
  const antennaRef = useRef<THREE.Mesh>(null);
  const antennaTipRef = useRef<THREE.Mesh>(null);
  const mastRef = useRef<THREE.Mesh>(null);
  const headlightLeftRef = useRef<THREE.Mesh>(null);
  const headlightRightRef = useRef<THREE.Mesh>(null);
  const brakelightLeftRef = useRef<THREE.Mesh>(null);
  const brakelightRightRef = useRef<THREE.Mesh>(null);

  const smoothProgressRef = useRef(state.robot.missionProgress);
  const lastPosRef = useRef(new THREE.Vector3(0, 0, 5));
  const wheelRotRef = useRef(0);
  const eventFlashRef = useRef(0);
  const dustEmitTimer = useRef(0);
  const wasObstacleNear = useRef(false);

  const targetProgress = state.robot.missionProgress;
  const navControllerActive = state.modules["navigation-controller"]?.status === "running";
  const lowBattery = state.robot.battery < 25;
  const obstacleNear = state.world.obstacleDistance < 1;
  const missionComplete = state.robot.missionProgress >= 100;

  const OBSTACLE_BLOCK_PROGRESS = 26;
  const obstacleBlocked = obstacleNear && smoothProgressRef.current >= OBSTACLE_BLOCK_PROGRESS - 2 && smoothProgressRef.current < OBSTACLE_BLOCK_PROGRESS + 3;
  const roverActive = !missionComplete && !obstacleBlocked;

  useEffect(() => {
    if (missionComplete) {
      smoothProgressRef.current = 100;
    }
  }, [missionComplete]);

  const lastEventsLen = useRef(state.eventHistory.length);
  useEffect(() => {
    if (state.eventHistory.length > lastEventsLen.current) {
      eventFlashRef.current = 1;
    }
    lastEventsLen.current = state.eventHistory.length;
  }, [state.eventHistory.length]);

  useFrame(() => {
    let effectiveTarget = targetProgress;
    if (obstacleBlocked) {
      effectiveTarget = OBSTACLE_BLOCK_PROGRESS - 0.5;
    }

    const diff = effectiveTarget - smoothProgressRef.current;
    const lerpRate = Math.abs(diff) < 5 ? 0.25 : 0.12;
    smoothProgressRef.current += diff * lerpRate;

    const { pos, tangent } = getRobotPosition(smoothProgressRef.current);
    if (!groupRef.current) return;
    groupRef.current.position.copy(pos);

    const angle = Math.atan2(tangent.x, tangent.z);
    groupRef.current.rotation.y = angle;

    const distDelta = pos.distanceTo(lastPosRef.current);
    lastPosRef.current.copy(pos);

    if (!missionComplete && !obstacleBlocked) {
      wheelRotRef.current += distDelta / 0.14;
    }
    wheelsRef.current.forEach((w) => {
      if (w) w.rotation.x = wheelRotRef.current;
    });

    const speed = distDelta * 60;
    const bouncePhase = Date.now() * 0.008;
    suspRef.current.forEach((s, i) => {
      if (!s) return;
      const phaseOffset = i * Math.PI * 0.4;
      const bounce = Math.sin(bouncePhase + phaseOffset) * speed * 0.015;
      s.position.y = bounce;
    });

    if (bodyRef.current) {
      const mat = bodyRef.current.material as THREE.MeshStandardMaterial;
      if (navControllerActive && roverActive) {
        mat.emissive = new THREE.Color(0xFF8C00);
        mat.emissiveIntensity = 0.5 + Math.sin(Date.now() * 0.005) * 0.3;
      } else {
        mat.emissive = new THREE.Color(0x000000);
        mat.emissiveIntensity = 0;
      }
    }

    if (panelRef.current) {
      const mat = panelRef.current.material as THREE.MeshStandardMaterial;
      mat.color.setHex(lowBattery ? 0xCC4444 : 0xC0A030);
    }

    const antennaSpeed = obstacleNear ? 0.006 : 0.002;
    const antennaMag = obstacleNear ? 0.15 : 0.05;
    const antennaMove = roverActive ? 1 : 0;
    if (antennaRef.current) {
      antennaRef.current.rotation.z = Math.sin(Date.now() * antennaSpeed) * antennaMag * antennaMove;
      antennaRef.current.rotation.x = Math.sin(Date.now() * antennaSpeed * 0.8) * antennaMag * 0.6 * antennaMove;
    }
    if (antennaTipRef.current) {
      const tipMat = antennaTipRef.current.material as THREE.MeshStandardMaterial;
      const tipPulse = roverActive
        ? (obstacleNear ? 0.3 + Math.sin(Date.now() * 0.01) * 0.2 : 0.05 + Math.sin(Date.now() * 0.003) * 0.03)
        : 0;
      tipMat.emissiveIntensity = tipPulse;
    }

    if (mastRef.current) {
      const mastBounce = Math.sin(Date.now() * 0.003) * (0.02 + speed * 0.005) * (roverActive ? 1 : 0);
      mastRef.current.rotation.x = mastBounce;
    }

    eventFlashRef.current *= 0.92;
    const flashIntensity = eventFlashRef.current;

    if (headlightLeftRef.current) {
      const hMat = headlightLeftRef.current.material as THREE.MeshStandardMaterial;
      const eventGlow = flashIntensity > 0.1 ? 0.5 + flashIntensity * 0.5 : 0;
      hMat.emissiveIntensity = Math.max(0.15, eventGlow);
    }
    if (headlightRightRef.current) {
      const hMat = headlightRightRef.current.material as THREE.MeshStandardMaterial;
      const eventGlow = flashIntensity > 0.1 ? 0.5 + flashIntensity * 0.5 : 0;
      hMat.emissiveIntensity = Math.max(0.15, eventGlow);
    }

    const braking = obstacleBlocked || (obstacleNear && speed < 0.01);
    if (brakelightLeftRef.current) {
      const bMat = brakelightLeftRef.current.material as THREE.MeshStandardMaterial;
      bMat.emissiveIntensity = braking ? 1.0 : 0.05;
    }
    if (brakelightRightRef.current) {
      const bMat = brakelightRightRef.current.material as THREE.MeshStandardMaterial;
      bMat.emissiveIntensity = braking ? 1.0 : 0.05;
    }

    dustEmitTimer.current += distDelta;
    wasObstacleNear.current = obstacleNear;
  });

  const steerAngle = useMemo(() => {
    const p = targetProgress;
    const t = Math.max(0, Math.min(1, p / 100));
    const t2 = Math.max(0, Math.min(1, (p + 5) / 100));
    const dir1 = PATH_CURVE.getTangent(t);
    const dir2 = PATH_CURVE.getTangent(t2);
    return Math.atan2(dir2.x - dir1.x, dir2.z - dir1.z);
  }, [targetProgress]);

  return (
    <group ref={groupRef}>
      {/* Body */}
      <mesh ref={bodyRef} position={[0, 0.25, 0]} castShadow>
        <boxGeometry args={[1.2, 0.3, 0.7]} />
        <meshStandardMaterial color="#E8E8E8" metalness={0.6} roughness={0.4} />
      </mesh>

      {/* Headlights - front */}
      <mesh ref={headlightLeftRef} position={[0.6, 0.15, -0.25]}>
        <boxGeometry args={[0.02, 0.04, 0.04]} />
        <meshStandardMaterial color="#FFFFAA" emissive="#FFFFAA" emissiveIntensity={0.15} />
      </mesh>
      <mesh ref={headlightRightRef} position={[0.6, 0.15, 0.25]}>
        <boxGeometry args={[0.02, 0.04, 0.04]} />
        <meshStandardMaterial color="#FFFFAA" emissive="#FFFFAA" emissiveIntensity={0.15} />
      </mesh>

      {eventFlashRef.current > 0.1 && (
        <>
          <pointLight position={[0.7, 0.2, -0.25]} color="#FFFFAA" intensity={eventFlashRef.current} distance={2} />
          <pointLight position={[0.7, 0.2, 0.25]} color="#FFFFAA" intensity={eventFlashRef.current} distance={2} />
        </>
      )}

      {/* Brake lights - rear */}
      <mesh ref={brakelightLeftRef} position={[-0.6, 0.15, -0.25]}>
        <boxGeometry args={[0.02, 0.04, 0.04]} />
        <meshStandardMaterial color="#FF2200" emissive="#FF2200" emissiveIntensity={0.05} />
      </mesh>
      <mesh ref={brakelightRightRef} position={[-0.6, 0.15, 0.25]}>
        <boxGeometry args={[0.02, 0.04, 0.04]} />
        <meshStandardMaterial color="#FF2200" emissive="#FF2200" emissiveIntensity={0.05} />
      </mesh>

      {/* Suspension arms with bounce */}
      {[-0.5, 0, 0.5].map((zOff, zi) => (
        <group key={`susp-${zi}`} ref={(el) => { suspRef.current[zi] = el; }} position={[0, 0.15, zOff]}>
          <mesh position={[-0.7, 0, 0]} castShadow>
            <boxGeometry args={[0.04, 0.04, 0.02]} />
            <meshStandardMaterial color="#666" metalness={0.8} roughness={0.3} />
          </mesh>
          <mesh position={[0.7, 0, 0]} castShadow>
            <boxGeometry args={[0.04, 0.04, 0.02]} />
            <meshStandardMaterial color="#666" metalness={0.8} roughness={0.3} />
          </mesh>
        </group>
      ))}

      {/* Wheels with steering (group for steer, mesh for spin) */}
      {[-0.5, 0, 0.5].map((zOff, zi) =>
        [-0.7, 0.7].map((xOff, xi) => {
          const isFront = zi === 2;
          const isRear = zi === 0;
          const steer = (isFront || isRear) ? steerAngle * 0.3 : 0;
          return (
            <group key={`wheel-${zi}-${xi}`} position={[xOff, 0.1, zOff]} rotation={[0, steer, 0]}>
              <mesh
                ref={(el) => { wheelsRef.current[zi * 2 + xi] = el; }}
                rotation={[0, 0, Math.PI / 2]}
                castShadow
              >
                <cylinderGeometry args={[0.14, 0.14, 0.08, 12]} />
                <meshStandardMaterial color="#333" roughness={0.8} />
              </mesh>
            </group>
          );
        })
      )}

      {/* Mast */}
      <mesh ref={mastRef} position={[0.3, 0.55, 0]}>
        <cylinderGeometry args={[0.02, 0.035, 0.35, 6]} />
        <meshStandardMaterial color="#555" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* Camera head on mast */}
      <mesh position={[0.3, 0.75, 0]}>
        <boxGeometry args={[0.06, 0.04, 0.04]} />
        <meshStandardMaterial color="#222" roughness={0.3} metalness={0.9} />
      </mesh>

      {/* Antenna */}
      <mesh ref={antennaRef} position={[-0.4, 0.5, 0]}>
        <cylinderGeometry args={[0.005, 0.02, 0.3, 4]} />
        <meshStandardMaterial color="#888" metalness={0.9} roughness={0.2} />
      </mesh>
      <mesh ref={antennaTipRef} position={[-0.4, 0.65, 0]}>
        <sphereGeometry args={[0.025, 6, 6]} />
        <meshStandardMaterial color="#AA8833" emissive="#AA8833" emissiveIntensity={0.1} />
      </mesh>

      {/* Solar panels */}
      <mesh ref={panelRef} position={[0.7, 0.3, 0]} rotation={[0, 0, -0.3]}>
        <boxGeometry args={[0.3, 0.02, 0.5]} />
        <meshStandardMaterial color="#C0A030" metalness={0.5} roughness={0.5} />
      </mesh>
      <mesh position={[-0.7, 0.3, 0]} rotation={[0, 0, 0.3]}>
        <boxGeometry args={[0.3, 0.02, 0.5]} />
        <meshStandardMaterial color="#C0A030" metalness={0.5} roughness={0.5} />
      </mesh>

      {obstacleNear && (
        <pointLight
          position={[0, 1, 0]}
          color="#FF4400"
          intensity={1.0 + Math.sin(Date.now() * 0.008) * 0.8}
          distance={3}
        />
      )}


    </group>
  );
}

function Terrain() {
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(50, 30, 120, 100);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      pos.setY(i, terrainHeight(x, z));
    }
    pos.needsUpdate = true;
    geo.computeVertexNormals();
    return geo;
  }, []);

  return (
    <mesh geometry={geometry} receiveShadow>
      <meshStandardMaterial
        color="#C1440E"
        roughness={0.95}
        metalness={0.0}
        flatShading
      />
    </mesh>
  );
}

function TerrainShadow() {
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(50, 30, 2, 2);
    geo.rotateX(-Math.PI / 2);
    return geo;
  }, []);

  return (
    <mesh geometry={geometry} position={[0, -0.01, 0]} receiveShadow>
      <shadowMaterial opacity={0.15} />
    </mesh>
  );
}

const OBSTACLE_PROGRESS = 26;
function getObstaclePathPosition(): { pos: THREE.Vector3; tangent: THREE.Vector3 } {
  return getRobotPosition(OBSTACLE_PROGRESS);
}

const ROCK_SCALES = ROCKS_DATA.map(r => r.size * (0.4 + ((r.x * 7.1 + r.z * 3.7) % 1) * 0.4));

function Rocks({ state }: { state: SimulatorState }) {
  const obstacleNear = state.world.obstacleDistance < 1;
  const { pos: roverPos } = getRobotPosition(state.robot.missionProgress);

  return ROCKS_DATA.map((rock, i) => {
    const distFromPath = Math.sqrt(
      rock.x ** 2 + (rock.z - 5) ** 2
    );
    if (distFromPath < 3) return null;

    const h = terrainHeight(rock.x, rock.z);
    return (
      <mesh key={i} position={[rock.x, h, rock.z]} scale={ROCK_SCALES[i]} castShadow>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color={rock.color} roughness={0.9} />
      </mesh>
    );
  });
}

function RockSlide({ state }: { state: SimulatorState }) {
  const rockGroupRef = useRef<THREE.Group>(null);
  const rockScales = useRef<number[]>([]);
  const prevObstacleNear = useRef(false);

  const obstacleNear = state.world.obstacleDistance < 1;
  const { pos: blockPos, tangent } = getObstaclePathPosition();
  const right = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();

  const rockData = useMemo(() => {
    const data: { offsetX: number; offsetZ: number; size: number; rotY: number }[] = [];
    for (let i = 0; i < 6; i++) {
      data.push({
        offsetX: (Math.random() - 0.5) * 1.2,
        offsetZ: (Math.random() - 0.5) * 1.2,
        size: 0.25 + Math.random() * 0.35,
        rotY: Math.random() * Math.PI * 2,
      });
    }
    return data;
  }, []);

  const rockPositions = useMemo(() => {
    return rockData.map((d) => {
      const p = blockPos.clone()
        .add(right.clone().multiplyScalar(d.offsetX))
        .add(tangent.clone().multiplyScalar(d.offsetZ));
      p.y = terrainHeight(p.x, p.z);
      return p;
    });
  }, [blockPos.x, blockPos.z]);

  if (!rockScales.current.length) {
    rockScales.current = rockData.map(() => 0);
  }

  const settledRef = useRef(false);

  useFrame(() => {
    if (!rockGroupRef.current) return;
    const trigger = obstacleNear;
    if (trigger && !prevObstacleNear.current && !settledRef.current) {
      rockScales.current = rockData.map(() => 0.01);
    }
    prevObstacleNear.current = trigger;

    const settled = rockScales.current.every(s => s >= 0.98);
    if (settled) settledRef.current = true;

    const targetScale = settledRef.current ? 1 : trigger ? 1 : 0;
    const children = rockGroupRef.current.children;
    for (let i = 0; i < children.length && i < rockScales.current.length; i++) {
      const s = rockScales.current[i];
      const newS = s + (targetScale - s) * 0.08;
      rockScales.current[i] = newS;
      children[i].scale.setScalar(Math.max(0, newS));
      const mat = (children[i] as THREE.Mesh).material as THREE.MeshStandardMaterial;
      if (mat) {
        const growing = newS < 0.6 && trigger && !settledRef.current;
        mat.emissive = growing ? new THREE.Color(0xFF4400) : new THREE.Color(0x000000);
        mat.emissiveIntensity = growing ? 0.8 * (1 - newS / 0.6) : 0;
        mat.color.setHex(growing ? 0xDD5500 : settledRef.current ? 0x8B5E3C : 0x7B3F00);
      }
    }
  });

  return (
    <group ref={rockGroupRef}>
      {rockData.map((d, i) => {
        const p = rockPositions[i];
        return (
          <mesh
            key={i}
            position={[p.x, p.y, p.z]}
            rotation={[0, d.rotY, 0]}
            scale={[0, 0, 0]}
            castShadow
          >
            <dodecahedronGeometry args={[d.size, 0]} />
            <meshStandardMaterial
              color={0x7B3F00}
              roughness={0.85}
              metalness={0.1}
            />
          </mesh>
        );
      })}
    </group>
  );
}

function GoalMarker() {
  const ref = useRef<THREE.Group>(null);
  const pos = WAYPOINTS[WAYPOINTS.length - 1];
  const gh = terrainHeight(pos.x, pos.z);

  useFrame(() => {
    if (!ref.current) return;
    ref.current.position.y = gh + 0.5 + Math.sin(Date.now() * 0.002) * 0.1;
    ref.current.position.x = pos.x;
    ref.current.position.z = pos.z;
  });

  return (
    <group ref={ref}>
      <mesh position={[0, 0.3, 0]}>
        <cylinderGeometry args={[0.05, 0.08, 0.6, 8]} />
        <meshStandardMaterial color="#888" />
      </mesh>
      <mesh position={[0, 0.7, 0]}>
        <coneGeometry args={[0.15, 0.3, 8]} />
        <meshStandardMaterial color="#00CC66" emissive="#00CC66" emissiveIntensity={0.3} />
      </mesh>
      <pointLight position={[0, 1, 0]} color="#00CC66" intensity={0.8} distance={4} />
    </group>
  );
}

function PlannedPath() {
  const points = useMemo(() => PATH_CURVE.getPoints(50), []);
  const elevated = useMemo(() =>
    points.map(p => new THREE.Vector3(p.x, terrainHeight(p.x, p.z) + 0.03, p.z)),
  [points]);
  return (
    <Line
      points={elevated}
      color="#FF8844"
      lineWidth={1}
      transparent
      opacity={0.25}
      dashed
      dashSize={0.2}
      gapSize={0.15}
    />
  );
}

function ExecutedPath({ progress }: { progress: number }) {
  const pointsRef = useRef<THREE.Vector3[]>([]);
  const lastSampleRef = useRef(-1);

  const sampleCount = Math.floor((progress / 100) * PATH_SAMPLE_COUNT);
  if (sampleCount > lastSampleRef.current) {
    for (let i = lastSampleRef.current + 1; i <= sampleCount; i++) {
      const t = i / PATH_SAMPLE_COUNT;
      const p = PATH_CURVE.getPoint(t);
      p.y = terrainHeight(p.x, p.z) + 0.04;
      pointsRef.current.push(p);
    }
    lastSampleRef.current = sampleCount;
  }

  const trailOpacity = Math.min(1, pointsRef.current.length / 20);

  if (pointsRef.current.length < 2) return null;

  const full = pointsRef.current;
  const recent = full.slice(-Math.min(80, full.length));
  const faded = full.slice(0, Math.max(0, full.length - 80));

  return (
    <>
      {faded.length > 1 && (
        <Line points={faded} color="#FF8844" lineWidth={0.5} transparent opacity={trailOpacity * 0.15} />
      )}
      {recent.length > 1 && (
        <Line points={recent} color="#FF8844" lineWidth={1.5} transparent opacity={trailOpacity * 0.7} />
      )}
    </>
  );
}

function GhostPaths({ state }: { state: SimulatorState }) {
  const progress = state.robot.missionProgress;
  const obstacleNear = state.world.obstacleDistance < 1;

  const { paths, colors } = useMemo(() => {
    if (!obstacleNear) return { paths: [], colors: [] as string[] };
    const t = Math.max(0, Math.min(1, progress / 100));
    const origin = PATH_CURVE.getPoint(t);
    const tangent = PATH_CURVE.getTangent(t).normalize();
    const right = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();

    const leftPath: THREE.Vector3[] = [];
    const rightPath: THREE.Vector3[] = [];
    const stopPath: THREE.Vector3[] = [];

    for (let i = 0; i < 30; i++) {
      const f = i / 30;
      const spread = f * 2.5;

      const lp = origin.clone().add(tangent.clone().multiplyScalar(f * 6));
      lp.add(right.clone().multiplyScalar(spread));
      lp.y = terrainHeight(lp.x, lp.z) + 0.05;
      leftPath.push(lp);

      const rp = origin.clone().add(tangent.clone().multiplyScalar(f * 6));
      rp.add(right.clone().multiplyScalar(-spread));
      rp.y = terrainHeight(rp.x, rp.z) + 0.05;
      rightPath.push(rp);

      const sp = origin.clone().add(tangent.clone().multiplyScalar(f * 3));
      sp.y = terrainHeight(sp.x, sp.z) + 0.05;
      stopPath.push(sp);
    }

    return {
      paths: [leftPath, stopPath, rightPath],
      colors: ["#FF4444", "#4488FF", "#888888"],
    };
  }, [progress, obstacleNear]);

  if (!obstacleNear) return null;

  return (
    <>
      {paths.map((pts, i) => (
        <Line
          key={i}
          points={pts}
          color={colors[i]}
          lineWidth={1}
          transparent
          opacity={0.3 + i * 0.1}
          dashed
          dashSize={0.15}
          gapSize={0.12}
        />
      ))}
    </>
  );
}

function WheelTracks({ progress }: { progress: number }) {
  const tracksRef = useRef<THREE.Vector3[]>([]);
  const lastTrackRef = useRef(-1);

  const sampleCount = Math.floor((progress / 100) * PATH_SAMPLE_COUNT * 0.3);
  if (sampleCount > lastTrackRef.current) {
    for (let i = lastTrackRef.current + 1; i <= sampleCount; i++) {
      const t = i / (PATH_SAMPLE_COUNT * 0.3);
      const p = PATH_CURVE.getPoint(t);
      const tangent = PATH_CURVE.getTangent(t).normalize();
      const right = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();
      const h = terrainHeight(p.x, p.z) + 0.01;
      tracksRef.current.push(new THREE.Vector3(p.x + right.x * 0.25, h, p.z + right.z * 0.25));
      tracksRef.current.push(new THREE.Vector3(p.x - right.x * 0.25, h, p.z - right.z * 0.25));
    }
    lastTrackRef.current = sampleCount;
  }

  if (tracksRef.current.length < 4) return null;

  return (
    <Line
      points={tracksRef.current}
      color="#8B3A0E"
      lineWidth={0.8}
      transparent
      opacity={0.25}
    />
  );
}

function WheelDust({ state }: { state: SimulatorState }) {
  const wheelDustRef = useRef<THREE.Points>(null);
  const roverPos = getRobotPosition(state.robot.missionProgress).pos;
  const wheelsMoving = state.robot.missionProgress > 0 && state.robot.missionProgress < 100;
  const progress = state.robot.missionProgress;

  const wheelDustGeo = useMemo(() => {
    const count = 120;
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = roverPos.x + (Math.random() - 0.5) * 3;
      pos[i * 3 + 1] = -1;
      pos[i * 3 + 2] = roverPos.z + (Math.random() - 0.5) * 3;
    }
    return new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(pos, 3));
  }, []);

  useFrame(() => {
    if (!wheelDustRef.current) return;
    const dustArr = wheelDustRef.current.geometry.attributes.position.array as Float32Array;
    const { pos } = getRobotPosition(state.robot.missionProgress);
    const count = 120;
    for (let i = 0; i < count; i++) {
      dustArr[i * 3] += (Math.random() - 0.5) * 0.015;
      dustArr[i * 3 + 1] += 0.003 + Math.random() * 0.005;
      dustArr[i * 3 + 2] += (Math.random() - 0.5) * 0.015;
      dustArr[i * 3 + 1] *= 0.97;
      const tooHigh = dustArr[i * 3 + 1] > 0.4;
      const tooFar = Math.abs(dustArr[i * 3] - pos.x) > 1.5 || Math.abs(dustArr[i * 3 + 2] - pos.z) > 1.5;
      if (tooHigh || tooFar) {
        dustArr[i * 3] = pos.x + (Math.random() - 0.5) * 0.6;
        dustArr[i * 3 + 1] = terrainHeight(pos.x, pos.z) + 0.02;
        dustArr[i * 3 + 2] = pos.z + (Math.random() - 0.5) * 0.6;
        if (!wheelsMoving) {
          dustArr[i * 3 + 1] = -1;
        }
      }
    }
    wheelDustRef.current.geometry.attributes.position.needsUpdate = true;
  });

  const opacity = progress >= 100 ? 0 : wheelsMoving ? 0.35 : 0.08;

  return (
    <points ref={wheelDustRef} geometry={wheelDustGeo}>
      <pointsMaterial
        size={0.035}
        color="#CC8833"
        transparent
        opacity={opacity}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

function DustStorm({ active, state }: { active: boolean; state: SimulatorState }) {
  const pointsRef = useRef<THREE.Points>(null);
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(dustPositions, 3));
    return geo;
  }, []);

  useFrame(() => {
    if (pointsRef.current && active) {
      const pos = pointsRef.current.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < DUST_COUNT; i++) {
        pos[i * 3] += 0.02;
        pos[i * 3 + 1] += Math.sin(Date.now() * 0.001 + i) * 0.002;
        if (pos[i * 3] > 15) pos[i * 3] = -15;
      }
      pointsRef.current.geometry.attributes.position.needsUpdate = true;
    }
  });

  return (
    <>
      {active && (
        <points ref={pointsRef} geometry={geometry}>
          <pointsMaterial
            size={0.08}
            color="#CC8833"
            transparent
            opacity={0.4}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </points>
      )}
    </>
  );
}

function SceneLighting({ state }: { state: SimulatorState }) {
  const stormActive = state.world.weather === "Dust Storm";
  const lowBattery = state.robot.battery < 25;
  const criticalBattery = state.robot.battery < 10;
  const batteryFactor = criticalBattery ? 0.2 + Math.sin(Date.now() * 0.01) * 0.1 : lowBattery ? 0.6 : 1.0;
  const dimFactor = batteryFactor;
  const fogColor = criticalBattery ? "#220000" : stormActive ? "#885533" : "#C1440E";
  const fogNear = criticalBattery ? 8 : stormActive ? 5 : 25;
  const fogFar = criticalBattery ? 18 : stormActive ? 15 : 40;

  return (
    <>
      <ambientLight intensity={(stormActive ? 0.2 : 0.4) * dimFactor} color="#FF8844" />
      <directionalLight
        position={[10, 15, 5]}
        intensity={(stormActive ? 0.3 : 1.0) * dimFactor}
        color="#FFDDAA"
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <hemisphereLight
        args={["#FF8844", "#442200", (stormActive ? 0.2 : 0.4) * dimFactor]}
      />
      <fog
        attach="fog"
        args={[fogColor, fogNear, fogFar]}
      />
    </>
  );
}

function CameraController({ state, preset: currentPreset }: { state: SimulatorState; preset: CameraPreset }) {
  const { camera } = useThree();
  const targetRef = useRef(new THREE.Vector3());
  const shakeRef = useRef(0);
  const prevTickRef = useRef(state.tick);

  useEffect(() => {
    const events = state.eventHistory;
    if (events.length > 0) {
      const last = events[events.length - 1];
      if (last.tick !== prevTickRef.current && last.type === "warning") {
        shakeRef.current = 0.3;
      }
    }
    prevTickRef.current = state.tick;
  });

  useFrame(() => {
    const { pos } = getRobotPosition(state.robot.missionProgress);
    targetRef.current.copy(pos);
    const target = targetRef.current;
    const shake = shakeRef.current;

    if (currentPreset === "cinematic") {
      const angle = Date.now() * 0.0003;
      const dist = 4 + Math.sin(Date.now() * 0.0005) * 1;
      const camPos = new THREE.Vector3(
        target.x + Math.cos(angle) * dist,
        0.8 + Math.sin(Date.now() * 0.0004) * 0.2,
        target.z + Math.sin(angle) * dist,
      );
      camera.position.lerp(camPos, 0.02);
      camera.lookAt(target.x, target.y + 0.3, target.z);
    } else if (currentPreset === "topdown") {
      const camPos = new THREE.Vector3(target.x, 10, target.z);
      camera.position.lerp(camPos, 0.05);
      camera.lookAt(target.x, target.y, target.z);
    } else if (currentPreset === "thirdperson") {
      const behind = new THREE.Vector3(-2.5, 1.8, 0);
      const tangent = PATH_CURVE.getTangent(Math.max(0, Math.min(1, state.robot.missionProgress / 100)));
      const angle = Math.atan2(tangent.x, tangent.z);
      const rotated = behind.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), angle);
      const camPos = new THREE.Vector3(
        target.x + rotated.x,
        target.y + rotated.y,
        target.z + rotated.z,
      );
      camera.position.lerp(camPos, 0.04);
      camera.lookAt(target.x, target.y + 0.3, target.z);
    }

    if (shake > 0.01) {
      camera.position.x += (Math.random() - 0.5) * shake * 0.2;
      camera.position.y += (Math.random() - 0.5) * shake * 0.15;
      shakeRef.current *= 0.95;
    }
  });

  return null;
}

export function MarsScene({ state, cameraPreset = "free" }: { state: SimulatorState; cameraPreset?: CameraPreset }) {
  const lowBattery = state.robot.battery < 25;
  const criticalBattery = state.robot.battery < 10;
  const bgColor = criticalBattery
    ? `rgb(${10 + Math.sin(Date.now() * 0.02) * 5}, ${3 + Math.sin(Date.now() * 0.015) * 2}, 0)`
    : lowBattery ? "#0a0500" : "#1a0a00";
  return (
    <div className="w-full h-full">
      <Canvas
        shadows
        camera={{ position: [-5, 8, 10], fov: 45, near: 0.1, far: 50 }}
        gl={{ antialias: true, alpha: false }}
        style={{ background: bgColor }}
      >
        <SceneLighting state={state} />
        <Terrain />
        <TerrainShadow />
        <Rocks state={state} />
        <RockSlide state={state} />
        <PlannedPath />
        <ExecutedPath progress={state.robot.missionProgress} />
        <GhostPaths state={state} />
        <WheelTracks progress={state.robot.missionProgress} />
        <GoalMarker />
        <Rover state={state} />
        <WheelDust state={state} />
        <DustStorm active={state.world.weather === "Dust Storm"} state={state} />
        <CameraController state={state} preset={cameraPreset} />
        <OrbitControls
          enableDamping
          dampingFactor={0.1}
          minDistance={3}
          maxDistance={25}
          maxPolarAngle={Math.PI / 2.2}
          enabled={cameraPreset === "free"}
        />
      </Canvas>
    </div>
  );
}

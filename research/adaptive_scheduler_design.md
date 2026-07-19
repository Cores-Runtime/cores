# Adaptive Cognitive Scheduler — Research Design

**Document status:** Draft  
**Phase:** Research (post Phase 1 — Runtime Foundation)  
**Date:** 2026-07-15  
**Baseline comparator:** `OperatorSchedulingPolicy` (Priority Scheduler)

---

## 1. Research Question

> Given finite compute, memory, and battery; a changing mission state; and evolving environmental hazards — how should CORES allocate cognitive execution resources across modules each runtime cycle to maximize mission success while respecting safety and resource constraints?

This is not a question of static priority ordering. It is a **resource allocation problem under uncertainty and constraint**, solved deterministically at each runtime cycle using observable state.

---

## 2. Problem Statement

### 2.1 Context

CORES coordinates cognitive modules (planning, safety, mapping, diagnostics, etc.) on an autonomous robot. Each module consumes computational resources and may contribute to mission progress, safety, or system health. The robot operates under hard and soft limits:

- **Compute budget** — normalized CPU capacity per cycle (`RuntimeContext.compute_budget`)
- **Time budget** — maximum wall-clock duration per cycle (`RuntimeContext.time_budget_ms`)
- **Battery** — energy reserve affecting allowable workload (`RobotState.battery_level`)
- **Mission phase** — task relevance changes over time (`RobotState.mission_status`)
- **Environmental hazards** — safety-critical conditions (`RobotState.flags`, buffered `Event`s)

The Phase 1 **Priority Scheduler** (`OperatorSchedulingPolicy`) orders all registered modules by a fixed integer priority. It ignores resource budgets, mission phase, battery, and events. It schedules every module every cycle regardless of feasibility.

This is adequate for infrastructure validation but insufficient for research-grade adaptive scheduling.

### 2.2 Formal Problem

At runtime cycle \( t \), given a set of candidate modules \( \mathcal{M}_t = \{m_1, \ldots, m_n\} \), select a subset \( \mathcal{S}_t \subseteq \mathcal{M}_t \) and an execution order \( \pi_t \) such that:

1. **Safety invariants** are never violated (mandatory modules execute when required).
2. **Resource constraints** are satisfied (compute, time, and energy budgets are not exceeded).
3. **Mission utility** is maximized among all feasible schedules.

The Adaptive Cognitive Scheduler (ACS) is a scheduling research program implemented within the existing `SchedulingPolicy` abstraction. In Phase A, ACS is realized by `CriticalitySchedulingPolicy`, which composes a scoring strategy and a selection strategy to produce \( (\mathcal{S}_t, \pi_t) \) each cycle.

### 2.3 What ACS Is Not

- Not a replacement for ROS2, motion planning, or perception pipelines.
- Not a learning system in its initial formulation (weights are configurable constants, not trained parameters).
- Not non-deterministic — identical inputs must produce identical schedules (CORES Rule 5).
- Not a new runtime component — ACS is implemented as a `SchedulingPolicy` within the existing `Scheduler` abstraction.

---

## 3. Mathematical Formulation

### 3.1 Module Descriptor

Each module \( m_i \) is characterized by a descriptor vector (to be attached to the module interface in a future implementation phase):

\[
\mathbf{d}_i = (w_i^{S}, w_i^{M}, w_i^{U}, c_i^{cpu}, c_i^{mem}, c_i^{time}, c_i^{energy}, p_i^{fixed})
\]

| Symbol | Meaning |
|---|---|
| \( w_i^{S} \in [0, 1] \) | Static safety relevance |
| \( w_i^{M} \in [0, 1] \) | Static mission relevance |
| \( w_i^{U} \in [0, 1] \) | Base urgency weight |
| \( c_i^{cpu} \in [0, 1] \) | Normalized compute cost per execution |
| \( c_i^{mem} \in [0, 1] \) | Normalized memory footprint |
| \( c_i^{time} \in \mathbb{R}^+ \) | Expected execution time (ms) |
| \( c_i^{energy} \in [0, 1] \) | Normalized energy cost per execution |
| \( p_i^{fixed} \in \mathbb{Z} \) | Legacy fixed priority (baseline compatibility) |

### 3.2 Runtime State Vector

At cycle \( t \), define the observable state:

\[
\mathbf{x}_t = (\mathbf{r}_t, \mathbf{c}_t, \mathbf{e}_t)
\]

where:

- \( \mathbf{r}_t \) — `RobotState` fields: battery \( b_t \), mission status \( \mu_t \), flags \( \mathbf{f}_t \), sensor summaries
- \( \mathbf{c}_t \) — `RuntimeContext` fields: compute budget \( C_t \), time budget \( T_t \), scheduler mode, emergency flag
- \( \mathbf{e}_t = (e_1, \ldots, e_k) \) — buffered events since cycle \( t-1 \)

### 3.3 Dynamic Factor Functions

Define normalized dynamic multipliers in \( [0, 1] \):

**Safety factor** — elevated when hazards or emergency events are present:

\[
\phi_i^{S}(\mathbf{x}_t) = \mathrm{clip}\Big(w_i^{S} + \sum_{e \in \mathbf{e}_t} \delta_S(e, m_i) + \sum_{f \in \mathbf{f}_t} \delta_f(f, m_i),\ 0,\ 1\Big)
\]

**Mission factor** — elevated when module is relevant to current mission phase:

\[
\phi_i^{M}(\mathbf{x}_t) = \mathrm{clip}\big(w_i^{M} \cdot \rho(\mu_t, m_i),\ 0,\ 1\big)
\]

where \( \rho(\mu_t, m_i) \in \{0, 0.5, 1.0\} \) is a deterministic mission–module relevance lookup table.

**Urgency factor** — elevated by time-sensitive events and deadlines:

\[
\phi_i^{U}(\mathbf{x}_t) = \mathrm{clip}\Big(w_i^{U} + \sum_{e \in \mathbf{e}_t} \delta_U(e, m_i),\ 0,\ 1\Big)
\]

**Resource penalty** — cost relative to available budgets:

\[
\psi_i(\mathbf{x}_t) = \alpha_{cpu} \frac{c_i^{cpu}}{C_t} + \alpha_{time} \frac{c_i^{time}}{T_t} + \alpha_{energy} \frac{c_i^{energy}}{b_t + \epsilon}
\]

where \( \alpha_{cpu} + \alpha_{time} + \alpha_{energy} = 1 \) and \( \epsilon \) prevents division by zero.

### 3.4 Criticality Score

The **criticality score** of module \( m_i \) at cycle \( t \):

\[
K_i(\mathbf{x}_t) = w_S \cdot \phi_i^{S}(\mathbf{x}_t) + w_M \cdot \phi_i^{M}(\mathbf{x}_t) + w_U \cdot \phi_i^{U}(\mathbf{x}_t) - w_R \cdot \psi_i(\mathbf{x}_t)
\]

The weights \( w_S, w_M, w_U, w_R \) are explicit policy parameters. Phase A uses hand-tuned defaults and treats calibration as future research.

**Initial hand-tuned defaults** (subject to calibration via benchmarks):

| Coefficient | Value | Rationale |
|---|---|---|
| \( w_S \) | 0.35 | Safety dominates — violations are irreversible |
| \( w_M \) | 0.30 | Mission progress is primary objective |
| \( w_U \) | 0.20 | Responsiveness to time-sensitive conditions |
| \( w_R \) | 0.15 | Penalize expensive modules under constraint |

Constraint: \( w_S + w_M + w_U + w_R = 1.0 \).

Weight selection is intentionally treated as an open research question. Candidate calibration methods include expert tuning, sensitivity analysis, Bayesian optimization, and reinforcement learning. The runtime implementation therefore exposes these values as configuration rather than embedding them as architectural constants.

Modules with \( K_i(\mathbf{x}_t) \leq 0 \) are candidates for deferral unless marked mandatory (see §5.3).

### 3.5 Scheduling as Constrained Selection

**Phase A — Criticality Scheduler (first implementation target):**

1. Compute \( K_i(\mathbf{x}_t) \) for all \( m_i \in \mathcal{M}_t \).
2. Sort modules by \( K_i \) descending; break ties by registration order (stable sort).
3. Greedily include modules in sorted order while constraints (§5) remain satisfied.
4. Output the feasible ordered subset as `ExecutionPlan`.

**Phase B — Risk-Aware Criticality Knapsack (future):**

Formulate module selection as a 0–1 knapsack variant:

\[
\max_{\mathbf{z} \in \{0,1\}^n} \sum_{i=1}^{n} K_i(\mathbf{x}_t) \cdot z_i
\]

subject to:

\[
\sum_{i=1}^{n} c_i^{cpu} \cdot z_i \leq C_t, \quad
\sum_{i=1}^{n} c_i^{time} \cdot z_i \leq T_t, \quad
\sum_{i=1}^{n} c_i^{energy} \cdot z_i \leq E_t
\]

\[
z_i = 1 \quad \forall m_i \in \mathcal{M}^{mandatory}(\mathbf{x}_t)
\]

where \( E_t = g(b_t) \) maps battery level to an energy budget. Solve via deterministic dynamic programming or branch-and-bound. Order selected modules by \( K_i \) descending.

---

## 4. Scheduler Inputs

ACS consumes exactly the inputs defined by the existing `SchedulingPolicy` interface. No new runtime infrastructure is required.

| Input | Source | Fields Used |
|---|---|---|
| Module pool | `Runtime.modules` | Descriptors \( \mathbf{d}_i \), registration order |
| Robot state | `RobotState` | `battery_level`, `mission_status`, `flags`, `sensor_summaries` |
| Runtime context | `RuntimeContext` | `compute_budget`, `time_budget_ms`, `scheduler_mode`, `is_emergency`, `cycle_count` |
| Event buffer | Harvested `Event` list | `event_type`, `priority`, `source`, `payload` |

### 4.1 Event-to-Factor Mapping (Deterministic)

| Event Type | Effect |
|---|---|
| `SYSTEM_EMERGENCY` | Set \( \phi_i^{S} = 1.0 \) for safety/diagnostic modules; force emergency mode |
| `MODULE_FAILED` | Boost diagnostic module urgency |
| `STATE_UPDATED` | Re-evaluate mission relevance |
| `DIAGNOSTIC` | Informational; no direct score change unless payload specifies hazard |

| RobotState Flag | Effect |
|---|---|
| `obstacle_detected = True` | Boost safety and collision-avoidance modules |
| `hardware_fault = True` | Boost diagnostic modules; suppress non-essential modules |

| Mission Status | Effect |
|---|---|
| `idle` | Suppress navigation/exploration modules (\( \rho = 0 \)) |
| `active` | Enable mission modules (\( \rho = 1.0 \)) |
| `docking` | Enable precision navigation modules only |

---

## 5. Scheduler Outputs

ACS produces the same outputs as all `SchedulingPolicy` implementations:

| Output | Type | Description |
|---|---|---|
| `ExecutionPlan` | Ordered `List[Module]` | Feasible subset of modules to execute this cycle |
| Updated `RuntimeContext` | In-place mutation | `scheduler_mode`, `is_emergency`, scheduling metadata in `metrics` |

The policy/algorithm split is explicit:

```text
SchedulingPolicy
  -> CriticalityScoringStrategy
  -> ModuleSelectionStrategy
```

This keeps the policy boundary stable while allowing future scoring or selection algorithms to change independently.

### 5.1 Output Metadata (Observability)

Each scheduling decision should record in `RuntimeContext.metrics`:

```text
{
  "policy": "adaptive_criticality",
  "cycle": t,
  "scores": {"module_name": K_i, ...},
  "selected": ["module_a", "module_b"],
  "deferred": ["module_c"],
  "mode": "default | low_power | emergency",
  "constraints_active": ["time", "battery"],
  "decision_time_ms": float
}
```

This supports benchmark analysis without altering runtime architecture.

### 5.2 Resource Constraints

Three hard constraints govern module selection:

| Constraint | Symbol | Source | Violation Handling |
|---|---|---|---|
| Compute | \( \sum c_i^{cpu} \cdot z_i \leq C_t \) | `RuntimeContext.compute_budget` | Defer lowest-\( K_i \) non-mandatory modules |
| Time | \( \sum c_i^{time} \cdot z_i \leq T_t \) | `RuntimeContext.time_budget_ms` | Defer lowest-\( K_i \) non-mandatory modules |
| Energy | \( \sum c_i^{energy} \cdot z_i \leq E_t \) | Derived from `RobotState.battery_level` | Defer highest-energy non-mandatory modules |

**Energy budget mapping:**

\[
E_t = \begin{cases}
0.2 & b_t < 0.10 \quad \text{(critical)} \\
0.5 & 0.10 \leq b_t < 0.30 \quad \text{(low power)} \\
1.0 & b_t \geq 0.30 \quad \text{(normal)}
\end{cases}
\]

### 5.3 Mandatory Module Set

Define \( \mathcal{M}^{mandatory}(\mathbf{x}_t) \subseteq \mathcal{M}_t \) — modules that must execute regardless of score:

\[
\mathcal{M}^{mandatory}(\mathbf{x}_t) = \{ m_i \mid \phi_i^{S}(\mathbf{x}_t) = 1.0 \} \cup \{ m_i \mid \text{is\_emergency} \land m_i \in \text{Diagnostics} \}
\]

If mandatory modules alone exceed a budget, execute mandatory modules in safety-priority order and log a constraint violation event. Safety must never be silently dropped.

---

## 6. Criticality Score Definition

The criticality score \( K_i(\mathbf{x}_t) \) is the central research artifact. It answers: *"How important is it to run module \( m_i \) right now, given everything the runtime knows?"*

### 6.1 Component Semantics

| Component | Symbol | Meaning | High When |
|---|---|---|---|
| Safety Importance | \( \phi_i^{S} \) | Potential to prevent or mitigate harm | Obstacle detected, emergency event, hardware fault |
| Mission Importance | \( \phi_i^{M} \) | Contribution to current mission objective | Module matches active mission phase |
| Time Urgency | \( \phi_i^{U} \) | Time-sensitivity of execution | Deadlines approaching, stale state, event-triggered |
| Resource Cost | \( \psi_i \) | Relative expense of execution | High CPU/time/energy cost under tight budgets |

### 6.2 Relationship to Priority Scheduler

The baseline Priority Scheduler uses only \( p_i^{fixed} \):

\[
K_i^{baseline} = p_i^{fixed}
\]

ACS generalizes this: \( p_i^{fixed} \) becomes one input to the descriptor, but dynamic factors can override static ordering when runtime conditions change. This enables direct comparison — same modules, same runtime, different policy.

### 6.3 Score Properties (Required)

1. **Deterministic** — \( K_i(\mathbf{x}_t) \) is a pure function of observable inputs.
2. **Bounded** — \( K_i \in [-1, 1] \) after normalization (clip final score).
3. **Monotonic in safety** — increasing hazard level never decreases \( \phi_i^{S} \) for safety modules.
4. **Explainable** — every score decomposes into named components for logging and debugging.

---

## 7. Baseline Comparison

### 7.1 Baselines

| Policy | Class | Behavior | Role |
|---|---|---|---|
| **Default** | `DefaultSchedulingPolicy` | All modules, registration order | Sanity check |
| **Priority** | `OperatorSchedulingPolicy` | All modules, fixed priority order | Primary baseline |
| **Criticality** | `CriticalitySchedulingPolicy` (proposed) | Scored subset, greedy constraint satisfaction | ACS Phase A |
| **Knapsack** | `KnapsackSchedulingPolicy` (proposed) | Optimal subset under budget | ACS Phase B |

### 7.2 Comparison Protocol

For each benchmark scenario (§8), run identical module sets through all policies using the same `RobotState`, `RuntimeContext`, and event buffer. Record:

- Selected modules and order
- Deferred modules
- Constraint violations
- Decision latency
- Mission outcome (scenario-specific)

**Hypothesis:** ACS Phase A will match Priority Scheduler under nominal conditions (Scenario A) but outperform it under resource pressure (Scenarios B, C) by deferring low-value modules while preserving safety.

**Null hypothesis:** ACS provides no measurable improvement in mission utility or resource efficiency over Priority Scheduler at equivalent decision latency.

---

## 8. Benchmark Scenarios

All scenarios use simulated `RobotState` via `SimulatedStateEstimator`. No hardware or ROS2.

### Scenario A — Nominal Exploration

| Parameter | Value |
|---|---|
| Battery | 100% (1.0) |
| Obstacle | False |
| Mission | `active` (explore) |
| Compute budget | 1.0 |
| Time budget | 100 ms |
| Events | None |

**Expected ACS behavior:** Schedule exploration-relevant modules (Explorer, Mapper, Logger). All modules fit within budget.

**Expected Priority behavior:** All modules scheduled by fixed priority.

**Pass criterion:** ACS selects same or superset of mission modules; no safety modules deferred.

---

### Scenario B — Low Battery

| Parameter | Value |
|---|---|
| Battery | 5% (0.05) |
| Obstacle | False |
| Mission | `active` |
| Compute budget | 1.0 |
| Time budget | 100 ms |
| Events | None |

**Expected ACS behavior:** Schedule BatteryMonitor, Safety, Navigation. **Defer** Explorer and other high-energy modules.

**Expected Priority behavior:** All modules scheduled regardless of battery — including Explorer.

**Pass criterion:** ACS defers ≥ 1 non-mandatory high-energy module; all mandatory safety modules retained.

---

### Scenario C — Obstacle Detected

| Parameter | Value |
|---|---|
| Battery | 80% (0.8) |
| Obstacle | True |
| Mission | `active` |
| Compute budget | 1.0 |
| Time budget | 100 ms |
| Events | `DIAGNOSTIC` from proximity sensor |

**Expected ACS behavior:** Safety and CollisionAvoidance modules first. Exploration modules deferred or deprioritized.

**Expected Priority behavior:** Safety runs first (if highest fixed priority) but all modules still execute.

**Pass criterion:** ACS ranks safety modules above exploration modules; collision-avoidance module in selected set.

---

### Scenario D — Emergency Event

| Parameter | Value |
|---|---|
| Battery | 50% |
| Obstacle | False |
| Mission | `active` |
| Events | `SYSTEM_EMERGENCY` |
| `is_emergency` | True |

**Expected ACS behavior:** Emergency mode. Only diagnostic, recovery, and safety modules scheduled.

**Pass criterion:** Zero non-essential modules in execution plan.

---

### Scenario E — Budget Exhaustion

| Parameter | Value |
|---|---|
| Battery | 60% |
| Compute budget | 0.3 |
| Time budget | 20 ms |
| Modules | 10 modules with varying costs |

**Expected ACS behavior:** Select highest-criticality feasible subset; defer remainder.

**Pass criterion:** Total resource cost of selected modules ≤ budget; highest-scoring modules included.

---

### Scenario F — Determinism Verification

Run Scenarios A–E twice with identical inputs.

**Pass criterion:** Bit-identical `ExecutionPlan` and `RuntimeContext.metrics` across runs.

---

### Scenario G â€” Sensor Failure

| Parameter | Value |
|---|---|
| Battery | 60% |
| Mission | `explore` |
| Sensor summaries | GPS offline, camera degraded |
| Flags | `sensor_failure = True`, `hardware_fault = True` |
| Events | `MODULE_FAILED` from localization stack |
| Compute budget | 0.6 |
| Time budget | 40 ms |

**Expected ACS behavior:** Increase diagnostic and localization criticality, defer at least one non-essential mapping/exploration module, and preserve safety coverage.

**Expected Priority behavior:** Continue executing by fixed priority without explicit sensor-degradation adaptation.

**Pass criterion:** `diagnostics` and `localization` are selected; at least one high-cost exploration or mapping module is deferred.

---

## 9. Evaluation Metrics

### 9.1 Primary Metrics (Scheduler Quality)

| Metric | Symbol | Definition | Target |
|---|---|---|---|
| Mission Utility | \( U \) | \( \sum_{m_i \in \mathcal{S}_t \cap \mathcal{M}_{mission}} w_i^M \; / \; \sum_{m_i \in \mathcal{M}_{mission}} w_i^M \) | Higher is better |
| Safety Coverage | \( S \) | Fraction of mandatory safety modules executed | 1.0 always |
| Resource Efficiency | \( R \) | Useful compute delivered / total budget consumed | Higher is better |
| Deferral Accuracy | \( D \) | Fraction of correctly deferred low-value modules (scenario-defined) | Higher is better |
| Decision Latency | \( L \) | Time to produce `ExecutionPlan` (ms) | < 1 ms (Phase A target) |

### 9.2 Secondary Metrics

| Metric | Definition |
|---|---|
| Scheduling overhead ratio | Decision latency / runtime cycle latency |
| Constraint violation rate | Fraction of cycles where mandatory modules exceed budget |
| Module starvation count | Consecutive cycles a module is deferred |
| Score entropy | Distribution spread of \( K_i \) values (diagnostic) |
| Policy divergence | Module selection difference vs Priority baseline |

### 9.3 Regression Metrics (from Phase 1 benchmarks)

Existing microbenchmarks (`benchmarks/run_benchmarks.py`) must not regress:

| Component | Phase 1 Baseline (mean) |
|---|---|
| EventBus | ~0.0007 ms |
| Scheduler (Priority) | ~0.006 ms |
| ExecutionLayer | ~0.034 ms |
| Runtime Cycle | ~0.070 ms |

ACS decision latency should remain within 10× of Priority Scheduler latency for \( n \leq 20 \) modules.

---

## 10. Computational Complexity

### 10.1 Criticality Scheduler (Phase A)

| Step | Complexity |
|---|---|
| Score computation | \( O(n) \) |
| Stable sort by score | \( O(n \log n) \) |
| Greedy constraint check | \( O(n) \) |
| **Total per cycle** | \( O(n \log n) \) |

Memory: \( O(n) \) for score array and selected set.

For \( n \leq 20 \) modules, this is negligible relative to module execution time.

### 10.2 Knapsack Scheduler (Phase B)

| Variant | Complexity |
|---|---|
| 0–1 Knapsack (single budget) | \( O(n \cdot B) \) where \( B \) is discretized budget |
| Multi-constraint knapsack | NP-hard; pseudo-polynomial via DP |
| Proposed approach | DP with discretized \( C_t \) into 100 units |

For \( n \leq 20, B = 100 \): 2,000 DP cells per cycle — acceptable for research validation.

### 10.3 Scalability Limit

| Module Count | Recommended Policy |
|---|---|
| \( n \leq 20 \) | Criticality or Knapsack |
| \( 20 < n \leq 50 \) | Criticality (greedy) only |
| \( n > 50 \) | Requires approximation algorithms (future research) |

---

## 11. Future Algorithm Roadmap

Following the incremental research path defined in project guidance:

```
Phase 1 (Complete)
  └── Priority Scheduler (OperatorSchedulingPolicy)
        │
Step 1 (Research — this document)
  └── Formalize criticality model and benchmarks
        │
Step 2 (Implementation)
  └── CriticalitySchedulingPolicy
        │   • Compute K_i scores
        │   • Greedy constraint satisfaction
        │   • Benchmark vs Priority
        │
Step 3 (Implementation)
  └── KnapsackSchedulingPolicy
        │   • Risk-Aware Criticality Knapsack (Operator module algorithm)
        │   • Optimal subset selection under multi-constraint budget
        │   • Benchmark vs Criticality and Priority
        │
Step 4 (Research)
  └── Mode Selection Layer
        │   • default / low_power / emergency mode transitions
        │   • Event-driven mode switching (SCHEDULER_DESIGN.md §6)
        │
Step 5 (Research)
  └── Adaptive Weight Calibration
        │   • Sensitivity analysis on weight coefficients
        │   • Scenario-specific weight profiles
        │
Step 6 (Future)
  └── Operator Cognitive Module
        • Full Risk-Aware Criticality Knapsack Optimization
        • Integration as a Module (not SchedulingPolicy)
        • Module proposes schedule; Scheduler validates constraints
```

Each step requires benchmarks before proceeding to the next. No step introduces new runtime infrastructure — only new `SchedulingPolicy` implementations and module descriptors.

---

## 12. Success Criteria

The Adaptive Cognitive Scheduler research program succeeds when:

1. **Formalization complete** — criticality score, constraints, and selection algorithm are fully specified (this document).
2. **Baseline established** — Priority Scheduler benchmark results recorded for Scenarios A–G.
3. **Phase A validated** — Criticality Scheduler outperforms Priority on \( U \), \( R \), or \( D \) in ≥ 2 of 6 conditional scenarios (B–G) without violating \( S = 1.0 \).
4. **Latency acceptable** — ACS decision latency < 1 ms for \( n = 20 \) modules.
5. **Determinism preserved** — Scenario F passes for all policies.
6. **Phase B justified** — Knapsack implementation proceeds only if Phase A greedy selection shows suboptimal resource utilization in Scenario E.

---

## 13. Assumptions and Limitations

| Assumption | Risk | Mitigation |
|---|---|---|
| Module costs \( c_i \) are known a priori | Estimation error | Use conservative (upper-bound) costs; update from `ModuleResult.metrics` |
| Mission–module relevance table is static | New missions require manual mapping | Document table; extend in Phase 3 with cognitive modules |
| Battery-to-energy mapping is linear | Non-linear discharge curves | Refine with hardware data in Phase 4 |
| Weight coefficients are global | Suboptimal per-scenario | Step 5 introduces scenario profiles |
| All modules are independent | Hidden dependencies | Future: dependency graph constraint |

---

## 14. References

| Document | Relevance |
|---|---|
 Policy abstraction constraint |
| `src/cores/core/scheduler.py` | Existing `OperatorSchedulingPolicy` baseline |

---

## 15. Guiding Principle

> The scheduler exists to answer one question each cycle: **given what the robot knows and what it can afford, which cognitive work matters most right now?**

Every formula, constraint, and benchmark scenario in this document serves that question. Implementation begins only after this design is reviewed and approved.

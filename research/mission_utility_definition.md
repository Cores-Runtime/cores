# Mission Utility Definition

## Motivation

Mission utility in robotics is not binary.

Two runs can both "complete" a mission while leaving the robot in very different states:

- one run may finish with almost no battery remaining
- another may finish with substantial reserve

Those outcomes are not equally desirable for an autonomous system that must continue operating after the current task.

Mission utility therefore needs to reflect more than completion alone.

## Definition

For Phase 2A.6, mission utility is defined as a multi-objective evaluation score with five normalized components:

\[
U = \langle C, S, E, T, R \rangle
\]

Where:

- \(C\) = mission completion
- \(S\) = safety coverage
- \(E\) = energy headroom
- \(T\) = time headroom
- \(R\) = resource preservation

Each component is normalized to the range \([0, 1]\).

### Component Definitions

#### Mission Completion \(C\)

Fraction of mission-relevant workload that is selected by the scheduler.

This is a weighted completion ratio, not a binary completed/not-completed flag.

#### Safety Coverage \(S\)

Fraction of required safety modules present in the execution plan.

Safety remains a first-class objective because a mission that completes unsafely is not a success.

#### Energy Headroom \(E\)

Normalized remaining energy after the scheduled workload is accounted for.

This captures whether the chosen schedule leaves the robot with practical operating reserve.

#### Time Headroom \(T\)

Normalized remaining time budget after the scheduled workload is accounted for.

This measures whether the plan is feasible within the cycle budget.

#### Resource Preservation \(R\)

Aggregate preservation of compute, energy, and time budgets.

This term rewards schedules that remain balanced across resource dimensions rather than only optimizing one axis.

## Scalar Evaluation Score

For benchmark comparison, the vector utility is scalarized as:

\[
U^* = w_C C + w_S S + w_E E + w_T T + w_R R
\]

with default evaluation weights:

- \(w_C = 0.35\)
- \(w_S = 0.20\)
- \(w_E = 0.15\)
- \(w_T = 0.15\)
- \(w_R = 0.15\)

These weights are evaluation parameters, not runtime policy parameters.

They are fixed across all benchmark policies to preserve comparability.

## Weight Justification

The default weight vector is chosen to reflect the priorities of an autonomous robot that must keep operating after the current task:

- completion matters because the robot still needs to achieve the mission objective
- safety matters because an unsafe completion is not a valid success
- energy matters because depleted batteries reduce operational continuity
- time matters because overrunning the cycle budget breaks schedulability
- resource preservation matters because the scheduler should not solve one constraint by collapsing the others

The weights are intentionally not equal.

Completion and safety together receive the largest share because they govern whether the robot actually accomplishes a safe mission. Energy, time, and preservation remain separate because they expose different failure modes that should not be collapsed too early.

These values are a defensible starting point for evaluation, not a final universal optimum. Sensitivity analysis should still be used to test whether the conclusions depend strongly on the chosen vector.

## Why This Is Appropriate

This definition matches the robotics setting better than a binary completion score because it reflects the actual constraints of autonomous operation:

- a completed mission with no remaining energy is fragile
- a completed mission that exceeded timing budgets is operationally questionable
- safety cannot be reduced to task completion
- resource preservation affects what the robot can do next

The metric is therefore closer to "quality of successful execution" than to simple goal attainment.

## Trade-Offs

The metric is intentionally not a pure completion score.

That has consequences:

- a policy that always executes everything may score well on completion but poorly on feasibility
- a policy that is overly conservative may preserve resources but underdeliver on mission completion
- the scalar score hides trade-offs that are visible only in the component breakdown

For that reason, benchmark reports should publish both:

- the scalar score \(U^*\)
- the component vector \(\langle C, S, E, T, R \rangle\)

## Research Use

This definition is intended for evaluation only.

It does not change the scheduler implementation.

The scheduler remains frozen while the benchmark framework is rerun under this revised objective.

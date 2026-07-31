# Phase 4H: Learning Subsystem -- Research and Strategy Comparison

## What Learning Is and Is Not

Learning is not Memory.

Memory stores discrete experiences: observations, actions, outcomes.

Learning extracts patterns from those experiences.

Memory answers: "What happened?"

Learning answers: "What tends to happen when we do X?"

## Approaches Studied

### Success Rate Tracking

Maintain running success/failure statistics per action, plan, or context.

Strengths: Simple, explainable, O(1) update, confidence intervals via Beta distribution.

Weaknesses: Treats all trials equally unless weighted. Cannot detect complex failure modes.

Good for: "Should I try OpenDoor again?" Based on the last 50 attempts, it works 18% of the time.

### Failure Pattern Recognition

Identify conditions that correlate with failure.

Strengths: Finds root causes ("door jams when humidity > 80%"), not just symptoms.

Weaknesses: Requires structured context data. Heuristic pattern extraction can produce false positives.

Good for: "Why does OpenDoor keep failing?" Because every failure happened in Room 12 with a closed door.

### Reward / Utility Learning

Assign scalar utility to actions based on observed outcomes, energy cost, and time cost.

Strengths: Produces a single comparable score per action. Natural input to utility-based planners.

Weaknesses: Requires a reward function. Different missions need different reward functions.

Good for: "Which route should I take?" The utility of Corridor B is 0.85, Corridor A is 0.42.

### Confidence Estimation

Estimate how reliable an action or module is based on past performance and trend.

Strengths: Planners can use confidence to modulate risk. "If I'm unsure, take a safer path."

Weaknesses: Confidence without well-calibrated uncertainty is misleading.

Good for: "Should I trust the GPS?" It has been failing 40% of the time.

### Policy Learning

Recommend which planner strategy or module configuration to prefer given current conditions.

Strengths: High-level adaptation. Can switch between planners per mission phase.

Weaknesses: Requires performance data across policies. Cold-start problem.

Good for: "Should I use GoalPlanner or ReactivePlanner?" ReactivePlanner has been winning for obstacle avoidance missions.

### Reinforcement Learning (distant future)

Full RL with policy gradients, Q-learning, or PPO.

Strengths: Can discover optimal policies from reward alone.

Weaknesses: Sample-inefficient, non-deterministic, hard to debug. Overkill for Phase 4H.

Good for: Complex continuous control tasks. Not needed yet.

## Recommended Architecture

```
Memory → Learning → Planning
```

Learning queries Memory for structured experiences (outcomes, observations), updates internal models, and publishes a `LearningSnapshot` to `RuntimeContext.learning`.

Planners (specifically UtilityPlanner) read `context.learning` to adjust action utilities.

## Default Strategy

SuccessRateLearner.

It is the foundation everything else builds on:

- RewardLearner needs success statistics
- ConfidenceLearner needs success statistics + trend
- PolicyLearner needs planner performance stats
- FailurePatternLearner needs failure records + context

Each strategy implements the same `LearningStrategy` ABC and can be swapped independently.

## Update Frequency

Learning should NOT run every cycle. Three policies:

- `interval`: run every N cycles (default: 10)
- `count`: run when N new experiences accumulated (default: 25)
- `manual`: only when explicitly triggered

This avoids recomputing the same statistics when no new data exists.

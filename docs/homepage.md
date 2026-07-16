# CORES Homepage

A static documentation and demo site for the CORES robotics runtime, built with Next.js 14, Tailwind CSS, and Framer Motion.

## Location

`cores/homepage/`

## Stack

- **Next.js 14** (App Router) — static generation
- **Tailwind CSS** — custom design tokens (`ink`, `paper`, `accent`, `muted`, `card`, `border`, `code`)
- **Framer Motion** — scroll-triggered section animations
- All charts render as **inline SVG** (no charting library)

## Sections

| Section | File | Content |
|---|---|---|
| Hero | `components/Hero.tsx` | Title, tagline, key metrics, module status badges |
| Core Modules | `components/ModulesSection.tsx` | 4 composable scheduler modules |
| Policies | `components/Policies.tsx` | Priority, Criticality, Knapsack, Lexicographic explainers |
| Scenarios | `components/ScenarioList.tsx` | 20 benchmark test cases |
| Visualizations | `components/Visualizations.tsx` | Bar, radar, heatmap, Pareto, and dependency graph charts |
| Footer | `components/Footer.tsx` | Navigation, artifact links |

## Charts

All chart components live in `components/charts/`:

| Component | What it shows |
|---|---|
| `BarChart.tsx` | Grouped bars — one policy per group, all 20 scenarios |
| `RadarChart.tsx` | Multi-axis polygon for 5 metrics across 4 policies |
| `HeatmapChart.tsx` | Policy x scenario matrix with color scale (4 metrics available) |
| `ParetoChart.tsx` | Safety vs Mission Utility scatter with frontier line |
| `DependencyGraph.tsx` | Module dependency topology with edge type styles |

## Data

Benchmark data is hardcoded in `lib/benchmark-data.ts`. It represents 4 scheduling policies evaluated across 20 scenarios on 4 metrics (mission utility, safety coverage, energy headroom, decision time).

## Commands

```bash
cd cores/homepage
npm run dev      # development server
npm run build    # static production build
npm run start    # serve production build
```

## Style Notes

- No em dashes anywhere in the UI.
- No gradients, no AI-generated filler text.
- Custom Tailwind color palette defined in `tailwind.config.ts`.
- All animations use `framer-motion` `whileInView` triggers.

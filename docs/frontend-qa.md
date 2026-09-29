# Dashboard Shell Visual QA

## Layout

- Top bar includes plant selector, search, notifications, and user menu.
- Left navigation includes Dashboard, Plant Map, Incidents, Timeline, Reports, AI Assistant, and Settings.
- Main area contains risk score, active alerts, charts, heatmap preview, and timeline preview.
- Right panel contains recommendations, recent events, and emergency actions.
- Desktop and tablet widths preserve readable density without overlapping controls.

## Design Tokens

- Background uses the dark industrial theme.
- Semantic colors are restricted to safe green, warning amber, critical red, and informational blue.
- Typography uses Inter with IBM Plex Sans fallback.
- Cards use restrained 8px-or-less radii and no decorative gradients or glass effects.

## Components

- Risk score is large, color-coded, and includes a visible trend indicator.
- Alert list highlights new/active alerts with motion only on state change.
- ECharts are used for telemetry trend and severity distribution, not decoration.
- Heatmap preview communicates spatial concentration of risk.
- Emergency actions are visibly disabled for read-only roles.

## Accessibility

- Critical and warning text remains high contrast against the dark background.
- Interactive controls have visible borders and focus rings through shared button/input styling.
- Icon-only signals are paired with text labels.

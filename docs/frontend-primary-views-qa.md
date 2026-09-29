# Frontend Primary Views QA

## Plant Map

- Leaflet map initializes without external tile dependencies and supports zoom/pan.
- Layer toggles independently show/hide sensors, workers, equipment, permits, hazards, alerts, and heatmap.
- Alert markers link to `/api/v1/timeline/alerts/{id}` and are positioned from evidence coordinates.
- Viewer and Compliance Officer roles cannot edit layout metadata or upload layout.
- Supervisor role is scoped to assigned area.

## Incident Timeline

- Timeline entries are sorted chronologically.
- Each event has a clickable evidence link.
- Sequence reads as a causal story: gas trend, maintenance, worker presence, compound alert, notification.
- Supervisor role only sees assigned-area timeline content.

## Incident History

- Filters cover date, area, equipment, severity, and search text.
- Records include Past Incidents, Near Misses, Alerts, Sensor Data, Reports, and Corrective Actions.
- Viewer role remains read-only.
- Supervisor role is area-scoped.

## AI Assistant

- User can choose question, procedure, regulation, incident explanation, or recommendation mode.
- Grounded answers show visible document/section citations inline.
- No-source responses render with a distinct warning state and no citations.
- Read-only roles cannot submit new questions.

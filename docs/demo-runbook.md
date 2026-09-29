# SentinelAI Live Demo Runbook

## Objective

Run the Section 15 unattended demo flow from normal operation to report export without manual data manipulation.

## Start The Stack

1. Copy `.env.example` to `.env`.
2. Start services:

```bash
make up
make migrate
make seed
```

3. Start the replay controller:

```bash
curl -k -X POST https://localhost/api/demo/replay/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"accelerated","speed_multiplier":600}'
```

4. Open the frontend at `https://localhost` or `http://localhost:3000` depending on how the frontend is being served.

Demo login:

- Email: `demo.admin@sentinelai.local`
- Password: `DemoPass123!`

## Scripted Demo Talk Track

### 1. Login And Normal Dashboard

Advance target: step 1.

What to show: Dashboard `Current Plant Risk` is Low.

What to say: "SentinelAI starts as an intelligence layer over existing plant systems. At this point no single source is alarming, and the plant is in normal low-risk operation."

### 2. Gas Slowly Increases

Advance:

```bash
curl -k -X POST https://localhost/api/demo/replay/advance \
  -H "Content-Type: application/json" \
  -d '{"step":2}'
```

What to show: Replay status says `Gas slowly increasing`.

What to say: "The gas signal begins moving upward, but it is still not a naive threshold alarm."

### 3. Maintenance Begins

Advance to step 3.

What to say: "A maintenance activity begins in the same zone. Still, maintenance alone is not an emergency."

### 4. Workers Enter The Area

Advance to step 4.

What to say: "Workers enter the affected zone. Each individual signal remains plausible, but the combination is becoming unsafe."

### 5. Compound High-Risk Alert

Advance to step 5.

What to show: Dashboard now shows High risk and `High compound gas risk`.

What to say: "This is SentinelAI's core differentiator: gas increasing plus maintenance active plus workers nearby raises the alert before a naive gas threshold would."

### 6. Heatmap

Advance to step 6, then open Plant Map.

What to show: Alert marker and heatmap concentration in Zone A.

What to say: "The map is not a static overlay. It computes spatial risk from alert evidence and places the marker at the triggering evidence location."

### 7. Timeline

Advance to step 7, then open Timeline.

What to show: Gas readings, maintenance start, worker presence, compound alert, and notification in chronological order.

What to say: "This timeline is generated from stored evidence links, not a hand-written incident narrative."

### 8. AI Assistant

Advance to step 8, open AI Assistant, ask:

`What should we do when gas rises during maintenance with workers nearby?`

What to show: Grounded response with `Demo Gas Maintenance Controls` citation.

What to say: "The assistant refuses ungrounded answers. Here it cites the indexed safety guidance used for the recommendation."

### 9. Emergency Response Panel

Advance to step 9, open Emergency.

What to show: affected area, workers present, nearby equipment, nearest exit, contacts, and role-specific actions.

What to say: "During an incident, SentinelAI removes ambiguity: who is affected, where to exit, whom to contact, and what each role should do."

### 10. Incident History And Export

Advance to step 10, open Incidents and Emergency export buttons.

What to show: incident history includes Gas + Maintenance + Workers; PDF/CSV report export works.

What to say: "The export is generated from the same evidence chain shown on screen, so audit output cannot drift from operational truth."

## Headless E2E Test

With backend, frontend, nginx, Postgres, and ChromaDB running:

```bash
cd frontend
npm run test:e2e
```

The test calls the replay controller, logs in as the demo user, drives Dashboard, Map, Timeline, Assistant, Emergency, Incidents, exports a report, and checks dashboard performance.

## Dashboard Performance Check

```bash
curl -k "https://localhost/api/demo/performance/dashboard?plant_id=<plant_id>"
```

Expected: `passed: true`, with `elapsed_ms` below `2000`.

## Troubleshooting

If login fails:

- Run `/api/demo/replay/start` again.
- Confirm migrations have run.
- Confirm the demo user exists by checking backend logs for `demo_replay_started`.

If the alert does not fire:

- Advance to step 5 again.
- Check `/api/demo/replay/status` for a non-null `alert_id`.
- Confirm the Phase 10 dataset is mounted into the backend container at `/app/data`.

If the AI Assistant has no citation:

- Confirm ChromaDB is running.
- Restart the replay. The controller indexes `Demo Gas Maintenance Controls` during start.
- If Chroma is unavailable, backend tests still validate report/timeline flow, but the live assistant citation requires Chroma.

If map/timeline/emergency show fallback data:

- Confirm the browser has the access token in local storage.
- Confirm `/api/demo/replay/status` returns non-null `plant_id` and, after step 5, non-null `incident_id`.

If dashboard exceeds two seconds:

- Check Postgres health and CPU load.
- Confirm no unrelated bulk data has been loaded into the demo plant.
- Run the performance endpoint directly to separate backend aggregation time from browser rendering time.

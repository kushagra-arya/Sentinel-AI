"""Forensic timeline reconstruction service from persisted evidence links."""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import Alert, AlertEvidenceLink
from app.models.incidents import Incident, IncidentEvidenceLink
from app.models.maintenance import MaintenanceActivity
from app.models.notifications import Notification
from app.models.permits import Permit
from app.models.sensor_readings import SensorReading
from app.models.workers import WorkerLocationEvent
from app.schemas.timeline import TimelineEntry, TimelineEvidenceLink, TimelineResponse


class TimelineService:
    """Reconstruct incident and alert timelines entirely from evidence records."""

    @staticmethod
    async def for_incident(session: AsyncSession, *, incident_id: str) -> TimelineResponse:
        """Reconstruct a chronological incident timeline from stored evidence links."""
        incident = await session.get(Incident, incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

        result = await session.execute(
            select(IncidentEvidenceLink).where(IncidentEvidenceLink.incident_id == incident_id)
        )
        entries: list[TimelineEntry] = []
        for link in result.scalars():
            entries.extend(await TimelineService._entries_from_incident_link(session, link))
        entries.append(
            TimelineEntry(
                occurred_at=incident.opened_at,
                event_type="incident_opened",
                title=incident.title,
                description=incident.summary,
                evidence=TimelineEvidenceLink(
                    entity_type="incident",
                    entity_id=incident.id,
                    api_path=f"/api/v1/incidents/{incident.id}",
                ),
            )
        )
        entries.extend(
            await TimelineService._notification_entries(session, plant_id=incident.plant_id)
        )
        return TimelineResponse(
            subject_type="incident",
            subject_id=incident_id,
            entries=sorted(entries, key=lambda entry: entry.occurred_at),
        )

    @staticmethod
    async def for_alert(session: AsyncSession, *, alert_id: str) -> TimelineResponse:
        """Reconstruct a chronological alert timeline from stored evidence links."""
        alert = await session.get(Alert, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

        result = await session.execute(
            select(AlertEvidenceLink).where(AlertEvidenceLink.alert_id == alert_id)
        )
        entries: list[TimelineEntry] = []
        for link in result.scalars():
            entries.extend(await TimelineService._entries_from_alert_link(session, link))
        entries.append(
            TimelineEntry(
                occurred_at=alert.triggered_at,
                event_type="compound_alert",
                title=alert.title,
                description=alert.message,
                evidence=TimelineEvidenceLink(
                    entity_type="alert",
                    entity_id=alert.id,
                    api_path=f"/api/v1/alerts/{alert.id}",
                ),
            )
        )
        entries.extend(
            await TimelineService._notification_entries(session, plant_id=alert.plant_id)
        )
        return TimelineResponse(
            subject_type="alert",
            subject_id=alert_id,
            entries=sorted(entries, key=lambda entry: entry.occurred_at),
        )

    @staticmethod
    async def _entries_from_incident_link(
        session: AsyncSession,
        link: IncidentEvidenceLink,
    ) -> list[TimelineEntry]:
        """Create timeline entries from one incident evidence link."""
        entries: list[TimelineEntry] = []
        if link.alert_id:
            alert_timeline = await TimelineService.for_alert(session, alert_id=link.alert_id)
            entries.extend(alert_timeline.entries)
        if link.sensor_reading_id:
            entry = await TimelineService._sensor_entry(session, link.sensor_reading_id)
            if entry:
                entries.append(entry)
        if link.permit_id:
            entry = await TimelineService._permit_entry(session, link.permit_id)
            if entry:
                entries.append(entry)
        if link.maintenance_activity_id:
            entry = await TimelineService._maintenance_entry(session, link.maintenance_activity_id)
            if entry:
                entries.append(entry)
        if link.worker_location_event_id:
            entry = await TimelineService._worker_entry(session, link.worker_location_event_id)
            if entry:
                entries.append(entry)
        return entries

    @staticmethod
    async def _entries_from_alert_link(
        session: AsyncSession,
        link: AlertEvidenceLink,
    ) -> list[TimelineEntry]:
        """Create timeline entries from one alert evidence link."""
        entries: list[TimelineEntry] = []
        if link.sensor_reading_id:
            entry = await TimelineService._sensor_entry(session, link.sensor_reading_id)
            if entry:
                entries.append(entry)
        if link.permit_id:
            entry = await TimelineService._permit_entry(session, link.permit_id)
            if entry:
                entries.append(entry)
        if link.maintenance_activity_id:
            entry = await TimelineService._maintenance_entry(session, link.maintenance_activity_id)
            if entry:
                entries.append(entry)
        if link.worker_location_event_id:
            entry = await TimelineService._worker_entry(session, link.worker_location_event_id)
            if entry:
                entries.append(entry)
        return entries

    @staticmethod
    async def _sensor_entry(session: AsyncSession, reading_id: str) -> TimelineEntry | None:
        """Create a timeline entry for a sensor reading."""
        reading = await session.get(SensorReading, reading_id)
        if reading is None:
            return None
        return TimelineEntry(
            occurred_at=reading.measured_at,
            event_type="sensor_reading",
            title="Sensor reading recorded",
            description=f"Sensor reading {reading.value} recorded with quality {reading.quality}.",
            evidence=TimelineEvidenceLink(
                entity_type="sensor_reading",
                entity_id=reading.id,
                api_path=f"/api/v1/sensor-readings/{reading.id}",
            ),
        )

    @staticmethod
    async def _permit_entry(session: AsyncSession, permit_id: str) -> TimelineEntry | None:
        """Create a timeline entry for a permit."""
        permit = await session.get(Permit, permit_id)
        if permit is None:
            return None
        return TimelineEntry(
            occurred_at=permit.starts_at,
            event_type="permit_active",
            title=f"Permit {permit.permit_number} active",
            description=f"{permit.permit_type} permit became active in {permit.zone}.",
            evidence=TimelineEvidenceLink(
                entity_type="permit",
                entity_id=permit.id,
                api_path=f"/api/v1/permits/{permit.id}",
            ),
        )

    @staticmethod
    async def _maintenance_entry(session: AsyncSession, activity_id: str) -> TimelineEntry | None:
        """Create a timeline entry for maintenance activity."""
        activity = await session.get(MaintenanceActivity, activity_id)
        if activity is None:
            return None
        return TimelineEntry(
            occurred_at=activity.starts_at,
            event_type="maintenance_started",
            title=f"Maintenance {activity.work_order} started",
            description=f"{activity.maintenance_type} maintenance started in {activity.zone}.",
            evidence=TimelineEvidenceLink(
                entity_type="maintenance_activity",
                entity_id=activity.id,
                api_path=f"/api/v1/maintenance/{activity.id}",
            ),
        )

    @staticmethod
    async def _worker_entry(session: AsyncSession, event_id: str) -> TimelineEntry | None:
        """Create a timeline entry for worker location evidence."""
        event = await session.get(WorkerLocationEvent, event_id)
        if event is None:
            return None
        return TimelineEntry(
            occurred_at=event.observed_at,
            event_type="worker_entered_area",
            title="Worker present in affected area",
            description=f"Worker {event.worker_id} observed in {event.zone}.",
            evidence=TimelineEvidenceLink(
                entity_type="worker_location_event",
                entity_id=event.id,
                api_path=f"/api/v1/worker-location-events/{event.id}",
            ),
        )

    @staticmethod
    async def _notification_entries(session: AsyncSession, *, plant_id: str) -> list[TimelineEntry]:
        """Return notification events associated with a plant."""
        result = await session.execute(
            select(Notification).where(Notification.plant_id == plant_id)
        )
        return [
            TimelineEntry(
                occurred_at=TimelineService._created_at(notification),
                event_type="notification_sent",
                title=notification.title,
                description=notification.body,
                evidence=TimelineEvidenceLink(
                    entity_type="notification",
                    entity_id=notification.id,
                    api_path=f"/api/v1/notifications/{notification.id}",
                ),
            )
            for notification in result.scalars()
        ]

    @staticmethod
    def _created_at(notification: Notification) -> datetime:
        """Return notification creation time."""
        return notification.created_at

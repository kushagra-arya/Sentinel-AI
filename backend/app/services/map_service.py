"""Operational map service for plant layouts, markers, and risk heatmaps."""

from datetime import UTC, datetime
from math import sqrt

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import Alert, AlertEvidenceLink
from app.models.equipment import Equipment
from app.models.map_layers import HazardZone, PlantLayout
from app.models.permits import Permit
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.models.workers import WorkerLocationEvent
from app.schemas.map import (
    AlertMarkerResponse,
    Coordinate,
    HazardZoneCreate,
    HeatmapCell,
    MapMarker,
    MapViewportRequest,
    MapViewportResponse,
    PlantLayoutCreate,
    PlantLayoutResponse,
)
from app.services.audit_service import AuditService


class MapService:
    """Service for operational map layers and spatial risk computation."""

    @staticmethod
    async def create_layout(
        session: AsyncSession,
        *,
        payload: PlantLayoutCreate,
        actor_user_id: str,
    ) -> PlantLayoutResponse:
        """Create an active plant layout from image or georeferenced coordinates."""
        layout = PlantLayout(
            plant_id=payload.plant_id,
            name=payload.name,
            layout_type=payload.layout_type,
            image_uri=payload.image_uri,
            bounds=payload.bounds,
            georeference=payload.georeference,
            description=payload.description,
            is_active=True,
        )
        session.add(layout)
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            action="plant_layout_created",
            target_entity_type="plant",
            target_entity_id=payload.plant_id,
            after_state={"name": payload.name, "layout_type": payload.layout_type},
        )
        await session.commit()
        await session.refresh(layout)
        return MapService._layout_response(layout)

    @staticmethod
    async def create_hazard_zone(
        session: AsyncSession,
        *,
        payload: HazardZoneCreate,
        actor_user_id: str,
    ) -> MapMarker:
        """Create a hazard-zone layer marker."""
        hazard = HazardZone(
            plant_id=payload.plant_id,
            zone=payload.zone,
            name=payload.name,
            hazard_type=payload.hazard_type,
            geometry=payload.geometry,
            severity=payload.severity,
        )
        session.add(hazard)
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            action="hazard_zone_created",
            target_entity_type="hazard_zone",
            target_entity_id=payload.zone,
            after_state={"name": payload.name, "severity": payload.severity},
        )
        await session.commit()
        await session.refresh(hazard)
        return MapService._hazard_marker(hazard)

    @staticmethod
    async def get_layout(session: AsyncSession, *, plant_id: str) -> PlantLayoutResponse:
        """Return active plant layout metadata without dynamic layers."""
        result = await session.execute(
            select(PlantLayout)
            .where(PlantLayout.plant_id == plant_id, PlantLayout.is_active.is_(True))
            .order_by(desc(PlantLayout.created_at))
            .limit(1)
        )
        layout = result.scalar_one_or_none()
        if layout is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plant layout not found.",
            )
        return MapService._layout_response(layout)

    @staticmethod
    async def get_viewport(
        session: AsyncSession,
        *,
        payload: MapViewportRequest,
    ) -> MapViewportResponse:
        """Return dynamic map layers for a viewport without re-fetching layout metadata."""
        markers: list[MapMarker] = []
        if "sensors" in payload.layers:
            markers.extend(await MapService._sensor_markers(session, payload))
        if "workers" in payload.layers:
            markers.extend(await MapService._worker_markers(session, payload))
        if "equipment" in payload.layers:
            markers.extend(await MapService._equipment_markers(session, payload))
        if "permits" in payload.layers:
            markers.extend(await MapService._permit_markers(session, payload))
        if "hazards" in payload.layers:
            markers.extend(await MapService._hazard_markers(session, payload))
        if "alerts" in payload.layers:
            markers.extend(await MapService._alert_markers(session, payload))

        heatmap = (
            await MapService._risk_heatmap(session, payload)
            if "heatmap" in payload.layers
            else []
        )
        return MapViewportResponse(
            plant_id=payload.plant_id,
            markers=markers,
            heatmap=heatmap,
            generated_at=datetime.now(UTC),
        )

    @staticmethod
    async def alert_markers(session: AsyncSession, *, plant_id: str) -> list[AlertMarkerResponse]:
        """Return alert markers positioned from evidence chains."""
        alert_query = (
            select(Alert)
            .where(Alert.plant_id == plant_id)
            .order_by(desc(Alert.triggered_at))
        )
        alerts = (await session.execute(alert_query)).scalars()
        markers = []
        for alert in alerts:
            coordinate = await MapService._alert_coordinate(session, alert.id)
            markers.append(
                AlertMarkerResponse(
                    alert_id=alert.id,
                    title=alert.title,
                    risk_level=alert.risk_level,
                    coordinate=coordinate,
                    evidence_link=f"/api/v1/timeline/alerts/{alert.id}",
                )
            )
        return markers

    @staticmethod
    async def _sensor_markers(
        session: AsyncSession,
        payload: MapViewportRequest,
    ) -> list[MapMarker]:
        """Return sensor markers in viewport."""
        result = await session.execute(select(Sensor).where(Sensor.plant_id == payload.plant_id))
        return [
            MapMarker(
                id=sensor.id,
                marker_type="sensor",
                title=sensor.name,
                zone=sensor.zone,
                coordinate=Coordinate(x=float(sensor.x_coordinate), y=float(sensor.y_coordinate)),
                status=sensor.status.value,
                evidence_link=f"/api/v1/sensors/{sensor.id}",
            )
            for sensor in result.scalars()
            if MapService._inside(payload, float(sensor.x_coordinate), float(sensor.y_coordinate))
        ]

    @staticmethod
    async def _worker_markers(
        session: AsyncSession,
        payload: MapViewportRequest,
    ) -> list[MapMarker]:
        """Return latest worker-location markers in viewport."""
        result = await session.execute(
            select(WorkerLocationEvent)
            .where(WorkerLocationEvent.plant_id == payload.plant_id)
            .order_by(desc(WorkerLocationEvent.observed_at))
        )
        seen_workers: set[str] = set()
        markers: list[MapMarker] = []
        for event in result.scalars():
            if event.worker_id in seen_workers:
                continue
            seen_workers.add(event.worker_id)
            x = float(event.x_coordinate)
            y = float(event.y_coordinate)
            if not MapService._inside(payload, x, y):
                continue
            markers.append(
                MapMarker(
                    id=event.id,
                    marker_type="worker",
                    title=f"Worker {event.worker_id}",
                    zone=event.zone,
                    coordinate=Coordinate(x=x, y=y),
                    status="present",
                    evidence_link=f"/api/v1/timeline/evidence/worker_location_events/{event.id}",
                )
            )
        return markers

    @staticmethod
    async def _equipment_markers(
        session: AsyncSession,
        payload: MapViewportRequest,
    ) -> list[MapMarker]:
        """Return equipment markers approximated by colocated sensors when available."""
        result = await session.execute(
            select(Equipment).where(Equipment.plant_id == payload.plant_id)
        )
        markers = []
        for equipment in result.scalars():
            coordinate = await MapService._zone_coordinate(
                session,
                payload.plant_id,
                equipment.zone,
            )
            markers.append(
                MapMarker(
                    id=equipment.id,
                    marker_type="equipment",
                    title=equipment.name,
                    zone=equipment.zone,
                    coordinate=coordinate,
                    status=equipment.status.value,
                    evidence_link=f"/api/v1/equipment/{equipment.id}",
                )
            )
        return markers

    @staticmethod
    async def _permit_markers(
        session: AsyncSession,
        payload: MapViewportRequest,
    ) -> list[MapMarker]:
        """Return permit-zone markers."""
        result = await session.execute(select(Permit).where(Permit.plant_id == payload.plant_id))
        markers = []
        for permit in result.scalars():
            coordinate = await MapService._zone_coordinate(session, payload.plant_id, permit.zone)
            markers.append(
                MapMarker(
                    id=permit.id,
                    marker_type="permit",
                    title=permit.permit_number,
                    zone=permit.zone,
                    coordinate=coordinate,
                    status=permit.status.value,
                    evidence_link=f"/api/v1/permits/{permit.id}",
                )
            )
        return markers

    @staticmethod
    async def _hazard_markers(
        session: AsyncSession,
        payload: MapViewportRequest,
    ) -> list[MapMarker]:
        """Return hazard-zone markers."""
        result = await session.execute(
            select(HazardZone).where(HazardZone.plant_id == payload.plant_id)
        )
        return [MapService._hazard_marker(hazard) for hazard in result.scalars()]

    @staticmethod
    async def _alert_markers(session: AsyncSession, payload: MapViewportRequest) -> list[MapMarker]:
        """Return alert markers positioned from evidence."""
        markers = []
        for marker in await MapService.alert_markers(session, plant_id=payload.plant_id):
            markers.append(
                MapMarker(
                    id=marker.alert_id,
                    marker_type="alert",
                    title=marker.title,
                    zone=None,
                    coordinate=marker.coordinate,
                    status=marker.risk_level.value,
                    evidence_link=marker.evidence_link,
                )
            )
        return markers

    @staticmethod
    async def _risk_heatmap(
        session: AsyncSession,
        payload: MapViewportRequest,
    ) -> list[HeatmapCell]:
        """Compute inverse-distance weighted risk heatmap cells from alert evidence."""
        alert_markers = await MapService.alert_markers(session, plant_id=payload.plant_id)
        weighted = [
            (marker, MapService._risk_weight(marker.risk_level.value))
            for marker in alert_markers
            if marker.coordinate is not None
        ]
        if not weighted:
            return []
        cells: list[HeatmapCell] = []
        grid_size = max((payload.max_x - payload.min_x) / 6.0, 1.0)
        x = payload.min_x
        while x <= payload.max_x:
            y = payload.min_y
            while y <= payload.max_y:
                numerator = 0.0
                denominator = 0.0
                contributors: list[str] = []
                for marker, weight in weighted:
                    assert marker.coordinate is not None
                    distance = sqrt((x - marker.coordinate.x) ** 2 + (y - marker.coordinate.y) ** 2)
                    influence = 1.0 / max(distance, 1.0)
                    numerator += weight * influence
                    denominator += influence
                    contributors.append(marker.alert_id)
                cells.append(
                    HeatmapCell(
                        x=round(x, 3),
                        y=round(y, 3),
                        intensity=round(min(numerator / denominator, 1.0), 4),
                        contributing_alert_ids=contributors,
                    )
                )
                y += grid_size
            x += grid_size
        return cells

    @staticmethod
    async def _alert_coordinate(session: AsyncSession, alert_id: str) -> Coordinate | None:
        """Resolve an alert coordinate from its evidence chain."""
        result = await session.execute(
            select(AlertEvidenceLink).where(AlertEvidenceLink.alert_id == alert_id)
        )
        for link in result.scalars():
            if link.sensor_reading_id:
                reading = await session.get(SensorReading, link.sensor_reading_id)
                if reading is not None:
                    sensor = await session.get(Sensor, reading.sensor_id)
                    if sensor is not None:
                        return Coordinate(
                            x=float(sensor.x_coordinate),
                            y=float(sensor.y_coordinate),
                        )
            if link.worker_location_event_id:
                event = await session.get(WorkerLocationEvent, link.worker_location_event_id)
                if event is not None:
                    return Coordinate(x=float(event.x_coordinate), y=float(event.y_coordinate))
            if link.permit_id:
                permit = await session.get(Permit, link.permit_id)
                if permit is not None:
                    return await MapService._zone_coordinate(session, permit.plant_id, permit.zone)
        return None

    @staticmethod
    async def _zone_coordinate(
        session: AsyncSession,
        plant_id: str,
        zone: str,
    ) -> Coordinate | None:
        """Approximate a zone coordinate from sensors in the same zone."""
        result = await session.execute(
            select(Sensor).where(Sensor.plant_id == plant_id, Sensor.zone == zone).limit(1)
        )
        sensor = result.scalar_one_or_none()
        if sensor is None:
            return None
        return Coordinate(x=float(sensor.x_coordinate), y=float(sensor.y_coordinate))

    @staticmethod
    def _hazard_marker(hazard: HazardZone) -> MapMarker:
        """Map a hazard-zone record to a marker."""
        centroid = hazard.geometry.get("centroid") if isinstance(hazard.geometry, dict) else None
        coordinate = None
        if isinstance(centroid, dict):
            coordinate = Coordinate(x=float(centroid["x"]), y=float(centroid["y"]))
        return MapMarker(
            id=hazard.id,
            marker_type="hazard",
            title=hazard.name,
            zone=hazard.zone,
            coordinate=coordinate,
            status=hazard.severity,
            evidence_link=f"/api/v1/map/hazards/{hazard.id}",
        )

    @staticmethod
    def _layout_response(layout: PlantLayout) -> PlantLayoutResponse:
        """Map a plant layout ORM record to an API response."""
        return PlantLayoutResponse(
            id=layout.id,
            plant_id=layout.plant_id,
            name=layout.name,
            layout_type=layout.layout_type,
            image_uri=layout.image_uri,
            bounds=layout.bounds,
            georeference=layout.georeference,
            description=layout.description,
        )

    @staticmethod
    def _inside(payload: MapViewportRequest, x: float, y: float) -> bool:
        """Return whether a coordinate is inside a viewport."""
        return payload.min_x <= x <= payload.max_x and payload.min_y <= y <= payload.max_y

    @staticmethod
    def _risk_weight(risk_level: str) -> float:
        """Map risk level to heatmap intensity weight."""
        return {"low": 0.25, "medium": 0.5, "high": 0.8, "critical": 1.0}.get(risk_level, 0.2)

"""Emergency response panel and incident report generation service."""

from base64 import b64encode
from csv import DictWriter
from datetime import UTC, datetime
from io import StringIO
import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import Alert
from app.models.equipment import Equipment
from app.models.incidents import Incident, IncidentEvidenceLink
from app.models.maintenance import MaintenanceActivity
from app.models.permits import Permit
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.models.workers import Worker, WorkerLocationEvent
from app.schemas.incidents import (
    EmergencyContact,
    EmergencyPanelState,
    EvidenceSummaryItem,
    ExportResponse,
    IncidentReport,
    NearbyEquipment,
    ReportStubResponse,
    RoleAction,
    WorkerPresence,
)
from app.services.timeline_service import TimelineService


class ReportService:
    """Generate emergency response state and exports from persisted evidence."""

    @staticmethod
    async def emergency_panel(session: AsyncSession, *, incident_id: str) -> EmergencyPanelState:
        """Return live emergency panel state for an incident."""
        report = await ReportService.incident_report(session, incident_id=incident_id)
        return report.panel

    @staticmethod
    async def incident_report(session: AsyncSession, *, incident_id: str) -> IncidentReport:
        """Generate an incident report from evidence links and timeline reconstruction."""
        incident = await session.get(Incident, incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

        evidence_links = list(
            (
                await session.execute(
                    select(IncidentEvidenceLink).where(
                        IncidentEvidenceLink.incident_id == incident_id
                    )
                )
            ).scalars()
        )
        alert_rules = await ReportService._triggering_rules(session, evidence_links, incident)
        affected_zone = await ReportService._affected_zone(session, evidence_links, incident)
        workers = await ReportService._workers_present(session, evidence_links, affected_zone)
        equipment = await ReportService._nearby_equipment(session, incident.plant_id, affected_zone)
        actions = ReportService._recommended_actions(alert_rules, incident.risk_level.value)
        timeline = (await TimelineService.for_incident(session, incident_id=incident_id)).entries
        evidence_summary = await ReportService._evidence_summary(session, evidence_links)

        panel = EmergencyPanelState(
            incident_id=incident.id,
            affected_area=affected_zone,
            risk_level=incident.risk_level,
            triggering_rules=alert_rules,
            workers_present=workers,
            nearby_equipment=equipment,
            nearest_exit=ReportService._nearest_exit(affected_zone),
            emergency_contacts=ReportService._emergency_contacts(),
            recommended_actions=actions,
        )
        return IncidentReport(
            incident_id=incident.id,
            generated_at=datetime.now(UTC),
            risk_type=ReportService._risk_type(alert_rules),
            affected_zone=affected_zone,
            triggering_rules=alert_rules,
            panel=panel,
            timeline=timeline,
            action_checklist=actions,
            evidence_summary=evidence_summary,
        )

    @staticmethod
    async def export_incident_csv(session: AsyncSession, *, incident_id: str) -> ExportResponse:
        """Export a generated incident report as CSV."""
        report = await ReportService.incident_report(session, incident_id=incident_id)
        output = StringIO()
        writer = DictWriter(
            output,
            fieldnames=["section", "entity_type", "entity_id", "timestamp", "detail"],
        )
        writer.writeheader()
        for item in report.evidence_summary:
            writer.writerow(
                {
                    "section": "evidence",
                    "entity_type": item.entity_type,
                    "entity_id": item.entity_id,
                    "timestamp": item.observed_at.isoformat() if item.observed_at else "",
                    "detail": item.description,
                }
            )
        for entry in report.timeline:
            writer.writerow(
                {
                    "section": "timeline",
                    "entity_type": entry.evidence.entity_type,
                    "entity_id": entry.evidence.entity_id,
                    "timestamp": entry.occurred_at.isoformat(),
                    "detail": entry.description,
                }
            )
        content = output.getvalue().encode("utf-8")
        return ExportResponse(
            filename=ReportService._safe_export_filename("incident", incident_id, "csv"),
            media_type="text/csv",
            content_base64=b64encode(content).decode("ascii"),
        )

    @staticmethod
    async def export_incident_pdf(session: AsyncSession, *, incident_id: str) -> ExportResponse:
        """Export a generated incident report as a minimal PDF."""
        report = await ReportService.incident_report(session, incident_id=incident_id)
        lines = [
            "SentinelAI Incident Report",
            f"Incident: {report.incident_id}",
            f"Risk Type: {report.risk_type}",
            f"Affected Zone: {report.affected_zone}",
            f"Triggering Rules: {', '.join(report.triggering_rules) or 'none'}",
            "Evidence:",
        ]
        lines.extend(
            f"- {item.entity_type} {item.entity_id}: {item.description}"
            for item in report.evidence_summary
        )
        content = MinimalPdf.render(lines)
        return ExportResponse(
            filename=ReportService._safe_export_filename("incident", incident_id, "pdf"),
            media_type="application/pdf",
            content_base64=b64encode(content).decode("ascii"),
        )

    @staticmethod
    def stub_report(report_type: str) -> ReportStubResponse:
        """Return a consistent stub for future report exports."""
        ReportService._validate_report_type(report_type)
        return ReportStubResponse(
            report_type=report_type,
            status="stubbed",
            export_pipeline="incident_report_pdf_csv_pipeline",
        )

    @staticmethod
    def _safe_export_filename(prefix: str, identifier: str, extension: str) -> str:
        """Build an export filename only from approved filename characters."""
        safe_pattern = r"^[A-Za-z0-9_.:-]{1,64}$"
        if not re.fullmatch(safe_pattern, identifier):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid export identifier.",
            )
        if extension not in {"csv", "pdf"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported export extension.",
            )
        return f"{prefix}-{identifier}.{extension}"

    @staticmethod
    def _validate_report_type(report_type: str) -> None:
        """Reject unknown report identifiers before export pipeline dispatch."""
        allowed = {
            "daily-safety",
            "incident",
            "risk-trend",
            "equipment-risk",
            "permit-summary",
            "compliance-summary",
        }
        if report_type not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported report type.",
            )

    @staticmethod
    async def _triggering_rules(
        session: AsyncSession,
        links: list[IncidentEvidenceLink],
        incident: Incident,
    ) -> list[str]:
        """Infer triggering rules from linked alert sources."""
        alert_ids = [link.alert_id for link in links if link.alert_id]
        if incident.primary_alert_id:
            alert_ids.append(incident.primary_alert_id)
        rules: list[str] = []
        for alert_id in sorted(set(alert_ids)):
            alert = await session.get(Alert, alert_id)
            if alert is not None and alert.source.startswith("rule:"):
                rules.append(alert.source.removeprefix("rule:"))
        return sorted(set(rules))

    @staticmethod
    async def _affected_zone(
        session: AsyncSession,
        links: list[IncidentEvidenceLink],
        incident: Incident,
    ) -> str:
        """Derive affected zone from linked evidence."""
        for link in links:
            if link.worker_location_event_id:
                event = await session.get(WorkerLocationEvent, link.worker_location_event_id)
                if event is not None:
                    return event.zone
            if link.maintenance_activity_id:
                activity = await session.get(MaintenanceActivity, link.maintenance_activity_id)
                if activity is not None:
                    return activity.zone
            if link.permit_id:
                permit = await session.get(Permit, link.permit_id)
                if permit is not None:
                    return permit.zone
            if link.sensor_reading_id:
                reading = await session.get(SensorReading, link.sensor_reading_id)
                if reading is not None:
                    sensor = await session.get(Sensor, reading.sensor_id)
                    if sensor is not None:
                        return sensor.zone
        return f"Plant {incident.plant_id}"

    @staticmethod
    async def _workers_present(
        session: AsyncSession,
        links: list[IncidentEvidenceLink],
        affected_zone: str,
    ) -> list[WorkerPresence]:
        """Return workers present from linked location evidence."""
        workers: list[WorkerPresence] = []
        seen: set[str] = set()
        for link in links:
            if not link.worker_location_event_id:
                continue
            event = await session.get(WorkerLocationEvent, link.worker_location_event_id)
            if event is None or event.worker_id in seen:
                continue
            worker = await session.get(Worker, event.worker_id)
            seen.add(event.worker_id)
            workers.append(
                WorkerPresence(
                    worker_id=event.worker_id,
                    badge_id=worker.badge_id if worker else None,
                    full_name=worker.full_name if worker else None,
                    zone=event.zone or affected_zone,
                    observed_at=event.observed_at,
                )
            )
        return workers

    @staticmethod
    async def _nearby_equipment(
        session: AsyncSession,
        plant_id: str,
        affected_zone: str,
    ) -> list[NearbyEquipment]:
        """Return equipment in the affected zone."""
        result = await session.execute(
            select(Equipment).where(Equipment.plant_id == plant_id, Equipment.zone == affected_zone)
        )
        return [
            NearbyEquipment(
                equipment_id=item.id,
                asset_tag=item.asset_tag,
                name=item.name,
                equipment_type=item.equipment_type,
                zone=item.zone,
                status=item.status.value,
            )
            for item in result.scalars()
        ]

    @staticmethod
    async def _evidence_summary(
        session: AsyncSession,
        links: list[IncidentEvidenceLink],
    ) -> list[EvidenceSummaryItem]:
        """Build audit-ready evidence summary from evidence links."""
        items: list[EvidenceSummaryItem] = []
        for link in links:
            if link.sensor_reading_id:
                reading = await session.get(SensorReading, link.sensor_reading_id)
                if reading:
                    items.append(
                        EvidenceSummaryItem(
                            entity_type="sensor_reading",
                            entity_id=reading.id,
                            observed_at=reading.measured_at,
                            description=f"Sensor reading quality {reading.quality}",
                            value=str(reading.value),
                        )
                    )
            if link.permit_id:
                permit = await session.get(Permit, link.permit_id)
                if permit:
                    items.append(
                        EvidenceSummaryItem(
                            entity_type="permit",
                            entity_id=permit.id,
                            observed_at=permit.starts_at,
                            description=(
                                f"{permit.permit_type} permit {permit.status.value} "
                                f"in {permit.zone}"
                            ),
                            value=permit.permit_number,
                        )
                    )
            if link.maintenance_activity_id:
                activity = await session.get(MaintenanceActivity, link.maintenance_activity_id)
                if activity:
                    items.append(
                        EvidenceSummaryItem(
                            entity_type="maintenance_activity",
                            entity_id=activity.id,
                            observed_at=activity.starts_at,
                            description=(
                                f"{activity.maintenance_type} maintenance in {activity.zone}"
                            ),
                            value=activity.work_order,
                        )
                    )
        return items

    @staticmethod
    def _recommended_actions(rules: list[str], risk_level: str) -> list[RoleAction]:
        """Return concrete role-specific actions based on triggering rules."""
        if "confined_space_ventilation_failure" in rules:
            return [
                RoleAction(
                    role="Supervisor",
                    action="Stop confined-space entry and account for entrants.",
                    priority=1,
                ),
                RoleAction(
                    role="Safety Officer",
                    action="Verify ventilation restoration before re-entry.",
                    priority=2,
                ),
                RoleAction(
                    role="Compliance Officer",
                    action="Preserve permit and gas-test records.",
                    priority=3,
                ),
            ]
        if "high_temperature_pressure_increase" in rules:
            return [
                RoleAction(
                    role="Supervisor",
                    action="Reduce equipment load and clear nonessential staff.",
                    priority=1,
                ),
                RoleAction(
                    role="Safety Officer",
                    action="Confirm pressure relief path and thermal isolation.",
                    priority=2,
                ),
                RoleAction(
                    role="Maintenance Lead",
                    action="Inspect pressure vessel trend and lockout status.",
                    priority=3,
                ),
            ]
        if "gas_increasing_maintenance_workers" in rules or risk_level in {"high", "critical"}:
            return [
                RoleAction(
                    role="Supervisor",
                    action="Move workers out of the affected zone immediately.",
                    priority=1,
                ),
                RoleAction(
                    role="Safety Officer",
                    action="Pause maintenance and verify gas trend with portable meter.",
                    priority=2,
                ),
                RoleAction(
                    role="Maintenance Lead",
                    action="Confirm isolation and remove ignition sources.",
                    priority=3,
                ),
            ]
        return [
            RoleAction(
                role="Supervisor",
                action="Monitor area and confirm conditions remain stable.",
                priority=1,
            )
        ]

    @staticmethod
    def _risk_type(rules: list[str]) -> str:
        """Return human-readable risk type from triggering rules."""
        mapping = {
            "gas_increasing_maintenance_workers": "Gas rise during maintenance with workers nearby",
            "confined_space_ventilation_failure": "Confined-space ventilation failure",
            "high_temperature_pressure_increase": (
                "Equipment failure risk from temperature and pressure"
            ),
        }
        return (
            mapping.get(rules[0], "Operational safety risk")
            if rules
            else "Operational safety risk"
        )

    @staticmethod
    def _nearest_exit(zone: str) -> str:
        """Return a deterministic nearest exit label for the affected zone."""
        return {
            "Zone A": "North muster exit A1",
            "Zone B": "East emergency stair B2",
            "Zone C": "South gate C1",
        }.get(zone, "Nearest marked emergency exit")

    @staticmethod
    def _emergency_contacts() -> list[EmergencyContact]:
        """Return emergency contacts for the live response panel."""
        return [
            EmergencyContact(
                role="Incident Commander",
                name="Shift Safety Lead",
                channel="radio-1",
            ),
            EmergencyContact(role="Medical", name="On-site medical room", channel="extension-222"),
            EmergencyContact(role="Plant Control", name="Control room", channel="extension-100"),
        ]


class MinimalPdf:
    """Small PDF renderer for dependency-free incident report export."""

    @staticmethod
    def render(lines: list[str]) -> bytes:
        """Render text lines into a minimal single-page PDF."""
        escaped_lines = [MinimalPdf._escape(line[:110]) for line in lines[:42]]
        text_commands = ["BT", "/F1 10 Tf", "50 780 Td"]
        for index, line in enumerate(escaped_lines):
            if index:
                text_commands.append("0 -16 Td")
            text_commands.append(f"({line}) Tj")
        text_commands.append("ET")
        stream = "\n".join(text_commands).encode("utf-8")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream",
        ]
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for number, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{number} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n".encode("ascii")
        )
        return bytes(pdf)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape PDF text characters."""
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

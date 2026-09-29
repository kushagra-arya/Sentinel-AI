"""Pydantic schemas for operational plant map APIs."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import RiskLevel


class Coordinate(BaseModel):
    """Two-dimensional plant coordinate."""

    x: float = Field(ge=-1_000_000, le=1_000_000, description="Plant X coordinate.")
    y: float = Field(ge=-1_000_000, le=1_000_000, description="Plant Y coordinate.")


class PlantLayoutCreate(BaseModel):
    """Request to create or update an active plant layout."""

    plant_id: str = Field(min_length=1, max_length=64, description="Plant identifier.")
    name: str = Field(min_length=1, max_length=160, description="Layout name.")
    layout_type: Literal["image", "georeferenced_coordinates"] = Field(
        description="image or georeferenced_coordinates."
    )
    image_uri: str | None = Field(
        default=None,
        max_length=500,
        description="Uploaded image URI.",
    )
    bounds: dict = Field(description="Coordinate bounds for the layout.")
    georeference: dict | None = Field(default=None, description="Optional georeference metadata.")
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Layout description.",
    )

    @field_validator("image_uri")
    @classmethod
    def reject_unsafe_image_uri(cls, value: str | None) -> str | None:
        """Reject traversal-style image URIs before storing layout metadata."""
        if value is not None and (".." in value or "\\" in value):
            raise ValueError("Image URI must not contain path traversal segments.")
        return value


class HazardZoneCreate(BaseModel):
    """Request to create a hazard zone."""

    plant_id: str = Field(min_length=1, max_length=64, description="Plant identifier.")
    zone: str = Field(min_length=1, max_length=120, description="Operational zone code.")
    name: str = Field(min_length=1, max_length=160, description="Hazard zone name.")
    hazard_type: str = Field(min_length=1, max_length=80, description="Hazard type.")
    geometry: dict = Field(description="Polygon or bounding geometry.")
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="Hazard severity label."
    )


class MapMarker(BaseModel):
    """Map marker for a plant entity or alert."""

    id: str = Field(description="Marker identifier.")
    marker_type: str = Field(description="sensor, worker, equipment, permit, hazard, or alert.")
    title: str = Field(description="Marker title.")
    zone: str | None = Field(description="Operational zone.")
    coordinate: Coordinate | None = Field(description="Marker coordinate if known.")
    status: str = Field(description="Marker status.")
    evidence_link: str | None = Field(description="API path for supporting evidence.")


class HeatmapCell(BaseModel):
    """Computed spatial risk heatmap cell."""

    x: float = Field(description="Grid cell X coordinate.")
    y: float = Field(description="Grid cell Y coordinate.")
    intensity: float = Field(description="Risk intensity from 0 to 1.")
    contributing_alert_ids: list[str] = Field(description="Alerts contributing to this cell.")


class PlantLayoutResponse(BaseModel):
    """Plant layout response."""

    id: str = Field(description="Layout identifier.")
    plant_id: str = Field(description="Plant identifier.")
    name: str = Field(description="Layout name.")
    layout_type: str = Field(description="Layout type.")
    image_uri: str | None = Field(description="Image URI.")
    bounds: dict = Field(description="Coordinate bounds.")
    georeference: dict | None = Field(description="Georeference metadata.")
    description: str | None = Field(description="Layout description.")


class MapViewportRequest(BaseModel):
    """Map viewport and layer request that avoids re-fetching layout data."""

    plant_id: str = Field(min_length=1, max_length=64, description="Plant identifier.")
    zoom: float = Field(ge=0, le=24, description="Client zoom level.")
    min_x: float = Field(description="Viewport minimum X.")
    min_y: float = Field(description="Viewport minimum Y.")
    max_x: float = Field(description="Viewport maximum X.")
    max_y: float = Field(description="Viewport maximum Y.")
    layers: list[str] = Field(min_length=1, max_length=7, description="Requested dynamic layers.")

    @field_validator("layers")
    @classmethod
    def validate_layers(cls, value: list[str]) -> list[str]:
        """Restrict layer toggles to supported dynamic map layers."""
        allowed = {"sensors", "workers", "equipment", "permits", "hazards", "alerts", "heatmap"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(f"Unsupported map layers: {', '.join(unknown)}")
        return value

    @model_validator(mode="after")
    def validate_bounds(self) -> "MapViewportRequest":
        """Ensure viewport bounds describe a valid rectangle."""
        if self.min_x >= self.max_x or self.min_y >= self.max_y:
            raise ValueError("Viewport minimum bounds must be less than maximum bounds.")
        return self


class MapViewportResponse(BaseModel):
    """Dynamic map layers for a viewport."""

    plant_id: str = Field(description="Plant identifier.")
    markers: list[MapMarker] = Field(description="Requested markers.")
    heatmap: list[HeatmapCell] = Field(description="Computed heatmap cells.")
    generated_at: datetime = Field(description="Generation timestamp.")


class AlertMarkerResponse(BaseModel):
    """Alert marker positioned from evidence chain."""

    alert_id: str = Field(description="Alert identifier.")
    title: str = Field(description="Alert title.")
    risk_level: RiskLevel = Field(description="Alert risk level.")
    coordinate: Coordinate | None = Field(description="Evidence-derived coordinate.")
    evidence_link: str = Field(description="Clickable evidence API path.")

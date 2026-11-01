"""Optional YOLO-based object detection wrapper.

The project is intentionally built to be YOLO-ready: if `ultralytics` is installed,
this class loads a model and returns detections for obstacle and scene understanding.
If it is not installed, the detector degrades gracefully and returns no detections,
so the rest of the robot stack keeps running.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

LOGGER = logging.getLogger(__name__)

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    YOLO = None  # type: ignore


@dataclass
class Detection:
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0


class YOLODetector:
    """Minimal YOLO wrapper for camera-based autonomy in ROS/Gazebo.

    The detector is optional and does not block the rest of the project when the
    dependency is absent. This keeps the repository usable in headless builds and
    VMs while still supporting real YOLO detection when installed.
    """

    def __init__(self, model_path: str = "yolov8n.pt", conf: float = 0.25, iou: float = 0.45, device: str | None = None):
        self.model_path = model_path
        self.conf = conf
        self.iou = iou
        self.device = device
        self.model = None

        if YOLO is None:
            LOGGER.warning("YOLO is not available: install `ultralytics` to enable model-based detection.")
            return

        try:
            self.model = YOLO(model_path)
        except Exception as exc:  # pragma: no cover - model download can fail at runtime
            LOGGER.warning("YOLO model failed to load: %s", exc)
            self.model = None

    def available(self) -> bool:
        return self.model is not None

    def detect(self, bgr) -> List[Detection]:
        if self.model is None:
            return []

        image_size = max(320, ((max(bgr.shape[:2]) + 31) // 32) * 32)
        results = self.model(
            bgr,
            imgsz=image_size,
            conf=self.conf,
            iou=self.iou,
            verbose=False,
            device=self.device,
        )
        detections: List[Detection] = []
        for result in results:
            names = getattr(result, "names", {})
            for box in getattr(result, "boxes", []) or []:
                if hasattr(box, "cls") and hasattr(box, "conf") and hasattr(box, "xyxy"):
                    cls_index = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].cpu().tolist()]
                    detections.append(
                        Detection(
                            label=str(names.get(cls_index, str(cls_index))),
                            confidence=conf,
                            x1=x1,
                            y1=y1,
                            x2=x2,
                            y2=y2,
                        )
                    )
        return detections

    def filter_labels(self, detections: List[Detection], labels: List[str]) -> List[Detection]:
        allowed = {label.lower() for label in labels}
        return [d for d in detections if d.label.lower() in allowed]


OBSTACLE_LABELS = {
    "person", "bicycle", "car", "motorcycle", "bus", "truck", "train", "boat",
    "bench", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear",
    "zebra", "giraffe", "backpack", "umbrella", "suitcase", "chair", "couch",
    "potted plant", "dining table", "skateboard", "surfboard",
}


def is_forward_obstacle(detection, image_shape):
    """Whether a detected COCO object overlaps the robot's near forward corridor."""
    height, width = image_shape[:2]
    return (
        detection.label.lower() in OBSTACLE_LABELS
        and width * 0.2 <= detection.center_x <= width * 0.8
        and detection.y2 >= height * 0.55
    )


def apply_overrides(
    detections,
    img,
    red,
    green,
    obs,
    traffic_light_areas,
    obs_value=2500,
    traffic_lights_enabled=True,
):
    """Use near, in-path YOLO objects as obstacle cues and inspect signal colors."""
    for d in detections:
        lab = d.label.lower()
        if is_forward_obstacle(d, img.shape):
            obs = max(obs, obs_value)
        elif lab == "traffic light" and traffic_lights_enabled:
            x1, y1, x2, y2 = (max(0, int(v)) for v in (d.x1, d.y1, d.x2, d.y2))
            crop = img[y1:y2, x1:x2]
            if crop.size:
                r, g = traffic_light_areas(crop)
                red, green = max(red, r), max(green, g)
    return red, green, obs

"""Exact millimetre geometry primitives; no inferred zones or automatic pathfinding."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Point:
    x: int
    y: int
    z: int = 0

    def __post_init__(self):
        if any(type(n) is not int for n in (self.x, self.y, self.z)):
            raise ValueError("Positions must use integer millimetres")


@dataclass(frozen=True)
class SolidBox:
    minimum: Point
    maximum: Point

    def __post_init__(self):
        if any(getattr(self.minimum, axis) > getattr(self.maximum, axis)
               for axis in ("x", "y", "z")):
            raise ValueError("Inverted obstacle bounds")


def in_range(origin: Point, target: Point, reach_mm: int) -> bool:
    if type(reach_mm) is not int or reach_mm < 0:
        raise ValueError("Range must use nonnegative integer millimetres")
    return sum((getattr(origin, axis) - getattr(target, axis)) ** 2
               for axis in ("x", "y", "z")) <= reach_mm ** 2


def intersects(origin: Point, target: Point, box: SolidBox) -> bool:
    low, high = Fraction(0), Fraction(1)
    for axis in ("x", "y", "z"):
        start, end = getattr(origin, axis), getattr(target, axis)
        minimum, maximum = getattr(box.minimum, axis), getattr(box.maximum, axis)
        delta = end - start
        if not delta:
            if not minimum <= start <= maximum:
                return False
            continue
        first, last = sorted((Fraction(minimum - start, delta),
                              Fraction(maximum - start, delta)))
        low, high = max(low, first), min(high, last)
        if low > high:
            return False
    return True


def legal_target(origin, target, reach_mm, obstacles=()):
    if not in_range(origin, target, reach_mm):
        return {"legal": False, "reason": "Out of range"}
    if any(intersects(origin, target, obstacle) for obstacle in obstacles):
        return {"legal": False, "reason": "Blocked by solid cover"}
    return {"legal": True, "reason": "Within range and clear line of effect"}

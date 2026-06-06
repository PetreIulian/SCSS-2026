import math
import numpy as np
import tinyik

_DEFAULT_LIMITS = [
    (-math.pi / 2,      math.pi / 2),
    (-math.pi / 2,      math.pi / 2),
    (-math.pi / 2,   math.pi / 2),  
    (-math.pi / 2,   math.pi /2)
]

_NEUTRAL_ANGLES = [0.0, 0.0, 0.0, 0.0]


class IKError(Exception):
    pass


class Arm:
    def __init__(
        self,
        l1 = 108.59,
        l2 = 128.11,
        l3 = 159.91,
        l4 = 62.45,
        limits: list[tuple[float, float]] | None = None,
        max_position_error_mm: float = 1.0,
        deterministic: bool = True,
    ):
        self.limits = limits if limits is not None else _DEFAULT_LIMITS
        self.max_position_error_mm = max_position_error_mm
        self.deterministic = deterministic

        self._arm = tinyik.Actuator([
            "z", [0, 0, l1],  # J1
            "y", [0, 0, l2],  # J2
            "y", [0, 0, l3],  # J3
            "y", [0, 0, l4],  # J4
        ])

    def go_to_cartesian(self, x: float, y: float, z: float) -> tuple[int, int, int, int] | None:
        j1_required = math.atan2(y, x)
        lo, hi = self.limits[0]
        if not (lo <= j1_required <= hi):
            print(f"J1 = {math.degrees(j1_required):.2f}° out of range [{math.degrees(lo):.1f}°, {math.degrees(hi):.1f}°]")
            return None

        snapshot = np.copy(self._arm.angles)

        try:
            if self.deterministic:
                self._arm.angles = _NEUTRAL_ANGLES

            self._arm.ee = [x, y, z]

            error_mm = float(np.linalg.norm(np.array(self._arm.ee) - np.array([x, y, z])))
            if error_mm > self.max_position_error_mm:
                self._arm.angles = snapshot
                print(f"Unreachable [{x}, {y}, {z}] — solver residual {error_mm:.3f} mm")
                return None

            norm_angles = [math.atan2(math.sin(a), math.cos(a)) for a in self._arm.angles]

            for i, (angle, (lo, hi)) in enumerate(zip(norm_angles, self.limits)):
                if not (lo <= angle <= hi):
                    self._arm.angles = snapshot
                    print(f"J{i+1} = {math.degrees(angle):.2f}° out of range [{math.degrees(lo):.1f}°, {math.degrees(hi):.1f}°]")
                    return None

            servo_angles = []
            for angle in norm_angles:
                deg_servo = round(math.degrees(angle)) + 90

                deg_servo = max(0, min(180, deg_servo))
                servo_angles.append(deg_servo)

            return tuple(servo_angles)

        except Exception as e:
            self._arm.angles = snapshot
            print(f"IK error for [{x}, {y}, {z}]: {e}")
            return None
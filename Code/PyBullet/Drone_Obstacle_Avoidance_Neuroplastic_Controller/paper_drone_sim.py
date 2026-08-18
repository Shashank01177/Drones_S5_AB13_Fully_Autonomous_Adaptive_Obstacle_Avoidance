"""PyBullet reconstruction of the drone obstacle-avoidance simulation in Devos et al.

The DSD 2018 paper provides Figure 5 maps but not exact obstacle coordinates.
This file therefore recreates the two maps from the figure and implements the
described two-LiDAR recurrent obstacle-avoidance loop.
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

import numpy as np


Vec2 = np.ndarray
DRONE_WIDTH = 0.34
DRONE_RADIUS = DRONE_WIDTH / 2.0
SENSOR_FORWARD_OFFSET = DRONE_RADIUS
LIDAR_RANGE = 0.5


@dataclass(frozen=True)
class CircleObstacle:
    x: float
    y: float
    radius: float
    height: float = 1.2


@dataclass(frozen=True)
class BoxObstacle:
    x: float
    y: float
    sx: float
    sy: float
    yaw: float = 0.0
    height: float = 1.2


Obstacle = CircleObstacle | BoxObstacle


@dataclass(frozen=True)
class MapSpec:
    name: str
    size: float
    start: tuple[float, float]
    yaw: float
    obstacles: tuple[Obstacle, ...]


def deg(value: float) -> float:
    return math.radians(value)


def paper_maps() -> dict[str, MapSpec]:
    """Approximate Figure 5 maps on a 10 m x 10 m floor grid."""

    circles = (
        CircleObstacle(-4.6, -0.9, 0.48),
        CircleObstacle(-4.55, -1.75, 0.48),
        CircleObstacle(-3.8, -1.35, 0.48),
        CircleObstacle(-3.0, 3.9, 0.52),
        CircleObstacle(-2.3, 3.9, 0.52),
        CircleObstacle(-2.45, 3.05, 0.52),
        CircleObstacle(-1.75, 2.5, 0.50),
        CircleObstacle(-2.2, 1.85, 0.48),
        CircleObstacle(-2.75, 1.35, 0.48),
        CircleObstacle(-1.3, 0.0, 0.48),
        CircleObstacle(-2.9, -3.2, 0.48),
        CircleObstacle(-2.0, -3.0, 0.50),
        CircleObstacle(-1.15, -2.9, 0.50),
        CircleObstacle(1.05, 3.85, 0.52),
        CircleObstacle(1.85, 3.9, 0.52),
        CircleObstacle(1.45, 3.1, 0.52),
        CircleObstacle(1.5, 2.25, 0.50),
        CircleObstacle(1.45, 1.35, 0.50),
        CircleObstacle(1.95, 0.55, 0.50),
        CircleObstacle(3.35, 2.1, 0.48),
        CircleObstacle(4.05, 2.35, 0.48),
        CircleObstacle(4.55, 2.8, 0.48),
        CircleObstacle(4.45, -2.3, 0.48),
        CircleObstacle(2.05, -3.25, 0.48),
        CircleObstacle(1.8, -2.35, 0.48),
        CircleObstacle(2.15, -1.55, 0.48),
    )

    maze = (
        BoxObstacle(-4.9, 1.2, 0.32, 6.7, deg(90)),
        BoxObstacle(-2.95, 3.85, 0.38, 1.9),
        BoxObstacle(-3.05, -1.3, 0.38, 3.0),
        BoxObstacle(-0.55, -2.45, 0.40, 6.2, deg(90)),
        BoxObstacle(1.45, 0.2, 0.42, 3.1),
        BoxObstacle(4.35, 1.2, 0.38, 1.8, deg(90)),
        BoxObstacle(-0.95, 2.85, 0.75, 0.75, deg(20)),
        BoxObstacle(3.85, 3.75, 0.78, 0.78, deg(20)),
        BoxObstacle(-4.55, -3.95, 0.38, 1.35, deg(30)),
        BoxObstacle(-1.85, -4.2, 0.75, 0.75),
        BoxObstacle(1.1, -4.05, 0.65, 0.8, deg(18)),
    )

    return {
        "circles": MapSpec("circles", 10.0, (0.0, 0.0), deg(250), circles),
        "maze": MapSpec("maze", 10.0, (0.0, 0.0), deg(8), maze),
    }


class AdaptiveObstacleAvoidanceController:
    """Two-neuron recurrent controller with correlation plasticity.

    This follows the controller family used by Pedersen and Manoonpong:
    two discrete-time non-spiking tanh neurons, self-excitatory synapses,
    mutual inhibition, and online correlation learning with synaptic scaling.
    """

    def __init__(self, turn_gain: float = 1.35) -> None:
        self.turn_gain = turn_gain
        self.input_gain = 4.7
        self.b = np.array([2.4, 2.4], dtype=float)
        self.q = np.array([3.5, 3.5], dtype=float)
        self.output = np.array([-1.0, -1.0], dtype=float)
        self.prev_output = self.output.copy()
        self.mu_b = 0.0065
        self.mu_q = 0.015
        self.gamma_b = 0.0003
        self.gamma_q = 0.0003
        self.k = -0.01
        self.last_steering = -0.35

    def _network_step(self, inputs: np.ndarray) -> np.ndarray:
        c = -0.5 * float(self.q[0] + self.q[1])
        activity = np.array(
            [
                self.b[0] * self.output[0] + c * self.output[1] + self.input_gain * inputs[0],
                self.b[1] * self.output[1] + c * self.output[0] + self.input_gain * inputs[1],
            ]
        )
        return np.tanh(activity)

    def _plasticity_step(self, inputs: np.ndarray, dt: float) -> None:
        scale = dt * 27.0
        reflex = (inputs > -0.5).astype(float)
        v = np.clip((self.output + 1.0) * 0.5, 0.0, 1.0)
        v_prev = np.clip((self.prev_output + 1.0) * 0.5, 0.0, 1.0)

        self.b += scale * (
            self.mu_b * v_prev * v * reflex + self.gamma_b * (self.k - v) * self.b * self.b
        )
        self.q += scale * (
            self.mu_q * v_prev * v * reflex + self.gamma_q * (self.k - v) * self.q * self.q
        )

        self.b = np.clip(self.b, 0.1, 8.0)
        self.q = np.clip(self.q, 0.1, 10.0)

    def step(self, left_signal: float, right_signal: float, dt: float) -> float:
        inputs = np.array([left_signal, right_signal], dtype=float)
        self.prev_output = self.output.copy()
        self.output = self._network_step(inputs)
        self._plasticity_step(inputs, dt)

        steering = 0.5 * (self.output[0] - self.output[1])
        both_blocked = left_signal > 0.05 and right_signal > 0.05
        if both_blocked and abs(steering) < 0.08:
            steering = self.last_steering
        elif abs(steering) >= 0.08:
            self.last_steering = float(np.clip(steering, -1.0, 1.0))
        return float(np.clip(-self.turn_gain * steering, -1.35, 1.35))


def forward_speed(left_signal: float, right_signal: float) -> float:
    """Nominal paper speed with slowdown while the yaw controller avoids obstacles."""

    proximity = max(left_signal, right_signal)
    if left_signal > 0.55 and right_signal > 0.55:
        return 0.0
    if proximity > 0.25:
        return 0.025
    if proximity > -0.15:
        return 0.055
    return 0.1


def exploration_bias(elapsed: float, left_signal: float, right_signal: float) -> float:
    if max(left_signal, right_signal) > -0.25:
        return 0.0
    return 0.22 * math.sin(0.19 * elapsed) + 0.11 * math.sin(0.53 * elapsed + 1.3)


def rotate(point: Vec2, yaw: float) -> Vec2:
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([c * point[0] - s * point[1], s * point[0] + c * point[1]])


def ray_circle(origin: Vec2, direction: Vec2, obstacle: CircleObstacle, max_range: float) -> float | None:
    center = np.array([obstacle.x, obstacle.y])
    oc = origin - center
    b = 2.0 * float(np.dot(oc, direction))
    c = float(np.dot(oc, oc) - obstacle.radius * obstacle.radius)
    disc = b * b - 4.0 * c
    if disc < 0:
        return None
    root = math.sqrt(disc)
    candidates = [(-b - root) / 2.0, (-b + root) / 2.0]
    hits = [t for t in candidates if 0.0 <= t <= max_range]
    return min(hits) if hits else None


def ray_box(origin: Vec2, direction: Vec2, obstacle: BoxObstacle, max_range: float) -> float | None:
    local_origin = rotate(origin - np.array([obstacle.x, obstacle.y]), -obstacle.yaw)
    local_dir = rotate(direction, -obstacle.yaw)
    half = np.array([obstacle.sx / 2.0, obstacle.sy / 2.0])
    tmin, tmax = 0.0, max_range

    for axis in range(2):
        if abs(local_dir[axis]) < 1e-9:
            if local_origin[axis] < -half[axis] or local_origin[axis] > half[axis]:
                return None
            continue
        inv = 1.0 / local_dir[axis]
        t1 = (-half[axis] - local_origin[axis]) * inv
        t2 = (half[axis] - local_origin[axis]) * inv
        t_near, t_far = min(t1, t2), max(t1, t2)
        tmin = max(tmin, t_near)
        tmax = min(tmax, t_far)
        if tmin > tmax:
            return None
    return tmin if 0.0 <= tmin <= max_range else None


def ray_boundary(origin: Vec2, direction: Vec2, size: float, max_range: float) -> float | None:
    half = size / 2.0
    candidates: list[float] = []
    for axis in range(2):
        if abs(direction[axis]) < 1e-9:
            continue
        for wall in (-half, half):
            t = (wall - origin[axis]) / direction[axis]
            if 0.0 <= t <= max_range:
                point = origin + direction * t
                other = 1 - axis
                if -half <= point[other] <= half:
                    candidates.append(float(t))
    return min(candidates) if candidates else None


def simple_lidar(position: Vec2, yaw: float, spec: MapSpec, max_range: float) -> tuple[float, float]:
    forward = np.array([math.cos(yaw), math.sin(yaw)])
    sensor_origin = position + forward * SENSOR_FORWARD_OFFSET
    readings: list[float] = []
    for angle in (deg(20), deg(-20)):
        direction = np.array([math.cos(yaw + angle), math.sin(yaw + angle)])
        hits: list[float] = []
        boundary_hit = ray_boundary(sensor_origin, direction, spec.size, max_range)
        if boundary_hit is not None:
            hits.append(boundary_hit)
        for obstacle in spec.obstacles:
            if isinstance(obstacle, CircleObstacle):
                hit = ray_circle(sensor_origin, direction, obstacle, max_range)
            else:
                hit = ray_box(sensor_origin, direction, obstacle, max_range)
            if hit is not None:
                hits.append(hit)
        readings.append(min(hits) if hits else max_range)
    return readings[0], readings[1]


def sensor_signal(distance: float, max_range: float = 0.5, near: float = 0.2) -> float:
    if distance >= max_range:
        return -1.0
    return float(np.clip(1.0 - 2.0 * ((distance - near) / (max_range - near)), -1.0, 1.0))


def collides(position: Vec2, obstacles: Iterable[Obstacle], radius: float = DRONE_RADIUS) -> bool:
    for obstacle in obstacles:
        if isinstance(obstacle, CircleObstacle):
            if np.linalg.norm(position - np.array([obstacle.x, obstacle.y])) <= obstacle.radius + radius:
                return True
        else:
            local = rotate(position - np.array([obstacle.x, obstacle.y]), -obstacle.yaw)
            half = np.array([obstacle.sx / 2.0 + radius, obstacle.sy / 2.0 + radius])
            if np.all(np.abs(local) <= half):
                return True
    return False


def out_of_bounds(position: Vec2, size: float) -> bool:
    boundary = size / 2.0 - DRONE_RADIUS
    return bool(abs(position[0]) > boundary or abs(position[1]) > boundary)


def safe_advance(
    position: Vec2,
    yaw: float,
    speed: float,
    yaw_rate: float,
    dt: float,
    spec: MapSpec,
) -> tuple[Vec2, float]:
    new_yaw = yaw + yaw_rate * dt
    candidate = position + np.array([math.cos(new_yaw), math.sin(new_yaw)]) * speed * dt
    if out_of_bounds(candidate, spec.size) or collides(candidate, spec.obstacles):
        spin = -1.0 if yaw_rate < 0.0 else 1.0
        if abs(yaw_rate) < 0.05:
            spin = 1.0
        return position, yaw + spin * 1.25 * dt
    return candidate, new_yaw


def run_simple2d(spec: MapSpec, duration: float, dt: float) -> tuple[list[tuple[float, float]], bool]:
    controller = AdaptiveObstacleAvoidanceController()
    pos = np.array(spec.start, dtype=float)
    yaw = spec.yaw
    path = [(float(pos[0]), float(pos[1]))]
    crashed = False

    for step in range(int(duration / dt)):
        elapsed = step * dt
        left_d, right_d = simple_lidar(pos, yaw, spec, LIDAR_RANGE)
        left_signal = sensor_signal(left_d)
        right_signal = sensor_signal(right_d)
        yaw_rate = controller.step(left_signal, right_signal, dt) + exploration_bias(elapsed, left_signal, right_signal)
        pos, yaw = safe_advance(pos, yaw, forward_speed(left_signal, right_signal), yaw_rate, dt, spec)

        if out_of_bounds(pos, spec.size) or collides(pos, spec.obstacles):
            crashed = True
            break
        path.append((float(pos[0]), float(pos[1])))
    return path, crashed


def save_trace(spec: MapSpec, path: list[tuple[float, float]], output: Path) -> None:
    from PIL import Image, ImageDraw

    output.parent.mkdir(parents=True, exist_ok=True)
    image_size = 900
    margin = 32
    scale = (image_size - 2 * margin) / spec.size

    def xy(point: tuple[float, float]) -> tuple[float, float]:
        return (
            margin + (point[0] + spec.size / 2.0) * scale,
            image_size - margin - (point[1] + spec.size / 2.0) * scale,
        )

    img = Image.new("RGB", (image_size, image_size), (218, 216, 205))
    draw = ImageDraw.Draw(img)

    for i in range(11):
        v = -spec.size / 2.0 + i
        draw.line([xy((v, -spec.size / 2.0)), xy((v, spec.size / 2.0))], fill=(95, 95, 88), width=1)
        draw.line([xy((-spec.size / 2.0, v)), xy((spec.size / 2.0, v))], fill=(95, 95, 88), width=1)

    fill = (236, 160, 160)
    outline = (60, 40, 40)
    for obstacle in spec.obstacles:
        if isinstance(obstacle, CircleObstacle):
            cx, cy = xy((obstacle.x, obstacle.y))
            r = obstacle.radius * scale
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=2)
        else:
            half_points = [
                np.array([-obstacle.sx / 2.0, -obstacle.sy / 2.0]),
                np.array([obstacle.sx / 2.0, -obstacle.sy / 2.0]),
                np.array([obstacle.sx / 2.0, obstacle.sy / 2.0]),
                np.array([-obstacle.sx / 2.0, obstacle.sy / 2.0]),
            ]
            poly = [
                xy(tuple(rotate(point, obstacle.yaw) + np.array([obstacle.x, obstacle.y])))
                for point in half_points
            ]
            draw.polygon(poly, fill=fill, outline=outline)

    if len(path) > 1:
        draw.line([xy(point) for point in path], fill=(25, 38, 190), width=3)
    if path:
        sx, sy = xy(path[0])
        ex, ey = xy(path[-1])
        draw.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=(40, 180, 80))
        draw.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], fill=(200, 40, 60))

    img.save(output)


def run_pybullet(spec: MapSpec, duration: float, dt: float, gui: bool) -> tuple[list[tuple[float, float]], bool]:
    try:
        import pybullet as p
        import pybullet_data
    except ImportError as exc:
        raise SystemExit(
            "PyBullet is not installed. Run `pip install -r requirements.txt`, "
            "or use `--backend simple2d` for a dependency-free sanity run."
        ) from exc

    client = p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.resetSimulation()
    p.setGravity(0, 0, -9.81)
    p.loadURDF("plane.urdf")

    for i in range(11):
        v = -spec.size / 2.0 + i
        p.addUserDebugLine([v, -spec.size / 2.0, 0.01], [v, spec.size / 2.0, 0.01], [0.35, 0.35, 0.35])
        p.addUserDebugLine([-spec.size / 2.0, v, 0.01], [spec.size / 2.0, v, 0.01], [0.35, 0.35, 0.35])

    wall_specs = (
        BoxObstacle(0.0, -spec.size / 2.0, spec.size, 0.08, 0.0, 0.35),
        BoxObstacle(0.0, spec.size / 2.0, spec.size, 0.08, 0.0, 0.35),
        BoxObstacle(-spec.size / 2.0, 0.0, 0.08, spec.size, 0.0, 0.35),
        BoxObstacle(spec.size / 2.0, 0.0, 0.08, spec.size, 0.0, 0.35),
    )
    for wall in wall_specs:
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[wall.sx / 2.0, wall.sy / 2.0, wall.height / 2.0])
        vis = p.createVisualShape(
            p.GEOM_BOX,
            halfExtents=[wall.sx / 2.0, wall.sy / 2.0, wall.height / 2.0],
            rgbaColor=[0.35, 0.35, 0.35, 0.45],
        )
        p.createMultiBody(0, col, vis, [wall.x, wall.y, wall.height / 2.0])

    for obstacle in spec.obstacles:
        if isinstance(obstacle, CircleObstacle):
            col = p.createCollisionShape(p.GEOM_CYLINDER, radius=obstacle.radius, height=obstacle.height)
            vis = p.createVisualShape(
                p.GEOM_CYLINDER,
                radius=obstacle.radius,
                length=obstacle.height,
                rgbaColor=[0.92, 0.55, 0.55, 1.0],
            )
            p.createMultiBody(0, col, vis, [obstacle.x, obstacle.y, obstacle.height / 2.0])
        else:
            col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[obstacle.sx / 2.0, obstacle.sy / 2.0, obstacle.height / 2.0])
            vis = p.createVisualShape(
                p.GEOM_BOX,
                halfExtents=[obstacle.sx / 2.0, obstacle.sy / 2.0, obstacle.height / 2.0],
                rgbaColor=[0.92, 0.55, 0.55, 1.0],
            )
            orn = p.getQuaternionFromEuler([0, 0, obstacle.yaw])
            p.createMultiBody(0, col, vis, [obstacle.x, obstacle.y, obstacle.height / 2.0], orn)

    drone_col = p.createCollisionShape(p.GEOM_SPHERE, radius=0.17)
    drone_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.17, rgbaColor=[0.15, 0.8, 0.2, 1.0])
    drone = p.createMultiBody(0.2, drone_col, drone_vis, [spec.start[0], spec.start[1], 0.45])

    controller = AdaptiveObstacleAvoidanceController()
    pos = np.array(spec.start, dtype=float)
    yaw = spec.yaw
    path = [(float(pos[0]), float(pos[1]))]
    crashed = False

    for step in range(int(duration / dt)):
        elapsed = step * dt
        starts = []
        ends = []
        for angle in (deg(20), deg(-20)):
            d = np.array([math.cos(yaw + angle), math.sin(yaw + angle)])
            start = np.array([pos[0], pos[1], 0.45])
            start[:2] += np.array([math.cos(yaw), math.sin(yaw)]) * SENSOR_FORWARD_OFFSET
            end = start + np.array([d[0], d[1], 0.0]) * LIDAR_RANGE
            starts.append(start.tolist())
            ends.append(end.tolist())

        results = p.rayTestBatch(starts, ends)
        distances = [LIDAR_RANGE if r[0] < 0 else LIDAR_RANGE * r[2] for r in results]
        left_signal = sensor_signal(distances[0])
        right_signal = sensor_signal(distances[1])
        yaw_rate = controller.step(left_signal, right_signal, dt) + exploration_bias(elapsed, left_signal, right_signal)
        pos, yaw = safe_advance(pos, yaw, forward_speed(left_signal, right_signal), yaw_rate, dt, spec)

        orn = p.getQuaternionFromEuler([0, 0, yaw])
        p.resetBasePositionAndOrientation(drone, [pos[0], pos[1], 0.45], orn)
        p.addUserDebugLine([path[-1][0], path[-1][1], 0.04], [pos[0], pos[1], 0.04], [0.05, 0.05, 0.9], lifeTime=0)
        p.stepSimulation()

        if out_of_bounds(pos, spec.size) or collides(pos, spec.obstacles):
            crashed = True
            break
        path.append((float(pos[0]), float(pos[1])))

    if not gui:
        p.disconnect(client)
    return path, crashed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=paper_maps().keys(), default="maze")
    parser.add_argument("--backend", choices=["pybullet", "simple2d"], default="pybullet")
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--dt", type=float, default=1.0 / 60.0)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("output/trace.png"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = paper_maps()[args.env]

    if args.backend == "simple2d":
        path, crashed = run_simple2d(spec, args.duration, args.dt)
    else:
        path, crashed = run_pybullet(spec, args.duration, args.dt, args.gui)

    save_trace(spec, path, args.output)
    status = "crashed" if crashed else "completed"
    print(f"{status}: env={spec.name} steps={len(path)} output={os.fspath(args.output)}")


if __name__ == "__main__":
    main()

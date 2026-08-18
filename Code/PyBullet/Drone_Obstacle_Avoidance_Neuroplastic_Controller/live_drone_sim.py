"""Live PyBullet viewer for the paper obstacle-avoidance simulation.

This script animates the reconstructed paper maps. It uses PyBullet directly
for the live 3D scene, while keeping the controller and map definitions shared
with paper_drone_sim.py.
"""

from __future__ import annotations

import argparse
import math
import time

import numpy as np

from paper_drone_sim import (
    DRONE_RADIUS,
    LIDAR_RANGE,
    SENSOR_FORWARD_OFFSET,
    AdaptiveObstacleAvoidanceController,
    BoxObstacle,
    CircleObstacle,
    collides,
    deg,
    forward_speed,
    out_of_bounds,
    paper_maps,
    sensor_signal,
)


class ReactiveRightAvoider:
    """Go straight until detection, then make one clean right turn."""

    def __init__(self) -> None:
        self.mode = "straight"
        self.target_yaw = 0.0
        self.cooldown = 0.0

    @staticmethod
    def _angle_error(target: float, current: float) -> float:
        return math.atan2(math.sin(target - current), math.cos(target - current))

    def step(self, yaw: float, left_signal: float, right_signal: float, dt: float) -> tuple[float, float]:
        self.cooldown = max(0.0, self.cooldown - dt)
        detected = max(left_signal, right_signal) > -0.35

        if self.mode == "straight" and detected and self.cooldown <= 0.0:
            self.mode = "turn_right"
            self.target_yaw = yaw - math.pi / 2.0

        if self.mode == "turn_right":
            error = self._angle_error(self.target_yaw, yaw)
            if abs(error) < deg(4):
                self.mode = "straight"
                self.cooldown = 1.2
                return 0.0, 0.1
            return -1.35, 0.0

        return 0.0, 0.1


class PaperLikeAvoider:
    """Controller path that follows the paper's described neural yaw interface."""

    def __init__(self) -> None:
        self.controller = AdaptiveObstacleAvoidanceController(turn_gain=2.25)
        self.mode = "drive"
        self.target_yaw = 0.0
        self.cooldown = 0.0

    @staticmethod
    def _angle_error(target: float, current: float) -> float:
        return math.atan2(math.sin(target - current), math.cos(target - current))

    def step(self, yaw: float, left_signal: float, right_signal: float, dt: float) -> tuple[float, float]:
        # Always update the neuroplastic network, including during a safety turn.
        yaw_rate = self.controller.step(left_signal, right_signal, dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        # sensor_signal is -1 only when the ray sees nothing in its 0.5 m
        # range.  Act on the first one-sided hit instead of waiting until the
        # obstacle is close enough to create a curved approach path.
        one_side_is_closer = abs(left_signal - right_signal) > 0.02
        detected = max(left_signal, right_signal) > -0.98

        if self.mode == "drive" and detected and one_side_is_closer and self.cooldown == 0.0:
            # A high left reading means the obstacle is left of the nose, so
            # turn right; a high right reading gives the opposite turn.
            turn_right = left_signal > right_signal
            self.target_yaw = yaw + (-math.pi / 2.0 if turn_right else math.pi / 2.0)
            self.mode = "turn_away"

        if self.mode == "turn_away":
            error = self._angle_error(self.target_yaw, yaw)
            if abs(error) < deg(3):
                self.mode = "drive"
                self.cooldown = 0.8
                return 0.0, 0.055
            return (1.65 if error > 0.0 else -1.65), 0.0

        speed = forward_speed(left_signal, right_signal)
        if max(left_signal, right_signal) > 0.05:
            speed = 0.0
            if abs(yaw_rate) < 0.25:
                yaw_rate = -0.9 if left_signal >= right_signal else 0.9
        return yaw_rate, speed


def require_pybullet():
    try:
        import pybullet as p
        import pybullet_data
    except ImportError as exc:
        raise SystemExit(
            "PyBullet is not installed yet.\n\n"
            "From Command Prompt, run:\n"
            'cd /d "C:\\Users\\work\\OneDrive\\Documents\\drones\\neuroplasticity_controller_version"\n'
            'py -3.12 -m pip install pybullet numpy\n\n'
            "Then run this script again."
        ) from exc
    return p, pybullet_data


def add_box(p, obstacle: BoxObstacle, rgba=(0.92, 0.55, 0.55, 1.0)) -> None:
    col = p.createCollisionShape(
        p.GEOM_BOX,
        halfExtents=[obstacle.sx / 2.0, obstacle.sy / 2.0, obstacle.height / 2.0],
    )
    vis = p.createVisualShape(
        p.GEOM_BOX,
        halfExtents=[obstacle.sx / 2.0, obstacle.sy / 2.0, obstacle.height / 2.0],
        rgbaColor=rgba,
    )
    orn = p.getQuaternionFromEuler([0, 0, obstacle.yaw])
    p.createMultiBody(0, col, vis, [obstacle.x, obstacle.y, obstacle.height / 2.0], orn)


def add_circle(p, obstacle: CircleObstacle) -> None:
    col = p.createCollisionShape(p.GEOM_CYLINDER, radius=obstacle.radius, height=obstacle.height)
    vis = p.createVisualShape(
        p.GEOM_CYLINDER,
        radius=obstacle.radius,
        length=obstacle.height,
        rgbaColor=[0.92, 0.55, 0.55, 1.0],
    )
    p.createMultiBody(0, col, vis, [obstacle.x, obstacle.y, obstacle.height / 2.0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=paper_maps().keys(), default="maze")
    parser.add_argument("--controller", choices=["paper", "right90"], default="paper")
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier.")
    parser.add_argument("--show-neurons", action="store_true", help="Print two-neuron controller state.")
    args = parser.parse_args()

    p, pybullet_data = require_pybullet()
    spec = paper_maps()[args.env]

    p.connect(p.GUI)
    p.resetSimulation()
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.setTimeStep(1.0 / 60.0)
    p.loadURDF("plane.urdf")
    p.resetDebugVisualizerCamera(
        cameraDistance=8.5,
        cameraYaw=0,
        cameraPitch=-68,
        cameraTargetPosition=[0, 0, 0],
    )

    for i in range(11):
        v = -spec.size / 2.0 + i
        p.addUserDebugLine([v, -spec.size / 2.0, 0.015], [v, spec.size / 2.0, 0.015], [0.35, 0.35, 0.35])
        p.addUserDebugLine([-spec.size / 2.0, v, 0.015], [spec.size / 2.0, v, 0.015], [0.35, 0.35, 0.35])

    for obstacle in spec.obstacles:
        if isinstance(obstacle, CircleObstacle):
            add_circle(p, obstacle)
        else:
            add_box(p, obstacle)

    half = spec.size / 2.0
    for wall in (
        BoxObstacle(0.0, -half, spec.size, 0.08, 0.0, 0.35),
        BoxObstacle(0.0, half, spec.size, 0.08, 0.0, 0.35),
        BoxObstacle(-half, 0.0, 0.08, spec.size, 0.0, 0.35),
        BoxObstacle(half, 0.0, 0.08, spec.size, 0.0, 0.35),
    ):
        add_box(p, wall, rgba=(0.25, 0.25, 0.25, 0.45))

    drone_col = p.createCollisionShape(p.GEOM_SPHERE, radius=DRONE_RADIUS)
    drone_vis = p.createVisualShape(p.GEOM_SPHERE, radius=DRONE_RADIUS, rgbaColor=[0.1, 0.8, 0.2, 1.0])
    drone = p.createMultiBody(0.2, drone_col, drone_vis, [spec.start[0], spec.start[1], 0.45])

    arm_len = 0.34
    controller = PaperLikeAvoider() if args.controller == "paper" else ReactiveRightAvoider()
    pos = np.array(spec.start, dtype=float)
    yaw = spec.yaw
    dt = 1.0 / 60.0
    last = time.time()

    for step in range(int(args.duration / dt)):
        forward = np.array([math.cos(yaw), math.sin(yaw)])
        sensor_origin = pos + forward * SENSOR_FORWARD_OFFSET

        starts = []
        ends = []
        for angle in (deg(20), deg(-20)):
            d = np.array([math.cos(yaw + angle), math.sin(yaw + angle)])
            start = np.array([sensor_origin[0], sensor_origin[1], 0.45])
            end = start + np.array([d[0], d[1], 0.0]) * LIDAR_RANGE
            starts.append(start.tolist())
            ends.append(end.tolist())

        results = p.rayTestBatch(starts, ends)
        distances = [LIDAR_RANGE if r[0] < 0 else LIDAR_RANGE * r[2] for r in results]
        left_signal = sensor_signal(distances[0])
        right_signal = sensor_signal(distances[1])

        yaw_rate, speed = controller.step(yaw, left_signal, right_signal, dt)
        if args.show_neurons and args.controller == "paper" and step % 60 == 0:
            neural = controller.controller
            print(
                "O=[{:.2f},{:.2f}] b=[{:.2f},{:.2f}] c={:.2f} I=[{:.2f},{:.2f}]".format(
                    neural.output[0],
                    neural.output[1],
                    neural.b[0],
                    neural.b[1],
                    -0.5 * float(neural.q[0] + neural.q[1]),
                    left_signal,
                    right_signal,
                )
            )
        new_yaw = yaw + yaw_rate * dt
        candidate = pos + np.array([math.cos(new_yaw), math.sin(new_yaw)]) * speed * dt

        if out_of_bounds(candidate, spec.size) or collides(candidate, spec.obstacles, radius=DRONE_RADIUS + 0.06):
            # Preserve the selected turn direction instead of always rotating
            # clockwise, which could steer a right-side detection into a wall.
            recovery_rate = yaw_rate if abs(yaw_rate) > 0.1 else -1.35
            new_yaw = yaw + recovery_rate * dt
            candidate = pos

        old = pos.copy()
        pos = candidate
        yaw = new_yaw

        orn = p.getQuaternionFromEuler([0, 0, yaw])
        p.resetBasePositionAndOrientation(drone, [pos[0], pos[1], 0.45], orn)

        nose = pos + np.array([math.cos(yaw), math.sin(yaw)]) * arm_len
        left = pos + np.array([math.cos(yaw + math.pi / 2), math.sin(yaw + math.pi / 2)]) * arm_len
        right = pos + np.array([math.cos(yaw - math.pi / 2), math.sin(yaw - math.pi / 2)]) * arm_len
        p.addUserDebugLine([old[0], old[1], 0.05], [pos[0], pos[1], 0.05], [0.05, 0.05, 0.9], lifeTime=0)
        p.addUserDebugLine([pos[0], pos[1], 0.47], [nose[0], nose[1], 0.47], [0, 0, 0], lifeTime=dt * 2)
        p.addUserDebugLine([left[0], left[1], 0.47], [right[0], right[1], 0.47], [0, 0, 0], lifeTime=dt * 2)
        for i, result in enumerate(results):
            ray_end = ends[i] if result[0] < 0 else result[3]
            color = [1, 0, 1] if result[0] < 0 else [1, 0, 0]
            p.addUserDebugLine(starts[i], ray_end, color, lifeTime=dt * 2)

        p.stepSimulation()
        delay = max(0.0, dt / max(args.speed, 0.1) - (time.time() - last))
        time.sleep(delay)
        last = time.time()

    print("Simulation finished. Close the PyBullet window when done.")


if __name__ == "__main__":
    main()

"""Main Entry Point - Arduino Quadcopter Obstacle Avoidance Simulation Server.

Orchestrates:
1. 30 Hz 6-DOF Quadcopter Physics & Sensor Raycasting.
2. Devos et al. (2018) Adaptive Neural Controller with Synaptic Plasticity.
3. Human-in-the-Loop Decision & Safety Verification Engine.
4. Experiment Logging with CSV/JSON Export.
5. Async Web Server (aiohttp) serving the 3D Dashboard and WebSocket Stream.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Set, Dict, Any, Optional

from aiohttp import web

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from avoidance.neural_controller import AdaptiveNeuralController
from avoidance.decision_engine import DecisionEngine, FlightState, DirectionCategory
from sensors.lidar_sensor import SensorSuite
from simulation.drone_physics import DronePhysics
from simulation.scenarios import get_all_scenarios, ScenarioDefinition
from simulation.experiment_logger import ExperimentLogger, ExperimentTrialRecord
from arduino.serial_bridge import ArduinoSerialBridge


class SimulationManager:
    """Coordinates physics, sensors, neural controller, and user decisions."""

    def __init__(self) -> None:
        self.scenarios = get_all_scenarios()
        self.current_scenario_id = "front_obstacle"
        self.active_scenario: ScenarioDefinition = self.scenarios[self.current_scenario_id]

        self.physics = DronePhysics()
        self.sensor_suite = SensorSuite()
        self.neural_controller = AdaptiveNeuralController()
        self.decision_engine = DecisionEngine()
        self.logger = ExperimentLogger(os.path.join(PROJECT_ROOT, "logs"))
        self.serial_bridge = ArduinoSerialBridge()

        self.sim_speed = 1.0
        self.is_running = False
        self.elapsed_time = 0.0

        # Pilot Modes: 'AUTONOMOUS' vs 'MANUAL'
        self.flight_mode = "AUTONOMOUS"
        self.collision_assist = True
        self.manual_vx = 0.0
        self.manual_vy = 0.0
        self.manual_vz = 0.0
        self.manual_yaw_rate = 0.0

        # Try connecting physical Arduino if available
        self.serial_bridge.connect()

        # Load initial scenario
        self.load_scenario(self.current_scenario_id)

    def set_flight_mode(self, mode: str) -> None:
        """Switches between Autonomous research cruise and live Manual pilot mode."""
        self.flight_mode = "MANUAL" if mode.upper() == "MANUAL" else "AUTONOMOUS"
        if self.flight_mode == "MANUAL":
            self.decision_engine.state = FlightState.MANUAL_PILOT
            self.is_running = True
        else:
            self.decision_engine.state = FlightState.HOLD_POSITION
            self.physics.set_directional_velocity("HOVER")

    def set_collision_assist(self, enabled: bool) -> None:
        """Toggles active collision prevention brake during manual pilot flight."""
        self.collision_assist = bool(enabled)

    def set_manual_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float) -> None:
        """Receives live velocity commands from manual keyboard/joystick inputs."""
        self.manual_vx = float(vx)
        self.manual_vy = float(vy)
        self.manual_vz = float(vz)
        self.manual_yaw_rate = float(yaw_rate)
        if self.flight_mode == "MANUAL":
            self.is_running = True

    def load_scenario(self, scenario_id: str) -> bool:
        if scenario_id not in self.scenarios:
            return False

        self.current_scenario_id = scenario_id
        self.active_scenario = self.scenarios[scenario_id]

        # Reset components
        pos = self.active_scenario.initial_drone_pos
        yaw = self.active_scenario.initial_drone_yaw
        self.physics.reset(pos[0], pos[1], pos[2], yaw)
        self.neural_controller.reset()
        self.decision_engine.reset()

        self.is_running = False
        return True

    def start(self) -> None:
        self.is_running = True
        if self.decision_engine.state in (FlightState.IDLE, FlightState.HOLD_POSITION, FlightState.MANEUVER_COMPLETE):
            self.decision_engine.state = FlightState.CRUISING

    def pause(self) -> None:
        self.is_running = False
        if self.decision_engine.state == FlightState.CRUISING:
            self.decision_engine.state = FlightState.HOLD_POSITION
        self.physics.set_directional_velocity("HOVER")

    def reset(self) -> None:
        self.load_scenario(self.current_scenario_id)

    def emergency_stop(self) -> None:
        self.is_running = False
        self.decision_engine.state = FlightState.EMERGENCY_STOPPED
        self.physics.set_directional_velocity("STOP")
        self.serial_bridge.emergency_stop()

    def set_speed(self, speed: float) -> None:
        self.sim_speed = max(0.2, min(5.0, float(speed)))

    def submit_user_decision(self, direction: str) -> Dict[str, Any]:
        accepted, msg, details = self.decision_engine.submit_user_decision(
            direction,
            (self.physics.state.x, self.physics.state.y, self.physics.state.z),
            self.elapsed_time,
        )

        if accepted:
            if direction in ("HOVER", "STOP"):
                self.physics.set_directional_velocity(direction)
            else:
                self.physics.set_directional_velocity(direction, speed_scale=1.2)
                self.is_running = True
            return {"accepted": True, "message": msg, "details": details}
        else:
            return {"accepted": False, "message": msg, "details": details}

    def set_override_mode(self, enabled: bool) -> None:
        self.decision_engine.override_mode = bool(enabled)

    def step(self, dt: float) -> Dict[str, Any]:
        scaled_dt = dt * self.sim_speed
        self.elapsed_time += scaled_dt

        # 1. Read sensors
        sensors = self.sensor_suite.read_all(
            self.physics.state.x,
            self.physics.state.y,
            self.physics.state.z,
            self.physics.state.yaw,
            self.active_scenario.obstacles,
        )

        # 2. Step Devos et al. (2018) Adaptive Neural Controller
        d_left = sensors["lidar_left"].distance
        d_right = sensors["lidar_right"].distance
        yaw_rate_cmd, fwd_speed_cmd, neural_telem = self.neural_controller.step(d_left, d_right, scaled_dt)

        # 3. Handle flight states and Human-in-the-Loop decision trigger
        event_to_broadcast: Optional[Dict[str, Any]] = None

        if self.is_running:
            if self.flight_mode == "MANUAL":
                self.decision_engine.state = FlightState.MANUAL_PILOT
                vx = self.manual_vx
                vy = self.manual_vy
                vz = self.manual_vz
                yaw_rate = self.manual_yaw_rate

                # Active collision prevention brake if enabled
                if self.collision_assist:
                    crit = self.decision_engine.critical_dist
                    min_fwd = min(sensors["lidar_left"].distance, sensors["lidar_right"].distance, sensors["FORWARD"].distance)
                    if vx > 0 and min_fwd < crit:
                        vx = 0.0  # Brake forward motion
                    if vx < 0 and sensors["BACKWARD"].distance < crit:
                        vx = 0.0  # Brake reverse motion
                    if vy > 0 and sensors["LEFT"].distance < crit:
                        vy = 0.0  # Brake left motion
                    if vy < 0 and sensors["RIGHT"].distance < crit:
                        vy = 0.0  # Brake right motion
                    if vz > 0 and sensors["UP"].distance < crit:
                        vz = 0.0  # Brake climb
                    if vz < 0 and sensors["DOWN"].distance < crit:
                        vz = 0.0  # Brake descent

                self.physics.set_manual_control(vx, vy, vz, yaw_rate)

            elif self.decision_engine.state == FlightState.CRUISING:
                # Forward motion governed by base-paper velocity
                self.physics.set_autonomous_control(fwd_speed_cmd, yaw_rate_cmd)

                # Check if obstacle triggered
                hit_event = self.decision_engine.check_detection_trigger(
                    sensors,
                    (self.physics.state.x, self.physics.state.y, self.physics.state.z),
                    self.elapsed_time,
                    yaw_rate_cmd,
                )

                if hit_event is not None:
                    if self.decision_engine.auto_avoid_safest_path and self.decision_engine.active_maneuver:
                        # Immediately steer along safest path!
                        self.physics.set_directional_velocity(self.decision_engine.active_maneuver, speed_scale=1.2)
                    else:
                        # Obstacle detected -> HOLD HOVER and wait for user decision
                        self.physics.set_directional_velocity("HOVER")

                    event_to_broadcast = {
                        "type": "obstacle_detected",
                        "data": {
                            "event_id": hit_event.event_id,
                            "trigger_sensor": hit_event.trigger_sensor,
                            "trigger_distance": hit_event.trigger_distance,
                            "safest_path": hit_event.user_choice or self.decision_engine.active_maneuver or "RIGHT",
                            "auto_avoid": self.decision_engine.auto_avoid_safest_path,
                            "evaluations": {k: v.to_dict() for k, v in hit_event.evaluations.items()},
                        },
                    }

            elif self.decision_engine.state == FlightState.EXECUTING_AVOIDANCE:
                # Actively execute the avoidance maneuver along the safest path!
                if self.decision_engine.active_maneuver:
                    self.physics.set_directional_velocity(self.decision_engine.active_maneuver, speed_scale=1.2)

            elif self.decision_engine.state == FlightState.WAITING_FOR_USER:
                # Hold safe hover
                self.physics.set_directional_velocity("HOVER")

            elif self.decision_engine.state == FlightState.MANEUVER_COMPLETE:
                # Avoidance complete, resume cruising!
                self.decision_engine.state = FlightState.CRUISING
                self.physics.set_autonomous_control(fwd_speed_cmd, yaw_rate_cmd)

            # 4. Integrate 6-DOF physics
            self.physics.step(scaled_dt, self.active_scenario.obstacles, self.sensor_suite.arena_size)

            # 5. Check state machine updates (completion, collision, timeout)
            min_dist = min(s.distance for s in sensors.values())
            completed_event = self.decision_engine.update(
                scaled_dt,
                (self.physics.state.x, self.physics.state.y, self.physics.state.z),
                min_dist,
                self.physics.state.has_collided,
            )

            if completed_event is not None:
                # Record to experiment logger
                trial_record = ExperimentTrialRecord(
                    trial_id=completed_event.event_id,
                    scenario_id=self.current_scenario_id,
                    scenario_name=self.active_scenario.name,
                    timestamp=self.elapsed_time,
                    initial_pos=self.active_scenario.initial_drone_pos,
                    trigger_sensor=completed_event.trigger_sensor,
                    trigger_distance_m=completed_event.trigger_distance,
                    sensor_snapshot={k: v.distance for k, v in sensors.items()},
                    available_directions=list(completed_event.evaluations.keys()),
                    user_selected_direction=completed_event.user_choice or "NONE",
                    executed_maneuver=completed_event.user_choice or "NONE",
                    override_applied=completed_event.override_applied,
                    final_pos=(self.physics.state.x, self.physics.state.y, self.physics.state.z),
                    has_collided=self.physics.state.has_collided,
                    collision_object=self.physics.state.collision_object_id,
                    response_time_sec=completed_event.response_time_sec,
                    avoidance_duration_sec=completed_event.avoidance_duration_sec,
                    min_clearance_m=completed_event.min_clearance_observed,
                    result_status=completed_event.outcome or "UNKNOWN",
                )
                self.logger.record_trial(trial_record)

                event_to_broadcast = {
                    "type": "trial_completed",
                    "data": trial_record.to_dict(),
                }

        # Format complete telemetry snapshot
        telem_data = {
            "elapsed_time": round(self.elapsed_time, 2),
            "sim_speed": self.sim_speed,
            "pilot_mode": self.flight_mode,
            "collision_assist": self.collision_assist,
            "drone": self.physics.state.to_dict(),
            "decision": {
                "state": self.decision_engine.state.value,
                "override_mode": self.decision_engine.override_mode,
                "active_maneuver": self.decision_engine.active_maneuver,
                "auto_avoid": self.decision_engine.auto_avoid_safest_path,
            },
            "sensors": {
                k: {
                    "name": v.direction_name,
                    "distance": round(v.distance, 3),
                    "relative_angle_deg": v.relative_angle_deg,
                    "hit_point": [round(p, 3) for p in v.hit_point] if v.hit_point else None,
                    "obstacle_id": v.obstacle_id,
                }
                for k, v in sensors.items()
            },
            "neural": neural_telem.to_dict(),
            "trajectory": self.physics.trajectory_history[-100:],
        }

        return {"telem": telem_data, "event": event_to_broadcast}


# --- Web Server & WebSocket Hub ---

class SimulationServer:
    def __init__(self, sim_manager: SimulationManager, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.sim = sim_manager
        self.host = host
        self.port = port
        self.app = web.Application()
        self.active_websockets: Set[web.WebSocketResponse] = set()

        self.setup_routes()

    def setup_routes(self) -> None:
        self.app.router.add_get("/ws", self.websocket_handler)
        self.app.router.add_get("/api/scenarios", self.api_get_scenarios)
        self.app.router.add_get("/api/logs/json", self.api_get_logs_json)
        self.app.router.add_get("/api/logs/csv", self.api_get_logs_csv)
        self.app.router.add_get("/presentation.pdf", self.serve_presentation_pdf)
        self.app.router.add_get("/presentation.pptx", self.serve_presentation_pptx)

        dashboard_dir = os.path.join(PROJECT_ROOT, "dashboard")
        self.app.router.add_static("/css", os.path.join(dashboard_dir, "css"))
        self.app.router.add_static("/js", os.path.join(dashboard_dir, "js"))
        self.app.router.add_get("/", self.serve_index)

    async def serve_index(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(os.path.join(PROJECT_ROOT, "dashboard", "index.html"))

    async def serve_presentation_pdf(self, request: web.Request) -> web.FileResponse:
        pdf_path = os.path.join(PROJECT_ROOT, "autonomous_quadcopter_obstacle_avoidance_presentation.pdf")
        return web.FileResponse(pdf_path, headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": "inline; filename=autonomous_quadcopter_obstacle_avoidance_presentation.pdf"
        })

    async def serve_presentation_pptx(self, request: web.Request) -> web.FileResponse:
        pptx_path = os.path.join(PROJECT_ROOT, "autonomous_quadcopter_obstacle_avoidance_presentation.pptx")
        return web.FileResponse(pptx_path, headers={
            "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "Content-Disposition": "attachment; filename=autonomous_quadcopter_obstacle_avoidance_presentation.pptx"
        })

    async def api_get_scenarios(self, request: web.Request) -> web.Response:
        data = {k: v.to_dict() for k, v in self.sim.scenarios.items()}
        return web.json_response(data)

    async def api_get_logs_json(self, request: web.Request) -> web.Response:
        json_str = self.sim.logger.export_json()
        return web.Response(text=json_str, content_type="application/json")

    async def api_get_logs_csv(self, request: web.Request) -> web.Response:
        csv_str = self.sim.logger.export_csv()
        return web.Response(
            text=csv_str,
            content_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=experiment_history.csv"},
        )

    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=20.0)
        await ws.prepare(request)
        self.active_websockets.add(ws)

        # Send initial scenario list and loaded scenario
        await ws.send_json({
            "type": "scenarios_list",
            "data": {k: v.to_dict() for k, v in self.sim.scenarios.items()},
        })
        await ws.send_json({
            "type": "scenario_loaded",
            "data": self.sim.active_scenario.to_dict(),
        })

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_client_msg(ws, data)
                    except Exception as e:
                        print("Error handling client ws msg:", e)
        finally:
            self.active_websockets.discard(ws)

        return ws

    async def handle_client_msg(self, ws: web.WebSocketResponse, data: Dict[str, Any]) -> None:
        msg_type = data.get("type")

        if msg_type == "start_sim":
            self.sim.start()
        elif msg_type == "pause_sim":
            self.sim.pause()
        elif msg_type == "reset_sim":
            self.sim.reset()
            await self.broadcast({
                "type": "scenario_loaded",
                "data": self.sim.active_scenario.to_dict(),
            })
        elif msg_type == "emergency_stop":
            self.sim.emergency_stop()
        elif msg_type == "set_speed":
            self.sim.set_speed(data.get("speed", 1.0))
        elif msg_type == "load_scenario":
            sc_id = data.get("scenario_id")
            if sc_id and self.sim.load_scenario(sc_id):
                await self.broadcast({
                    "type": "scenario_loaded",
                    "data": self.sim.active_scenario.to_dict(),
                })
        elif msg_type == "user_decision":
            dir_chosen = data.get("direction", "HOVER")
            res = self.sim.submit_user_decision(dir_chosen)
            if res["accepted"]:
                await self.broadcast({
                    "type": "decision_accepted",
                    "data": res,
                })
            else:
                await ws.send_json({
                    "type": "decision_rejected",
                    "data": res,
                })
        elif msg_type == "set_flight_mode":
            mode = data.get("mode", "AUTONOMOUS")
            self.sim.set_flight_mode(mode)
            await self.broadcast({
                "type": "flight_mode_changed",
                "mode": self.sim.flight_mode,
            })
        elif msg_type == "set_collision_assist":
            self.sim.set_collision_assist(data.get("enabled", True))
        elif msg_type == "manual_velocity":
            self.sim.set_manual_velocity(
                data.get("vx", 0.0),
                data.get("vy", 0.0),
                data.get("vz", 0.0),
                data.get("yaw_rate", 0.0),
            )
        elif msg_type == "set_override_mode":
            self.sim.set_override_mode(data.get("enabled", False))
        elif msg_type == "set_auto_avoid":
            self.sim.decision_engine.auto_avoid_safest_path = bool(data.get("enabled", True))
            await self.broadcast({
                "type": "auto_avoid_changed",
                "enabled": self.sim.decision_engine.auto_avoid_safest_path,
            })
        elif msg_type == "get_history":
            await ws.send_json({
                "type": "history_data",
                "data": {
                    "summary": self.sim.logger.get_summary_metrics(),
                    "trials": [t.to_dict() for t in self.sim.logger.trials],
                },
            })

    async def broadcast(self, data: Dict[str, Any]) -> None:
        if not self.active_websockets:
            return
        dead = []
        for ws in self.active_websockets:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_websockets.discard(ws)

    async def run_simulation_loop(self) -> None:
        """30 Hz simulation clock (~33 ms)."""
        dt = 0.033
        while True:
            t0 = time.time()
            step_output = self.sim.step(dt)

            # Broadcast high-rate telemetry
            if self.active_websockets:
                await self.broadcast({
                    "type": "state_update",
                    "data": step_output["telem"],
                })

                # Broadcast events (obstacle detected, trial completed)
                if step_output.get("event"):
                    await self.broadcast(step_output["event"])

            elapsed = time.time() - t0
            sleep_time = max(0.005, dt - elapsed)
            await asyncio.sleep(sleep_time)


async def main() -> None:
    sim_manager = SimulationManager()
    server = SimulationServer(sim_manager, host="0.0.0.0", port=8080)

    # Start simulation loop in background task
    asyncio.create_task(server.run_simulation_loop())

    runner = web.AppRunner(server.app)
    await runner.setup()
    site = web.TCPSite(runner, server.host, server.port)
    await site.start()

    print(f"===========================================================")
    print(f" AERODRONE AI - Simulation Dashboard Online")
    print(f" URL: http://localhost:{server.port}")
    print(f" Base Paper: Devos et al. (2018) IEEE DSD 2018")
    print(f"===========================================================")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulation server stopped gracefully.")

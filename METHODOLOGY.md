# Research Methodology & System Architecture

**Base Paper:**  
*Development of Autonomous Drones for Adaptive Obstacle Avoidance in Real World Environments*  
Arne Devos, Emad Ebeid, Poramate Manoonpong (2018), *IEEE 21st Euromicro Conference on Digital System Design (DSD)*, pp. 707–710.  
DOI: [10.1109/DSD.2018.00114](https://ieeexplore.ieee.org/document/8491889)

**Theoretical Foundation:**  
*Neural Control and Synaptic Plasticity for Adaptive Obstacle Avoidance of Autonomous Drones*  
Christian K. Pedersen, Poramate Manoonpong (2018), *Lecture Notes in Computer Science / Artificial Intelligence (LNAI)*.

---

## 1. Executive Summary & Objective

Autonomous quadcopters navigating in unknown real-world environments encounter walls, sharp corners, obstacles, and dead-end corridors. Traditional solutions rely on computationally intensive computer vision (SLAM, optical flow, deep CNNs) requiring heavy compute platforms (GPUs, full SBCs) that consume excessive electrical power and reduce drone flight endurance.

The objective of the base paper and this simulation platform is to implement and validate a **computationally lightweight, bio-inspired adaptive neural obstacle avoidance system** using minimal sensing hardware (dual LiDAR / ultrasonic sensors) interfaced with an Arduino / ArduPilot / Pixhawk flight controller. 

This project extends the paper's methodology into a **complete interactive 3D simulation and telemetry dashboard** where human operators can observe autonomous exploration, inspect real-time sensor streams, and execute user-driven avoidance decisions in 10 directions (Horizontal, Diagonal, Vertical, Hover) with automatic safety verification against mathematical clearance bounds.

---

## 2. Mathematical Formulations from the Base Paper

### 2.1 Sensor Geometry and Minimum Detectable Obstacle Width

The base paper uses two LiDAR sensors mounted at the front of the quadcopter with an angular separation $\Theta$. The sensors are placed to ensure full frontal coverage without blind spots while maintaining a safe clearance margin $L_m$ around the drone's physical radius $L_d / 2$.

The minimum detectable obstacle width $W_{\text{obj}}$ is given by Equation (1) from Devos et al.:

$$W_{\text{obj}} \ge 2 \tan\left(\frac{\Theta}{2}\right) \left(L_x + \frac{L_d}{2}\right)$$

Where:
- $W_{\text{obj}}$: Minimum detectable obstacle width (m)
- $\Theta$: Angular separation between LiDAR beams ($40^\circ = 0.6981\text{ rad}$)
- $L_x$: Distance between drone front and obstacle at which turn is initiated ($0.15\text{ m} = 15\text{ cm}$)
- $L_d$: Drone physical width including rotor arm span ($0.34\text{ m} = 34\text{ cm}$)
- $L_m$: Safety margin ($0.06\text{ m} = 6\text{ cm}$)
- $L_s$: Maximum LiDAR sensing range ($0.50\text{ m} = 50\text{ cm}$)

**Analytical Derivation for Turning Distance $L_x = 0.15\text{ m}$:**
$$\frac{\Theta}{2} = 20^\circ \implies \tan(20^\circ) \approx 0.36397$$
$$L_x + \frac{L_d}{2} = 0.15 + 0.17 = 0.32\text{ m}$$
$$W_{\text{obj}} \ge 2 \times 0.36397 \times 0.32 = 0.2329\text{ m} \approx 24\text{ cm}$$

Hence, all obstacles in the environment with a cross-section $\ge 24\text{ cm}$ are guaranteed to be detected before the drone approaches closer than $15\text{ cm}$.

---

### 2.2 Sensory Normalization

The raw LiDAR/ultrasonic distance readings $d_L, d_R \in [d_{\text{min}}, d_{\text{max}}]$ (where $d_{\text{min}} = 0.15\text{ m}$, $d_{\text{max}} = 0.50\text{ m}$) are mapped to the normalized input range $S_L, S_R \in [-1, +1]$:

$$S_i = \text{clip}\left( \frac{2 \times (d_{\text{max}} - d_i)}{d_{\text{max}} - d_{\text{min}}} - 1.0, -1.0, 1.0 \right)$$

- $S_i = -1.0$: No obstacle detected within the sensing horizon ($d_i \ge L_s = 0.50\text{ m}$).
- $S_i = +1.0$: Critical obstacle proximity ($d_i \le 0.15\text{ m}$ - $0.20\text{ m}$).

---

### 2.3 Recurrent Neural Network (RNN) Controller

The core control network consists of two discrete-time non-spiking neurons with hyperbolic tangent ($\tanh$) nonlinear activation functions, self-excitatory recurrent synapses, and mutual inhibitory cross-connections:

$$\begin{aligned}
O_1(t) &= \tanh\left( b_1(t) O_1(t-1) + c(t) O_2(t-1) + I_g S_L(t) \right) \\
O_2(t) &= \tanh\left( b_2(t) O_2(t-1) + c(t) O_1(t-1) + I_g S_R(t) \right)
\end{aligned}$$

Where:
- $O_1(t), O_2(t) \in (-1, +1)$: Outputs of left and right steering neurons.
- $O_1(t-1), O_2(t-1)$: Prior neural states providing short-term memory.
- $b_1(t), b_2(t) \in [0.1, 8.0]$: Self-feedback recurrent parameters (baseline $\approx 2.4$).
- $c(t) = -0.5(q_1(t) + q_2(t))$: Mutual inhibitory coupling weight ($q_i \in [0.1, 10.0]$, baseline $\approx 3.5$).
- $I_g = 4.7$: Input gain scaling the normalized sensory inputs $S_L, S_R$.

---

### 2.4 Correlation Plasticity & Synaptic Scaling

In sharp corners and dead-end alleys, obstacles may temporarily rotate out of the narrow $2^\circ$ LiDAR field of view during an avoidance turn. Without neural memory, the drone would terminate its turn prematurely and collide with the sidewall.

To solve this, online **synaptic plasticity** adapts the recurrent weights $b_i$ and inhibitory weights $q_i$ using correlation-based learning:

$$v_i(t) = \text{clip}\left( \frac{O_i(t) + 1}{2}, 0.0, 1.0 \right)$$
$$\text{reflex}_i(t) = \begin{cases} 1.0 & \text{if } S_i(t) > -0.5 \\ 0.0 & \text{otherwise} \end{cases}$$

$$\Delta b_i(t) = \kappa \cdot \Delta t \left[ \mu_b \cdot v_i(t-1) \cdot v_i(t) \cdot \text{reflex}_i(t) + \gamma_b \cdot (k - v_i(t)) \cdot b_i(t)^2 \right]$$
$$\Delta q_i(t) = \kappa \cdot \Delta t \left[ \mu_q \cdot v_i(t-1) \cdot v_i(t) \cdot \text{reflex}_i(t) + \gamma_q \cdot (k - v_i(t)) \cdot q_i(t)^2 \right]$$

**Hyperparameters (Pedersen & Manoonpong, 2018):**
- Scaling rate $\kappa = 27.0$
- Learning rates $\mu_b = 0.0065$, $\mu_q = 0.015$
- Decay rates $\gamma_b = 0.0003$, $\gamma_q = 0.0003$
- Target activation constant $k = -0.01$

The first term acts as an activity-dependent potentiation mechanism (Hebbian-like reinforcement of active turns). The second term enforces homeostatic synaptic scaling, returning weights to baseline when the drone is in open air.

---

### 2.5 Yaw Steering Calculation & Velocity Regulation

The differential activation between the two neurons dictates the yaw rate (turning speed):

$$\text{steering}(t) = 0.5 \left( O_1(t) - O_2(t) \right)$$
$$\dot{\psi}_{\text{cmd}}(t) = -k_{\text{turn}} \cdot \text{steering}(t)$$

Where $k_{\text{turn}} = 1.35\text{ rad/s}$.

Forward cruise speed is throttled during evasive maneuvers to allow sufficient turning radius:

$$V_{\text{forward}}(t) = \begin{cases}
0.0\text{ m/s} & \text{if } S_L > 0.55 \text{ and } S_R > 0.55 \text{ (deadlock/head-on)} \\
0.025\text{ m/s} & \text{if } \max(S_L, S_R) > 0.25 \\
0.055\text{ m/s} & \text{if } \max(S_L, S_R) > -0.15 \\
0.10\text{ m/s} & \text{otherwise (nominal cruising speed)}
\end{cases}$$

---

## 3. System Architecture & Arduino Integration

```
   +-------------------------------------------------------------+
   |                Web Telemetry Dashboard                      |
   |   (Three.js 3D Canvas, Control Panel, Telemetry Meters)     |
   +------------------------------+------------------------------+
                                  | WebSocket (JSON, 30 Hz)
   +------------------------------v------------------------------+
   |                  Python Simulation Backend                  |
   |  - 6-DOF Drone Physics & Trajectory Engine                  |
   |  - Devos et al. Adaptive Neural Controller                  |
   |  - Direction Safety Evaluator & Decision State Machine       |
   |  - Scenario Library & Experiment Logger                     |
   +------------------------------+------------------------------+
                                  | Serial / Simulated Stream
   +------------------------------v------------------------------+
   |          Arduino Flight Controller (Firmware / HIL)         |
   |  - Multi-sensor distance sampling (HC-SR04 / TF-Mini)       |
   |  - MAVLink packet framing / custom ASCII protocol           |
   |  - PID Roll, Pitch, Yaw & Altitude rate stabilization       |
   |  - 4-channel ESC PWM motor actuation                        |
   +-------------------------------------------------------------+
```

### Physical Drone Specifications from Paper:
- **Frame:** Tarot 650 Sport carbon fiber quadcopter
- **Propellers:** 14" stiff carbon fiber
- **Motors:** 370 KV brushless DC motors
- **ESCs:** 40A Electronic Speed Controllers
- **Battery:** 6S 22.2V 8000 mAh LiPo (25-minute flight endurance)
- **Flight Controller:** Pixhawk 2 / ArduPilot / Arduino Mega 2560
- **Onboard Companion Computer:** Raspberry Pi Zero running MAVProxy + DroneKit Python framework

---

## 4. User-Driven Simulation Workflow

Unlike black-box automatic simulations, this system enforces an explicit **Human-in-the-Loop (HITL) Decision Gate**:

1. **Autonomous Cruising:** Quadcopter navigates forward at $0.10\text{ m/s}$ in the chosen scenario.
2. **Obstacle Detection:** When any sensor detects an obstacle within trigger threshold $d \le L_s = 0.50\text{ m}$, the simulation **pauses autonomous progression**.
3. **Safe Hover State:** The drone transitions to `WAITING_FOR_USER` state, leveling pitch and roll and maintaining stable hover altitude.
4. **Safety Evaluation:** The Decision Engine evaluates all 10 candidate directions:
   - Evaluates line-of-sight and clearance geometry $d_{\text{clear}} \ge \frac{L_d}{2} + L_m = 0.23\text{ m}$.
   - Labels directions as `RECOMMENDED` (optimal neural decision), `SAFE` (clear of obstacles), or `BLOCKED` (collision within turning radius).
5. **Operator Interaction:** The user selects a direction via UI buttons or keyboard hotkeys (W, A, S, D, R, F, Q, E, Space, Enter).
6. **Execution & Telemetry Logging:**
   - If a `SAFE` or `RECOMMENDED` direction is chosen, the drone executes the avoidance trajectory.
   - If an `UNSAFE` direction is chosen without override, the system alerts the user and displays why it is dangerous.
   - If "Override Unsafe" is enabled, the system permits the maneuver to let researchers evaluate collision physics.
7. **Metric Collection:** Successful clearing, minimum clearance distance, response time, and collision status are recorded to CSV and JSON logs.

---

## 5. Distinction Between Base Paper and Simulation Assumptions

| Aspect | Base Paper (Devos et al., 2018) | This Simulation Implementation |
| :--- | :--- | :--- |
| **LiDAR Array** | Dual front sensors at $\pm 20^\circ$ ($\Theta = 40^\circ$) in horizontal 2D plane | Dual front LiDARs ($\Theta = 40^\circ$) matching paper exactly, plus 8-direction radial + Up/Down sensor ring for complete 3D spatial awareness |
| **Avoidance Trigger** | Automatic real-time continuous closed loop | **Interactive User-in-the-Loop Workflow**: Automatically pauses upon detection, holds hover, displays safety status, and executes user-selected direction |
| **Flight Dynamics** | V-REP quadcopter model with fixed altitude | Full 6-DOF quadcopter physics with lift, drag, angular damping, motor rotor dynamics, and 3D altitude variation |
| **Microcontroller** | Raspberry Pi Zero interfacing with Pixhawk via DroneKit/MAVLink | Python backend executing exact paper neural dynamics, combined with complete Arduino C++ firmware (`arduino_flight_controller.ino`) and serial bridge |
| **Directions Supported** | Yaw-only turning (Left / Right) | 10 directions: Forward, Backward, Left, Right, Up, Down, Front-Left, Front-Right, Rear-Left, Rear-Right, plus Hold and E-Stop |
| **Scenarios** | 2 static maps (Circles room, Maze) | 13 scenarios: Front, Left, Right, Behind, Above, Below, Both Sides, Front-Left, Front-Right, Rear-Left, Rear-Right, Multiple Obstacles, Base Paper Env 2 (Maze), and Clear Flight |

---

## 6. Verification and Acceptance Criteria

1. **Mathematical Accuracy:** Equation (1) validated with $W_{\text{obj}} \ge 24\text{ cm}$ at $L_x = 15\text{ cm}$.
2. **Neural Fidelity:** Recurrent neural equations and synaptic plasticity formulas strictly adhere to Pedersen & Manoonpong (2018).
3. **Interactive Control:** Real-time bi-directional telemetry via WebSocket with $< 15\text{ ms}$ latency.
4. **Automated Testing:** Comprehensive pytest unit suite covering neural equations, sensor raycasting, flight dynamics, and safety rules.

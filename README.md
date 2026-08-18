# Neuroplastic Drone Obstacle Avoidance

This folder is independent from `approximate_controller_version` and contains
the neuroplastic two-neuron controller version of the PyBullet drone simulation.

## What is implemented

- Two front LiDAR rays, separated by 40 degrees.
- Two recurrent non-spiking tanh neurons.
- Self-excitatory synapses and mutual inhibition.
- Online correlation-based synaptic plasticity with synaptic scaling.
- A live PyBullet drone view with the blue travelled path and visible LiDAR rays.

The obstacle maps are reconstructed from the paper figure because exact map
coordinates were not published.

## Windows setup

Install Python 3.12 (64-bit) and select **Add Python to PATH** during its setup.
Then double-click `install_pybullet.bat` once.

## Run the neuroplastic simulation

Double-click `run_neuroplastic_maze.bat` for the maze environment.

Or run this from Command Prompt:

```cmd
cd /d "C:\Users\work\OneDrive\Documents\drones\neuroplasticity_controller_version"
py -3.12 live_drone_sim.py --env maze --controller paper --duration 180 --show-neurons
```

`--show-neurons` prints the two neural outputs and changing synaptic weights in
the Command Prompt while the PyBullet window runs.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

RobotSimulator is a Python GUI application that simulates robot movement and publishes position data via MQTT. The simulator allows users to define start/end points and watch a robot move between them while broadcasting its position to an MQTT broker.

## Running the Application

```bash
python RobotSimulator.py
```

The application requires:
- Python 3.9+
- `tkinter` (usually included with Python)
- `paho-mqtt` library: `pip install paho-mqtt`

## Architecture

This is a single-file application (`RobotSimulator.py`) built with a GUI-driven architecture:

### Core Components

**RobotSimulator Class** - Main application class that manages:
- GUI setup and layout (Tkinter)
- MQTT client connection and message publishing
- Robot movement simulation in a separate thread
- Real-time UI updates during simulation

### Key Design Patterns

**Threading Model**:
- Main thread runs the Tkinter event loop
- Simulation runs in a daemon thread (`simulation_thread`)
- Thread-safe UI updates via `root.after(0, callback)` to ensure GUI updates happen on main thread

**MQTT Publishing**:
- Topic format: `robot/{robot_id}/position`
- Message payload is JSON with structure:
  ```json
  {
    "robot_id": "ROBOT-001",
    "timestamp": "2025-11-22T12:00:00Z",
    "position": {"x": 10.5, "y": 20.3, "z": 0},
    "heading": 45.0
  }
  ```
- Messages published at configurable intervals during movement

**Movement Simulation** (RobotSimulator.py:208-289):
- Calculates straight-line path from start to end point
- Uses vector math to determine direction and distance
- Updates position incrementally based on speed and update interval
- Heading calculated using `atan2` and normalized to 0-360 degrees

### State Management

The simulator maintains state through instance variables:
- `is_running`: Controls simulation loop
- `mqtt_client`: Paho MQTT client instance
- `simulation_thread`: Reference to running thread
- UI elements store configuration (entries) and display current state (labels, progress bar)

### UI Structure

Five main sections arranged vertically:
1. MQTT Broker Configuration - connection settings
2. Robot Settings - ID, start/end coordinates, speed, update interval
3. Control Buttons - start/stop simulation
4. Current Status - live position display and progress bar
5. Message Log - scrollable log of all MQTT messages and events

## Development Notes

When modifying the simulation logic, remember:
- All UI updates from the simulation thread must use `root.after(0, callback)` to avoid threading issues
- The simulation thread is marked as daemon, so it will terminate when the main thread exits
- MQTT client uses `loop_start()` for background network handling
- Distance calculations use Euclidean distance; movement is always in a straight line
- Z-coordinate is always 0 (2D simulation)
- Timestamps use UTC format for consistency

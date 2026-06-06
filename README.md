#SCSS-2026 — Robotic Arm Pick & Place System

A computer-vision-guided robotic arm that automatically sorts parts on a conveyor belt, built for the **SCSS 2026** student competition. The system detects parts using YOLOv8, controls a 4-DOF servo arm via inverse kinematics, and communicates with an Arduino over UART — all running concurrently with Python's `asyncio`.

---

##System Architecture

```
┌─────────────────┐     UART (19200 baud)     ┌──────────────────────┐
│   Python Host   │ ◄────────────────────────► │   Arduino Mega/Uno   │
│                 │                             │                      │
│  • YOLOv8 CV   │                             │  • 4x Servo joints   │
│  • IK Solver   │                             │  • Gripper servo     │
│  • asyncio     │                             │  • DC conveyor motor │
│  • UART comms  │                             │  • Ultrasonic sensor │
└─────────────────┘                             └──────────────────────┘
```

The Python side runs **4 concurrent async tasks**:

| Task | Role |
|---|---|
| `task_citire_uart` | Listens for `CONVEYOR_STOPPED` / `CONVEYOR_RUNNING` messages from Arduino |
| `task_logica_robot` | Executes pick & place sequences when a part is detected and in position |
| `vision_system.run_vision_task` | Runs YOLOv8 inference and pushes detected class to the shared queue |
| `task_tastatura` | Listens for `q` + Enter to gracefully shut down all tasks |

---

##Repository Structure

```
SCSS-2026/
├── main.py                # Entry point — asyncio event loop & task orchestration
├── InverseKinematics.py   # 4-DOF IK solver using tinyik
├── UART.py                # Serial communication wrapper (pyserial)
├── computer_vision.py     # YOLOv8 inference & async vision task
├── SCSS-Arduino.ino       # Arduino firmware (servos, conveyor, ultrasonic)
└── my_model/              # Custom-trained YOLOv8 OBB model weights
```

---

##Hardware

- **Robotic Arm** — 4-DOF servo arm (5 servos total, including gripper)
- **Arduino** — controls all servos and the conveyor belt DC motor
- **Conveyor Belt** — driven by 2 DC motors (H-bridge control)
- **Ultrasonic Sensor** (HC-SR04) — detects when a part reaches the pickup position
- **Camera** — used by the computer vision module for part classification

**Arm link lengths (mm):**

| Segment | Length |
|---|---|
| L1 (base → shoulder) | 108.59 mm |
| L2 (shoulder → elbow) | 128.11 mm |
| L3 (elbow → wrist) | 159.91 mm |
| L4 (wrist → end-effector) | 62.45 mm |

**Key positions (Cartesian, mm):**

| Position | X | Y | Z |
|---|---|---|---|
| Pickup | 214.4 | 0.0 | 271.8 |
| Good parts zone | 150.0 | +120.0 | 200.0 |
| Reject zone | 150.0 | −120.0 | 200.0 |

**Gripper angles:** open = 45°, closed = 135°

---

##How It Works

1. The **conveyor belt** runs continuously, transporting parts toward the pickup point.
2. The **ultrasonic sensor** on the Arduino detects when a part is close (< 10 cm) and stops the belt, sending `CONVEYOR_STOPPED` over serial.
3. Simultaneously, the **YOLOv8 model** classifies the part (e.g., `roata buna`, `cub bun`, or a reject variant) and places the result in an async queue.
4. The **robot task** waits for both the CV result and the conveyor-stopped event, then executes the pick & place sequence:
   - Move to pickup position (IK-solved)
   - Close gripper
   - Move to the appropriate drop zone (good parts or rejects)
   - Open gripper
   - Return to HOME position
5. The conveyor restarts automatically after the arm clears the pickup area.

---

##Setup & Installation

### Python Dependencies

```bash
pip install pyserial numpy tinyik ultralytics opencv-python
```

### Arduino

1. Open `SCSS-Arduino.ino` in the Arduino IDE.
2. Install the `Servo` library (included by default).
3. Upload to your board. **Note:** the Arduino sketch uses baud rate `57600` — make sure `UART.py` matches (currently set to `19200`; adjust one to match the other).

### Running

```bash
python main.py
```

Press `q` + Enter at any time to gracefully stop all tasks and return the arm to the HOME position.

---

##Configuration

Edit the constants at the top of `main.py` to match your setup:

```python
# Serial port of the Arduino
port = 'COM37'          # Windows: 'COMx', Linux/Mac: '/dev/ttyUSBx'
baud_rate = 19200

# Gripper angles (degrees)
GRIPPER_DESCHIS = 45    # Open
GRIPPER_INCHIS  = 135   # Closed

# Cartesian positions (mm)
POZITIE_PRELUARE = (214.4, 0.0, 271.8)
ZONA_PIESE_BUNE  = (150.0, 120.0, 200.0)
ZONA_REBUTURI    = (150.0, -120.0, 200.0)
```

To use a different YOLOv8 model, change the `model_path` in `main_async()`:

```python
vision_system = ComputerVision(model_path='my_model/best.pt')
```

---

##UART Protocol

Communication between Python and Arduino uses plain ASCII over serial.

**Python → Arduino** (angle command):
```
J1,J2,J3,J4,GRIPPER\n
```
Example: `90,120,75,95,45\n` — all values in degrees (0–180).

**Arduino → Python** (status messages):
```
CONVEYOR_STOPPED
CONVEYOR_RUNNING
```

---

##Dependencies Summary

| Package | Purpose |
|---|---|
| `pyserial` | UART communication with Arduino |
| `numpy` | Vector math for IK error checking |
| `tinyik` | Iterative inverse kinematics solver |
| `ultralytics` | YOLOv8 model inference |
| `opencv-python` | Camera capture & image preprocessing |
| `asyncio` | Concurrent task management (stdlib) |

---

##License

This project was developed for the **SCSS 2026** student competition. Feel free to use and adapt it for educational purposes.

This project aims to control a remote controlled car better than what most hobby-grade can offer.



Overview:
This is a BLE commanded RC car, operated via a desktop app that uses a Xbox Controller for user input. It features multiple motor control modes for precise speed control and safety systems such as roll-over risk warning. The platform showcases modular software and hardware integration, demonstrating real-time control, sensor feedback, and robust off-road performance. The system also provides over-the-air (OTA) updates via Wi-Fi, automatically checking for newer software versions at startup when known networks with internet access are available.



Features:
- Multiple motor control modes:
  - Feed-Forward (FF): applies expected voltage to the motor for a certain speed without feedback
  - Proportional-Integrator (PI): dynamically adjusts the voltage of the motor to maintain a certain speed under varying load
  - PI + FF: combines both for faster response
- Motor start boost: when starting from a stop, the motor gets a small boost to overcome static friction
- Motor stall boost: if the motor fails to rotate (which can happen at low speeds over obstacles) for a longer time, it gets more boost the more it stalls
- Motor stall protection: if voltage is applied and the motor doesn't move for a certain amount of time, it enters a short sleep mode to prevent overheating
- Selectable gearbox ratio:
  - low-speed and high-torque
  - high-speed and low-torque
- Roll and pitch information for the user, useful for avoiding rolling over the car
- Adjustable suspension:
  - shock absorber tops are mounted on servo arm instead of on the chassis, allowing height adjustments or roll/pitch countering
  - selectable ride height
  - the car tilts downwards in the direction controller's right joystick points (example: if joystick is top-left, FL corner lowers and RR corner rises)
- Telemetry: battery voltage, roll and pitch, motor speed (revolutions/s), wheel speed (cm/s) and other system information
- OTA updates at start: using stored, encrypted Wi-Fi credentials, checks GitHub for newer software versions



Software:
The software was written in MicroPython instead of C/C++ due to it being easier to be modified with OTA updates, while a C implementation requires connecting the microcontroller to the desktop each time a modification is needed. Thanks to the processor used by the Pico 2 W, the loss in performance is minimal. Each subsystem is encapsulated in its own module.

At start-up, it runs the OTA updates routine. First, it checks for nearby known Wi-Fi network. Those are stored locally and encrypted. For each of those, it checks if they have internet connection. When a internet connection is made, using GitHub API it checks if the last software timestamp is the same as the one in the specified git path, accounting for both updates and roll-backs. If the timestamp differs, then it downloads all the files found at that path. If the download is successful, the new files replace the old ones. Any error aborts the rutine and runs the current software.

After that, the Pico configures each hardware module it has and starts advertising itself as a BLE device and is waiting for a connection from the desktop remote control app. Then, it processes each command received, acting on each module is needed.

The motor control is made by a variation of a PI control. This control is triggered by a timer interrupt. Unfortunately, the MicroPython implementation for the Pico doesn't have hardware timer interrupts, only software. An alternative is to use a PWM pin as trigger for interrupt since only pin interrupt seems to support true hardware interrupts. The problem with software interrupts is that the garbage collector can sometimes delay their trigger. The reason software interrupts are still used is made by the limitations of the hardware interrupts such as the useage of only integer type variables.

The library used for the distance sensor is a slightly modified version of Kevin McAleer's library (https://github.com/kevinmcaleer/vl53l0x).



Hardware components:
- Microcontroller: Raspberry Pi Pico 2 W
  
- Motor + Drive System:
  - 370 45 turns brushed DC motor (25000RPM @8.4V)
  - IBT-4 motor driver
  - Pololu Quadrature Encoder (12 CPR)
  - WPL 2-speed gearbox (servo-actuated)

- Mechanical actuation:
  - DSPower DS-S007M 21g servo (steering)
  - Micro 9g servo (gearbox shifting)
  - 4x PTK 7465 MG (suspension height adjustment)

- Sensors:
  - MPU-6050 IMU

- Power:
  - 2S LiPo 3000 mAh 25C battery
  - MP1584EN step-down converter
  - Voltage divider (for battery voltage reading)

 - Chassis and Body:
  - MN-90 frame and body with metal linkages and axles



Roadmap:
- making a configuration file containg all the values needed by different modules (pins, factors etc.), similar to a car's CCF file
- finding a way to connect the Xbox controller directlly to Pico W, without the need of a desktop app
- self-leveing suspension algorithm
- suspension mode for asistting suspension articulation in off-road
- safety assistance to prevent rolling over the car at high speeds (which is easy due to car's higher center of gravity)
- motor control for lower speeds (which may result in also swapping the motor for another one)
- making a custom pistol-style transmitter, possibly using NRF24 modules for communication
- rotating steering wheel
- a display in the car dashboard, simulating a gauge cluster
- custom FPV camera system
- porting the code to C/C++, maybe even microROS, but in a way that allows OTA updates; alternatively, all modules can each have their own microcontroller and a communication between them similar to CAN bus

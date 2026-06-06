#include <Servo.h>

#define JOINTS_NUM 4
#define BUFFER_SIZE 64

#define trig 11
#define echo 10
#define motor1pin1 6
#define motor1pin2 7
#define motor2pin1 8
#define motor2pin2 9

int target_joints[JOINTS_NUM] = {90, 90, 90, 90};
char inputBuffer[BUFFER_SIZE];
int gripper = 90; // Inițializat la 90° (sau unghiul tău de "Home" pentru clește)

bool bandaOprita = false; 

Servo servos[JOINTS_NUM];
Servo gripper_servo;

void setup() {
  Serial.begin(57600); 
  
  pinMode(trig, OUTPUT);
  pinMode(echo, INPUT);

  pinMode(motor1pin1, OUTPUT);
  pinMode(motor1pin2, OUTPUT);
  pinMode(motor2pin1, OUTPUT);
  pinMode(motor2pin2, OUTPUT);

  servos[0].attach(A0);
  servos[1].attach(A1);
  servos[2].attach(A2);
  servos[3].attach(A3);
  gripper_servo.attach(A4);

  gripper_servo.write(gripper);

  digitalWrite(motor1pin1, HIGH);
  digitalWrite(motor1pin2, LOW);
  digitalWrite(motor2pin1, HIGH);
  digitalWrite(motor2pin2, LOW);
}

void taskReadSerial() {
  if (Serial.available() > 0) {
    int bytesRead = Serial.readBytesUntil('\n', inputBuffer, BUFFER_SIZE - 1);
    inputBuffer[bytesRead] = '\0';

    char* token = strtok(inputBuffer, ",");
    
    for (int i = 0; i < JOINTS_NUM; i++) {
      if (token != NULL) {
        target_joints[i] = atoi(token);
        token = strtok(NULL, ",");
      }
    }

    if (token != NULL) {
      gripper = atoi(token);
    }
  }  
}

void taskMoveJoint(int servo_id, int targetAngle, unsigned long duration) {
  static int currentAngles[JOINTS_NUM] = {90, 90, 90, 90};
  static unsigned long lastExecution[JOINTS_NUM] = {0, 0, 0, 0};

  if (millis() - lastExecution[servo_id] < duration) return;

  if (currentAngles[servo_id] != targetAngle) {
    if (currentAngles[servo_id] < targetAngle) {
      currentAngles[servo_id]++;
    } else {
      currentAngles[servo_id]--;
    }
    servos[servo_id].write(currentAngles[servo_id]);
    lastExecution[servo_id] = millis();
  }
}

void taskGripper(int target_gripper, unsigned long duration) {
  static unsigned long lastExecution = 0;
  if (millis() - lastExecution < duration) return;

  gripper_servo.write(target_gripper);
  lastExecution = millis();
}

float ultrasonic() {
  digitalWrite(trig, LOW);
  delayMicroseconds(2); 
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  
  unsigned long duration = pulseIn(echo, HIGH, 10000); 
  if (duration == 0) return 999; 
  
  return (duration * 0.0343) / 2;
}

void check_conveyor(unsigned long duration) {
  static unsigned long chrono = 0;
  if (millis() - chrono < duration) return;

  float distance = ultrasonic();

  if (distance > 0 && distance < 10) {
    digitalWrite(motor1pin1, LOW);
    digitalWrite(motor1pin2, LOW);
    digitalWrite(motor2pin1, LOW);
    digitalWrite(motor2pin2, LOW);

    if (!bandaOprita) {
      Serial.println("CONVEYOR_STOPPED");
      bandaOprita = true;
    }
  } else {
    digitalWrite(motor1pin1, HIGH);
    digitalWrite(motor1pin2, LOW);
    digitalWrite(motor2pin1, HIGH);
    digitalWrite(motor2pin2, LOW);

    if (bandaOprita) {
      Serial.println("CONVEYOR_RUNNING");
      bandaOprita = false; 
    }
  }
  
  chrono = millis();
}

void loop() {
  taskReadSerial();

  taskMoveJoint(0, target_joints[0], 10);
  taskMoveJoint(1, target_joints[1], 15);
  taskMoveJoint(2, target_joints[2], 20);
  taskMoveJoint(3, target_joints[3], 25);

  taskGripper(gripper, 40);
  
  check_conveyor(20);
}
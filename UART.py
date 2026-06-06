import serial
import time

class Communication:
    def __init__(self, port='COM9', baud_rate=9600, timeout=1):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None
        
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            print(f"[UART] Conectat cu succes pe portul {self.port}")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"[UART] Eroare la conectare pe portul {self.port}: {e}")
            return False

    def send_angles(self, joint_angles, gripper_angle=None):
        """
        Trimite unghiurile brațului și poziția gripperului.
        Dacă gripper_angle este furnizat separat, îl adaugă la sfârșitul listei.
        """
        if self.ser and self.ser.is_open:
            try:
                corrected_angles = list(joint_angles)
                
                if len(corrected_angles) >= 3:
                    corrected_angles[2] = 180 - corrected_angles[2]
                
                if gripper_angle is not None:
                    corrected_angles.append(gripper_angle)
                
                # Formatare date: unghi1,unghi2,unghi3,unghi4,gripper\n
                data = ','.join(str(angle) for angle in corrected_angles) + '\n'
                
                self.ser.write(data.encode('utf-8'))
                print(f"[UART] Trimis spre Arduino: {data.strip()}")
                if len(joint_angles) >= 3:
                    print(f"[UART] (Info) J3 a fost inversat hardware din {joint_angles[2]}° în {corrected_angles[2]}°")
            except Exception as e:
                print(f"[UART] Eroare la trimiterea datelor: {e}")
        else:
            print("[UART] Eroare: Conexiunea nu este deschisă.")

    def close(self):
        """Închide conexiunea serială în siguranță."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[UART] Conexiune serială închisă curat.")
    
    def primeste_date(self):
        """Citește o linie primită de la Arduino (dacă există)."""
        if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
            try:
                linie = self.ser.readline().decode('utf-8').strip()
                return linie
            except Exception as e:
                print(f"[UART] Eroare la citirea datelor: {e}")
        return None
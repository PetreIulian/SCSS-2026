import asyncio
import time
from UART import Communication
from InverseKinematics import Arm
from computer_vision import ComputerVision

GRIPPER_DESCHIS = 45
GRIPPER_INCHIS  = 135

POZITIE_PRELUARE = (214.4, 0.0, 271.8)
ZONA_PIESE_BUNE  = (150.0, 120.0, 200.0)
ZONA_REBUTURI    = (150.0, -120.0, 200.0)
HOME_POSITION    = [90, 90, 90, 90, GRIPPER_DESCHIS]

rezultat_coada = asyncio.Queue()
eveniment_banda_oprita = asyncio.Event()


async def task_citire_uart(robot_comm):
    """TASK 1: Ascultă permanent Arduino și actualizează starea benzii."""
    print("[TASK UART] Pornit. Ascult starea benzii...")
    try:
        while True:
            date_primite = robot_comm.primeste_date()
            
            if date_primite:
                if date_primite == "CONVEYOR_STOPPED":
                    print("[TASK UART] Arduino raporteză: Banda s-a OPRIT. Piesa este la punct!")
                    eveniment_banda_oprita.set()
                    
                elif date_primite == "CONVEYOR_RUNNING":
                    print("[TASK UART] Arduino raporteză: Banda pornită / liberă.")
                    eveniment_banda_oprita.clear()
            
            await asyncio.sleep(0.1)
            
    except asyncio.CancelledError:
        print("[TASK UART] Oprit.")


async def task_logica_robot(arm, robot_comm):
    """TASK 2: Se ocupă de mișcarea robotului sincronizată cu banda."""
    print("[TASK ROBOT] Pregătit, aștept piese de la CV...")
    
    try:
        while True:
            rezultat_cv = await rezultat_coada.get()
            print(f"[TASK ROBOT] Viziune: Detectat '{rezultat_cv.upper()}'. Aștept oprirea fizică a benzii...")
            
            await eveniment_banda_oprita.wait()
            print("[TASK ROBOT] Bandă confirmată oprită! Încep secvența de Pick & Place...")

            angles_pick = arm.go_to_cartesian(*POZITIE_PRELUARE)
            if angles_pick:
                comanda_pick = list(angles_pick) + [GRIPPER_DESCHIS]
                robot_comm.send_angles(comanda_pick)
                await asyncio.sleep(2.0) 

                print("[TASK ROBOT] Prindere piesă...")
                comanda_strangere = list(angles_pick) + [GRIPPER_INCHIS]
                robot_comm.send_angles(comanda_strangere)
                await asyncio.sleep(1.0) 
            
            if rezultat_cv in ['roata buna', 'cub bun']:
                destinatie = ZONA_PIESE_BUNE
            else:
                destinatie = ZONA_REBUTURI

            angles_drop = arm.go_to_cartesian(*destinatie)
            if angles_drop:
                comanda_drop = list(angles_drop) + [GRIPPER_INCHIS]
                robot_comm.send_angles(comanda_drop)
                await asyncio.sleep(2.5) 

                print("[TASK ROBOT] Eliberare piesă...")
                comanda_eliberare = list(angles_drop) + [GRIPPER_DESCHIS]
                robot_comm.send_angles(comanda_eliberare)
                await asyncio.sleep(1.0) 

            print("[TASK ROBOT] Revenire în poziția HOME...")
            robot_comm.send_angles(HOME_POSITION)
            await asyncio.sleep(1.5)
            
            eveniment_banda_oprita.clear()
            rezultat_coada.task_done()
            
    except asyncio.CancelledError:
        print("[TASK ROBOT] Oprit.")


async def task_tastatura():
    """TASK 3 (NOU): Ascultă tasta 'q' în fundal fără a bloca celelalte task-uri."""
    print("[TASK KEYBOARD] Apasă 'q' și apoi Enter în orice moment pentru a opri sistemul.")
    try:
        while True:
            comanda = await asyncio.to_thread(input)
            if comanda.strip().lower() == 'q':
                print("\n[SYSTEM] Comandă de oprire 'q' detectată. Inițiem oprirea tuturor sistemelor...")
                # Găsim toate task-urile din loop și le trimitem cerere de anulare
                for task in asyncio.all_tasks():
                    if task != asyncio.current_task():
                        task.cancel()
                break
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass


async def main_async():
    arm = Arm()
    robot_comm = Communication(port='COM37', baud_rate=19200)
    
    if not robot_comm.connect():
        print("[CRITIC] Conexiunea UART a eșuat. Execuție oprită.")
        return

    robot_comm.send_angles(HOME_POSITION)
    vision_system = ComputerVision(model_path='yolov8n-obb.pt')

    print("[SYSTEM] Pornire Event Loop (4 Task-uri concurente)...")
    
    try:
        await asyncio.gather(
            vision_system.run_vision_task(rezultat_coada),
            task_logica_robot(arm, robot_comm),
            task_citire_uart(robot_comm),
            task_tastatura()        
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[SYSTEM] Proces de oprire declanșat...")
    finally:
        print("[SYSTEM] Retragere robot în poziția de siguranță...")
        try:
            robot_comm.send_angles(HOME_POSITION)
        except Exception:
            pass
        await asyncio.sleep(0.5)
        robot_comm.close()
        print("[SYSTEM] Închidere completă finalizată.")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
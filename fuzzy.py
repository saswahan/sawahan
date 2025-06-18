import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import serial
import time
import re

# --- Definisi Variabel Fuzzy ---
suhu = ctrl.Antecedent(np.arange(0, 51, 1), 'suhu')
kelembapan = ctrl.Antecedent(np.arange(0, 101, 1), 'kelembapan')
kecepatan_kipas = ctrl.Consequent(np.arange(0, 4, 1), 'kecepatan_kipas')  # 0 = mati, 1 = rendah, 2 = sedang, 3 = tinggi

# --- Membership Function ---
suhu['rendah'] = fuzz.trimf(suhu.universe, [0, 0, 25])
suhu['sedang'] = fuzz.trimf(suhu.universe, [20, 30, 40])
suhu['tinggi'] = fuzz.trimf(suhu.universe, [35, 50, 50])

kelembapan['kering'] = fuzz.trimf(kelembapan.universe, [0, 0, 40])
kelembapan['normal'] = fuzz.trimf(kelembapan.universe, [30, 50, 70])
kelembapan['lembab'] = fuzz.trimf(kelembapan.universe, [60, 100, 100])

kecepatan_kipas['mati'] = fuzz.trimf(kecepatan_kipas.universe, [0, 0, 1])
kecepatan_kipas['rendah'] = fuzz.trimf(kecepatan_kipas.universe, [0, 1, 2])
kecepatan_kipas['sedang'] = fuzz.trimf(kecepatan_kipas.universe, [1, 2, 3])
kecepatan_kipas['tinggi'] = fuzz.trimf(kecepatan_kipas.universe, [2, 3, 3])

# --- Aturan Fuzzy ---
rule1 = ctrl.Rule(suhu['rendah'] & kelembapan['kering'], kecepatan_kipas['mati'])
rule2 = ctrl.Rule(suhu['sedang'] & kelembapan['normal'], kecepatan_kipas['sedang'])
rule3 = ctrl.Rule(suhu['tinggi'] & kelembapan['lembab'], kecepatan_kipas['tinggi'])
rule4 = ctrl.Rule(suhu['tinggi'] & kelembapan['normal'], kecepatan_kipas['tinggi'])
rule5 = ctrl.Rule(suhu['sedang'] & kelembapan['lembab'], kecepatan_kipas['sedang'])
rule6 = ctrl.Rule(suhu['rendah'] & kelembapan['lembab'], kecepatan_kipas['rendah'])
rule7 = ctrl.Rule(suhu['tinggi'] & kelembapan['kering'], kecepatan_kipas['sedang'])

control_system = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7])
fan_simulator = ctrl.ControlSystemSimulation(control_system)

# --- Serial Config ---
SERIAL_PORT = 'COM3'
BAUD_RATE = 9600

# --- Hubungkan ke Arduino ---
print(f"[{time.strftime('%H:%M:%S')}] Python: Mencoba menghubungkan ke Arduino di {SERIAL_PORT}...")
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"[{time.strftime('%H:%M:%S')}] Python: Koneksi berhasil. Menunggu data sensor...")
except Exception as e:
    print(f"[{time.strftime('%H:%M:%S')}] ERROR: Gagal terhubung ke Arduino: {e}")
    exit()

# --- Loop utama ---
try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()

            if line.startswith("SENSOR_DATA:"):
                print(f"[{time.strftime('%H:%M:%S')}] Python: Menerima: {line}")
                match = re.search(r"T:([\d.]+),H:([\d.]+)", line)
                if match:
                    suhu_val = float(match.group(1))
                    kelembapan_val = float(match.group(2))

                    # --- Proses Fuzzy ---
                    fan_simulator.input['suhu'] = suhu_val
                    fan_simulator.input['kelembapan'] = kelembapan_val
                    fan_simulator.compute()

                    output = fan_simulator.output['kecepatan_kipas']
                    result = int(round(output))  # Dibulatkan ke 0,1,2,3

                    label_map = {
                        0: 'Mati',
                        1: 'Rendah',
                        2: 'Sedang',
                        3: 'Tinggi'
                    }
                    print(f"[{time.strftime('%H:%M:%S')}] Prediksi: {label_map[result]} ({result})")

                    ser.write(f"{result}\n".encode())
                    print(f"[{time.strftime('%H:%M:%S')}] Mengirim ke Arduino: {result}")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Format tidak dikenali.")
        time.sleep(0.05)

except KeyboardInterrupt:
    print(f"\n[{time.strftime('%H:%M:%S')}] Program dihentikan oleh pengguna.")
finally:
    if ser.is_open:
        ser.close()
        print(f"[{time.strftime('%H:%M:%S')}] Koneksi serial ditutup.")

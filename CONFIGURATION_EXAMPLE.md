# FOG-ORCHESTRATOR 2.0 — CONFIGURATION & DEPLOYMENT EXAMPLE

**Scope**: Setup guidelines and configuration examples for running the Vehicle A (`TRUCK_01`) hardware telemetry with the HMI.

---

## 1. ESP32 Firmware Secrets Setup (`secrets.h`)

To configure Vehicle A's ESP32:

1. Navigate to the sketch folder:
   ```bash
   cd esp32_code/sketch_aug26a
   ```
2. Copy the template to `secrets.h` (which is gitignored):
   ```bash
   cp secrets.example.h secrets.h
   ```
3. Open `secrets.h` and configure your local Wi-Fi and backend IP:
   ```c
   #pragma once

   // Replace with your local Wi-Fi Access Point credentials:
   #define SECRET_WIFI_SSID      "YOUR_WIFI_SSID"
   #define SECRET_WIFI_PASSWORD  "YOUR_WIFI_PASSWORD"

   // Replace <YOUR_PC_LAN_IP> with the IPv4 address of the PC running FastAPI
   // Example: "http://192.168.37.74:8000/api/hardware/telemetry"
   #define SECRET_HMI_TELEMETRY_URL "http://<YOUR_PC_LAN_IP>:8000/api/hardware/telemetry"
   ```

> [!CAUTION]
> Never put `127.0.0.1` into the ESP32 firmware. `127.0.0.1` refers to the ESP32 microcontroller itself. Use the PC's LAN IP address (e.g. `192.168.x.x`).

---

## 2. Finding the PC's LAN IP Address

In PowerShell on the PC running the backend:
```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object IPAddress, InterfaceAlias
```

Look for the active Wi-Fi or Ethernet adapter IP (for example, `192.168.37.74` or `192.168.29.146`).

---

## 3. Starting the Backend Server (LAN Accessible)

The FastAPI server must listen on `0.0.0.0:8000` so it accepts packets from external network devices:

```powershell
cd SYNQRA_SIH2026-27-HMI\backend
$env:PYTHONPATH = "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27;c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-main"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify it is listening on all interfaces:
```powershell
curl.exe http://127.0.0.1:8000/api/observability
```

---

## 4. Starting the HMI Frontend

In a second terminal:
```powershell
cd SYNQRA_SIH2026-27-HMI\frontend
npm run dev
```

Open your browser at **http://localhost:5173** to view the live dashboard.

---

## 5. Firewall Configuration (If Required)

If the ESP32 cannot reach port 8000 due to Windows Firewall, run this one-time command in an Administrative PowerShell:
```powershell
New-NetFirewallRule -DisplayName "FOG-Orchestrator HMI Backend Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```
*(This allows TCP traffic on port 8000 only; do not disable the entire firewall).*

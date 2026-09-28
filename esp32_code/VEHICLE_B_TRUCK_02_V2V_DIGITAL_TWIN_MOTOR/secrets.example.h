#pragma once

// =====================================================
// DEPLOYMENT SECRETS / ENDPOINT CONFIGURATION
//
// Copy this file to  secrets.h  in the same sketch folder
// and fill in the values for your network.
//
//     cp secrets.example.h secrets.h
//
// secrets.h is gitignored and must never be committed.
// Do not put real credentials in THIS file.
// =====================================================

#define SECRET_WIFI_SSID      "SYNQRA_HOST"
#define SECRET_WIFI_PASSWORD  "jagadeeshking"

// Backend telemetry endpoint (PORT 8000 is required for uvicorn).
// Windows Mobile Hotspot static IP: 192.168.137.1
#define SECRET_HMI_TELEMETRY_URL "http://192.168.137.1:8000/api/hardware/telemetry"

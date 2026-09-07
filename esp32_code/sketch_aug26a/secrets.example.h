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

#define SECRET_WIFI_SSID      "YOUR_WIFI_SSID"
#define SECRET_WIFI_PASSWORD  "YOUR_WIFI_PASSWORD"

// Backend telemetry endpoint. Host must match wherever the HMI
// backend is bound (see HMI_HOST / HMI_PORT on the backend).
#define SECRET_HMI_TELEMETRY_URL "http://192.0.2.10:8000/api/hardware/telemetry"

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { VehicleHmiApp } from "./vehicle/VehicleHmiApp";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root element #root is missing from truck01.html");
}

createRoot(container).render(
  <StrictMode>
    <VehicleHmiApp vehicleId="TRUCK_01" />
  </StrictMode>,
);

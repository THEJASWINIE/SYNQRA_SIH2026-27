/**
 * Application root — M4.
 *
 * M1 rendered a backend connectivity proof here. That proof is preserved, not discarded:
 * it now lives in `components/BackendHealth.tsx` and appears in the shell header as the
 * HMI-backend indicator, deliberately separate from the operational data connection
 * because the two are different failure domains.
 *
 * This file does exactly two things: mount the provider boundary, and render the shell.
 * It imports no concrete provider — `ProviderHost` is the sole module that does.
 */

import { AppShell } from "./screens/AppShell";
import { ProviderHost } from "./state/ProviderHost";
import "./theme/hmi.css";

export function App() {
  return (
    <ProviderHost>
      <AppShell />
    </ProviderHost>
  );
}

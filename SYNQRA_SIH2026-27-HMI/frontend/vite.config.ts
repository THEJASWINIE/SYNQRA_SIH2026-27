import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        truck01: resolve(__dirname, "truck01.html"),
        truck02: resolve(__dirname, "truck02.html"),
        // Fourth client view of the same canonical Twin. Separate entry, shared backend.
        minecast: resolve(__dirname, "mine-cast.html"),
      },
    },
  },
  test: {
    // Smoke tests render with react-dom/server, so no DOM environment is needed.
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dashboard calls /api/* and Vite proxies it to the FastAPI backend, so the
// browser only ever talks to one origin. The backend serves plain HTTP — there is
// no TLS listener, so this must be http:// and not https://.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});

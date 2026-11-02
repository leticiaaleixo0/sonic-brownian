import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // Forwards /api to the FastAPI server, so the browser sees a single origin and needs no CORS
    // 127.0.0.1 and not localhost: Node may resolve localhost to IPv6, where uvicorn does not listen
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});

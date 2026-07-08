import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

// Backend (FastAPI) http://127.0.0.1:8000 ga dev proksi.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/v1": "http://127.0.0.1:8000",
      "/files": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
})

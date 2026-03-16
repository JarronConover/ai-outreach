import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import { spawn } from "child_process";
import type { ChildProcess } from "child_process";
import type { IncomingMessage, ServerResponse } from "http";

let backendProcess: ChildProcess | null = null;

function killBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill("SIGTERM");
    backendProcess = null;
  }
}

process.on("SIGINT", () => {
  killBackend();
  process.exit(0);
});

process.on("SIGTERM", () => {
  killBackend();
  process.exit(0);
});

process.on("exit", killBackend);

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "backend-launcher",
      configureServer(server) {
        // POST /dev/start-backend — spawn uvicorn from the project root
        server.middlewares.use(
          "/dev/start-backend",
          (req: IncomingMessage, res: ServerResponse) => {
            if (req.method !== "POST") {
              res.statusCode = 405;
              res.end();
              return;
            }
            if (backendProcess && !backendProcess.killed) {
              res.setHeader("Content-Type", "application/json");
              res.end(JSON.stringify({ status: "already_running" }));
              return;
            }
            const projectRoot = path.resolve(__dirname, "..");
            backendProcess = spawn(
              "uvicorn",
              ["backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
              { cwd: projectRoot, stdio: "inherit", shell: true }
            );
            backendProcess.on("exit", () => {
              backendProcess = null;
            });
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ status: "starting" }));
          }
        );

        // POST /dev/stop-backend — kill the spawned uvicorn process
        server.middlewares.use(
          "/dev/stop-backend",
          (req: IncomingMessage, res: ServerResponse) => {
            if (req.method !== "POST") {
              res.statusCode = 405;
              res.end();
              return;
            }
            killBackend();
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ status: "stopped" }));
          }
        );

        // GET /dev/backend-process-status — is our spawned process alive?
        server.middlewares.use(
          "/dev/backend-process-status",
          (_req: IncomingMessage, res: ServerResponse) => {
            const alive = !!(backendProcess && !backendProcess.killed);
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ spawned: alive }));
          }
        );
      },
    },
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});

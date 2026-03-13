import express, { type Express } from "express";
import cors from "cors";
import { createProxyMiddleware } from "http-proxy-middleware";
import router from "./routes";

const app: Express = express();

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(
  "/api/fastapi",
  createProxyMiddleware({
    target: "http://localhost:8000",
    changeOrigin: true,
    pathRewrite: { "^/api/fastapi": "" },
    on: {
      error: (_err, _req, res: any) => {
        res.status(502).json({
          error: "FastAPI service unavailable. Ensure the Python server is running.",
        });
      },
    },
  })
);

app.use("/api", router);

export default app;

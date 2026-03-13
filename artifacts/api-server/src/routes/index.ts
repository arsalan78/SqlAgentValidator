import { Router, type IRouter } from "express";
import healthRouter from "./health";
import sqlAgentRouter from "./sql-agent";

const router: IRouter = Router();

router.use(healthRouter);
router.use(sqlAgentRouter);

export default router;

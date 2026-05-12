import { v4 as uuid } from "uuid";
import { redis } from "../services/redis.js";
import { loadPrompt } from "../services/prompts.js";

export async function jobsRoutes(app) {
  app.post("/jobs", async (req) => {
    const id = uuid();

    const job = {
      id,
      type: "generic",
      prompt: req.body.prompt,
      created_at: Date.now(),
    };

    await redis.set(`job:${id}`, JSON.stringify(job));
    await redis.set(`status:${id}`, "queued");
    await redis.lpush("queue:ollama", JSON.stringify(job));

    return { job_id: id, status: "queued" };
  });

  app.post("/jobs/summary", async (req) => {
    const id = uuid();
    const prompt = loadPrompt("summary", req.body.text);

    const job = {
      id,
      type: "summary",
      prompt,
      created_at: Date.now(),
    };

    await redis.set(`job:${id}`, JSON.stringify(job));
    await redis.set(`status:${id}`, "queued");
    await redis.lpush("queue:ollama", JSON.stringify(job));

    return { job_id: id, status: "queued" };
  });

  app.get("/jobs/:id", async (req) => {
    const { id } = req.params;

    const status = await redis.get(`status:${id}`);
    const result = await redis.get(`result:${id}`);

    if (!status) return { error: "not_found" };

    return {
      status,
      result: status === "done" ? result : null,
    };
  });
}

const Fastify = require("fastify");
const Redis = require("ioredis");
const { v4: uuidv4 } = require("uuid");
const fs = require("fs");

const app = Fastify({ logger: true });

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: process.env.REDIS_PORT,
});

const KEY_TTL = 604800; // 7 days
const DEFAULT_JOB_DURATION = 30; // seconds, fallback when no history

// helper
function loadPrompt(name, input) {
  const template = fs.readFileSync(`shared/prompts/${name}.txt`, "utf-8");
  return template.replace("{{INPUT}}", input);
}

// POST generic
app.post("/jobs", async (req, reply) => {
  const { prompt } = req.body;

  const id = uuidv4();

  const job = {
    id,
    type: "generic",
    prompt,
    created_at: Date.now(),
  };

  await redis.set(`ollama:job:${id}`, JSON.stringify(job), "EX", KEY_TTL);
  await redis.set(`ollama:status:${id}`, "queued", "EX", KEY_TTL);
  await redis.lpush("ollama:queue", JSON.stringify(job));

  const eta = await estimateETA();

  return { job_id: id, status: "queued", eta_seconds: eta };
});

// POST summary
app.post("/jobs/summary", async (req, reply) => {
  const { text } = req.body;

  const prompt = loadPrompt("summary", text);
  const id = uuidv4();

  const job = {
    id,
    type: "summary",
    prompt,
    created_at: Date.now(),
  };

  await redis.set(`ollama:job:${id}`, JSON.stringify(job), "EX", KEY_TTL);
  await redis.set(`ollama:status:${id}`, "queued", "EX", KEY_TTL);
  await redis.lpush("ollama:queue", JSON.stringify(job));

  const eta = await estimateETA();

  return { job_id: id, status: "queued", eta_seconds: eta };
});

// GET status
app.get("/jobs/:id", async (req, reply) => {
  const { id } = req.params;

  const status = await redis.get(`ollama:status:${id}`);

  if (!status) return reply.code(404).send({ error: "not_found" });

  if (status === "done") {
    const result = await redis.get(`ollama:result:${id}`);
    return { status, result };
  }

  const eta = await estimateETA();

  return { status, eta_seconds: eta };
});

// ETA
async function estimateETA() {
  const len = await redis.llen("ollama:queue");
  const durations = await redis.lrange("ollama:metrics:durations", 0, 20);

  const avg = durations.length
    ? durations.reduce((a, b) => a + parseFloat(b), 0) / durations.length
    : DEFAULT_JOB_DURATION;

  return Math.round(len * avg);
}

app.listen({ port: 3000, host: "0.0.0.0" });

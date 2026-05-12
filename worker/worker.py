import redis
import requests
import json
import time
import os

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True
)

OLLAMA_URL = os.getenv("OLLAMA_URL")

while True:
    _, job_raw = r.brpop("queue:ollama")
    job = json.loads(job_raw)

    job_id = job["id"]

    r.set(f"status:{job_id}", "processing")

    start = time.time()

    try:
        res = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "llama3.1:8b-instruct-q4_K_M",
                "messages": [
                    {"role": "user", "content": job["prompt"]}
                ],
                "stream": False
            },
            timeout=120
        )

        output = res.json()["message"]["content"]
        duration = time.time() - start

        r.set(f"result:{job_id}", output)
        r.set(f"status:{job_id}", "done")

        r.lpush("metrics:durations", duration)
        r.ltrim("metrics:durations", 0, 50)

    except Exception as e:
        r.set(f"status:{job_id}", "error")
        r.set(f"result:{job_id}", str(e))
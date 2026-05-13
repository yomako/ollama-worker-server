import redis, requests, json, time, os, traceback

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True
)

OLLAMA_URL = os.getenv("OLLAMA_URL")
KEY_TTL = 604800  # 7 days

while True:
    result = r.brpop("ollama:queue", timeout=5)

    if result is None:
        continue

    _, job_raw = result
    job = json.loads(job_raw)

    job_id = job["id"]

    r.set(f"ollama:status:{job_id}", "processing")

    start = time.time()

    try:
        res = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "llama3.1:8b-instruct-q4_K_M",
                "messages": [{"role": "user", "content": job["prompt"]}],
                "stream": False
            },
            timeout=120
        )

        output = res.json()["message"]["content"]

        duration = time.time() - start

        r.set(f"ollama:result:{job_id}", output, ex=KEY_TTL)
        r.set(f"ollama:status:{job_id}", "done", ex=KEY_TTL)

        r.lpush("ollama:metrics:durations", duration)
        r.ltrim("ollama:metrics:durations", 0, 50)

    except Exception as e:
        err = traceback.format_exc()
        r.set(f"ollama:status:{job_id}", "error", ex=KEY_TTL)
        r.set(f"ollama:error:{job_id}", err)
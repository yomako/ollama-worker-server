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

    r.set(f"ollama:status:{job_id}", "processing", ex=KEY_TTL)

    start = time.time()
    r.set("ollama:current_job", job_id, ex=300)
    r.set(f"ollama:start:{job_id}", start, ex=300)

    try:
        with requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "llama3.1:8b-instruct-q4_K_M",
                "messages": [{"role": "user", "content": job["prompt"]}],
                "stream": True
            },
            stream=True,
            timeout=300  # tylko na połączenie / brak danych
        ) as res:

            full = ""

            for line in res.iter_lines():
                if not line:
                    continue

                chunk = json.loads(line)

                # Ollama chat API:
                # chunk["message"]["content"]
                token = chunk.get("message", {}).get("content", "")

                if token:
                    full += token

                    # 🔥 zapis progresu
                    r.set(f"ollama:partial:{job_id}", full, ex=KEY_TTL)

                # zakończenie streama
                if chunk.get("done"):
                    break

        duration = time.time() - start

        r.set(f"ollama:result:{job_id}", full, ex=KEY_TTL)
        r.set(f"ollama:status:{job_id}", "done", ex=KEY_TTL)

        r.delete(f"ollama:partial:{job_id}")
        r.delete("ollama:current_job")
        r.delete(f"ollama:start:{job_id}")

        r.lpush("ollama:metrics:durations", duration)
        r.ltrim("ollama:metrics:durations", 0, 50)

    except Exception:
        err = traceback.format_exc()

        r.set(f"ollama:status:{job_id}", "error", ex=KEY_TTL)
        r.set(f"ollama:error:{job_id}", err, ex=KEY_TTL)
        r.delete("ollama:current_job")
        r.delete(f"ollama:start:{job_id}")
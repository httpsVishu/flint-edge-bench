import requests

URL = "http://127.0.0.1:8080/v1/chat/completions"

payload = {
    "model": "flint",
    "messages": [{"role": "user", "content": "Write a Python function that reverses a string."}],
    "max_tokens": 600,
}
reply = requests.post(URL, json=payload, timeout=900).json()
message = reply["choices"][0]["message"]
print("THINKING:", (message.get("reasoning_content") or "")[:300])
print("ANSWER:", message.get("content"))
print()
t = reply.get("timings", {})
print("Tokens read     :", t.get("prompt_n"))
print("Reading speed   :", round(t.get("prompt_per_second", 0), 1), "tokens/sec")
print("Writing speed   :", round(t.get("predicted_per_second", 0), 1), "tokens/sec")
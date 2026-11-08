import os
import logging

for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(v, None)
os.environ["NO_PROXY"] = "*"

import fastf1

CACHE = r"C:\Users\user\OneDrive\Документы\deepseek-harness\default-workspace\race-engineering-portfolio\projects\02_fastf1\f1_cache"
fastf1.Cache.configure(cache_dir=CACHE)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

print("=== 1) событие найдено? ===")
s = fastf1.get_session(2024, "Sao Paulo", "R")
print("event:", s.event.get("EventName"), "round:", s.event.get("RoundNumber"))
print("session name:", s.name)

print()
print("=== 2) load() ===")
try:
    s.load(telemetry=False, messages=False, weather=False)
    print("load returned")
except Exception as e:
    print("load raised:", type(e).__name__, e)

print()
print("=== 3) что загрузилось ===")
print("has laps attr:", hasattr(s, "_laps"))
try:
    print("laps:", len(s.laps))
except Exception as e:
    print("laps error:", type(e).__name__, e)

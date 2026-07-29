import inspect

from app.ai.model_manager import ModelManager
from app.ai.detector import detector
import app.api.v1.ai as ai_mod

# Change 4 — warm-up size
src = inspect.getsource(ModelManager.load_model)
assert "640, 640" in src
print("[OK] #4 warm-up 640x640")

# Change 3 — helper methods
for m in ["get_boxes", "get_classes", "get_confidence", "parse_results"]:
    assert hasattr(detector, m), f"missing {m}"
print("[OK] #3 helpers: get_boxes / get_classes / get_confidence / parse_results")

# Change 1 — no "await asyncio.to_thread" call in code
src = inspect.getsource(ai_mod)
assert "await asyncio.to_thread" not in src, "await asyncio.to_thread still present"
print("[OK] #1 await asyncio.to_thread not in code")

# Change 2 — test-camera route
routes = [r.path for r in ai_mod.router.routes]
match = [r for r in routes if "test-camera" in r]
assert len(match) > 0, f"test-camera not found in routes: {routes}"
print("[OK] #2 /test-camera registered:", match)

print()
print("All 4 suggestions verified OK")

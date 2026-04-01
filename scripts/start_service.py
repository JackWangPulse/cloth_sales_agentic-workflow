from _bootstrap import PROJECT_ROOT  # noqa: F401
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple server starter with verification."""
import sys
import time
import httpx

print("=" * 70)
print("FastAPI Service Starter")
print("=" * 70)

# Test import first
print("\n[1] Testing imports...")
try:
    from app.main import app
    print(f"鉁?App imported: {app.title}")
    print(f"鉁?Version: {app.version}")
    print(f"鉁?Routes: {len(app.routes)}")
except Exception as e:
    print(f"鉁?Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[2] Starting server with uvicorn...")
print("=" * 70)
print("Server will start at: http://127.0.0.1:8000")
print("API Docs: http://127.0.0.1:8000/docs")
print("=" * 70)
print("\nStarting in 2 seconds...\n")
time.sleep(2)

# Start server
try:
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
except KeyboardInterrupt:
    print("\n\nServer stopped.")
except Exception as e:
    print(f"\n鉁?Server error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)



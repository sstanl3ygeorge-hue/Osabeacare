import re
import os
import collections

# Regex to match @app.get("/path"), @router.post("/", ...), etc.
# Groups: 1=method, 2=path
route_re = re.compile(r"@(?:app|router|[\w]+_router)\.(get|post|put|delete|patch|options|head)\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)

# Regex for include_router
include_re = re.compile(r"(?:app|router)\.include_router\(\s*(\w+)_router", re.IGNORECASE)

def get_routes(filepath):
    routes = []
    if not os.path.exists(filepath):
        return routes
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            match = route_re.search(line)
            if match:
                method = match.group(1).upper()
                path = match.group(2)
                routes.append({"method": method, "path": path, "line": i})
    return routes

def get_include_order(filepath):
    order = []
    if not os.path.exists(filepath):
        return order
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = include_re.search(line)
            if match:
                order.append(match.group(1))
    return order

server_file = "backend/server.py"
route_dir = "backend/routes"

# 1) Server duplicates
server_routes = get_routes(server_file)
server_map = collections.defaultdict(list)
for r in server_routes:
    server_map[(r["method"], r["path"])].append(r["line"])

print("--- Duplicates within backend/server.py ---")
found_server_dupes = False
for (m, p), lines in server_map.items():
    if len(lines) > 1:
        found_server_dupes = True
        print(f"[{m}] {p} -> lines: {lines}")
if not found_server_dupes:
    print("None found.")

# 2) Route module duplicates
all_module_routes = collections.defaultdict(list)
route_files = []
if os.path.exists(route_dir):
    route_files = [f for f in os.listdir(route_dir) if f.endswith(".py") and f != "__init__.py"]

for filename in route_files:
    module_name = filename[:-3]
    path = os.path.join(route_dir, filename)
    routes = get_routes(path)
    for r in routes:
        all_module_routes[(r["method"], r["path"])].append({"module": module_name, "line": r["line"], "file": path})

# 3) Check order relevance from server.py
include_order = get_include_order(server_file)
order_map = {name: i for i, name in enumerate(include_order)}

print("\n--- Duplicates across route modules ---")
found_module_dupes = False
for (m, p), entries in all_module_routes.items():
    if len(entries) > 1:
        found_module_dupes = True
        # Sort by include order if possible
        entries.sort(key=lambda x: order_map.get(x["module"], 999))
        print(f"[{m}] {p}")
        for e in entries:
            order_idx = order_map.get(e["module"], "unknown")
            print(f"  {e['file']}:{e['line']} (Module: {e['module']}, Include Order Index: {order_idx})")
if not found_module_dupes:
    print("None found.")

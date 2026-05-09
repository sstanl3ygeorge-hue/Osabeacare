"""Run once to regenerate backend/routes/body_maps_data.py"""
import base64
from pathlib import Path

lines = [
    "# Auto-generated: CQC Expert body map template images embedded as base64",
    "# Source: uploads/templates/Osabea Body Map_*.docx",
    "",
]
for g in ["male", "female"]:
    p = Path(f"backend/assets/body_maps/body_map_{g}.png")
    b64 = base64.b64encode(p.read_bytes()).decode()
    lines.append(f"BODY_MAP_{g.upper()}_PNG_B64 = (")
    chunks = [b64[i:i+88] for i in range(0, len(b64), 88)]
    for chunk in chunks:
        lines.append(f'    "{chunk}"')
    lines.append(")")
    lines.append("")

Path("backend/routes/body_maps_data.py").write_text("\n".join(lines))
print("written", len(lines), "lines to backend/routes/body_maps_data.py")

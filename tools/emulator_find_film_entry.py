#!/usr/bin/env python3
"""Find the actual Create Film card in Android uiautomator XML."""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
root = ET.parse(source).getroot()
candidates = []
for node in root.iter():
    text = node.attrib.get("text", "").strip().lower()
    desc = node.attrib.get("content-desc", "").strip().lower()
    label = (text + " " + desc).strip()
    bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
    if not bounds:
        continue
    x1, y1, x2, y2 = map(int, bounds.groups())
    if x2 <= x1 or y2 <= y1:
        continue
    if text == "create film" or desc == "create film":
        priority = 0
    elif "create film" in label:
        priority = 1
    elif "film creator" in label or "generate screenplay" in label:
        priority = 2
    else:
        continue
    clickable = node.attrib.get("clickable", "false") == "true"
    area = (x2 - x1) * (y2 - y1)
    candidates.append((priority, not clickable, -area, (x1+x2)//2, (y1+y2)//2, label))
if not candidates:
    raise SystemExit("Film-creation entry has no usable accessibility bounds")
candidates.sort()
_, _, _, x, y, label = candidates[0]
destination.write_text(f"x={x}\ny={y}\n", encoding="utf-8")
print(f"Found Create Film card at {x},{y}: {label}")

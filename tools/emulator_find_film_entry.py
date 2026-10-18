#!/usr/bin/env python3
"""Find a visible, tappable film-creation entry in Android uiautomator XML."""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
root = ET.parse(source).getroot()
phrases = ("create film", "film creator", "ai filmmaking studio", "filmmaking studio", "generate screenplay")
for node in root.iter():
    label = (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).strip().lower()
    if not any(phrase in label for phrase in phrases):
        continue
    bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
    if not bounds:
        continue
    x1, y1, x2, y2 = map(int, bounds.groups())
    if x2 <= x1 or y2 <= y1:
        continue
    destination.write_text(f"x={(x1+x2)//2}\ny={(y1+y2)//2}\n", encoding="utf-8")
    print(f"Found film-creation entry at {(x1+x2)//2},{(y1+y2)//2}: {label}")
    raise SystemExit(0)
raise SystemExit("Film-creation entry has no usable accessibility bounds")

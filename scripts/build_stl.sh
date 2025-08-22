#!/usr/bin/env bash
set -euo pipefail

CAD_DIR="hardware/cad"
STL_DIR="hardware/stl"
mkdir -p "$STL_DIR"

for scad in "$CAD_DIR"/*.scad; do
  [ -e "$scad" ] || continue
  base=$(basename "$scad" .scad)
  openscad -o "$STL_DIR/$base.stl" "$scad"
  echo "Generated $STL_DIR/$base.stl"
done

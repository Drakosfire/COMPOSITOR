# Conks illustrated asset inventory

Status: **COMPOSITOR-only offline asset witness for PRIME review**. Base `b5b878fb309c848892ccfa2a40b8fb3222afcf9c`. This does not constitute semantic ingestion, map interpretation, a provider run, or adventure competence acceptance.

The existing `conks-md-substrate-001` used the printer-friendly PDF (`sha256:9c6458d5c742945e7b0c0abfcaef217384a8a14a6c503458f2ad49e7ee143e8c`) with supplied Markdown (`sha256:7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`). It rightly reported `asset_inventory_pending`: neither supplied Markdown nor that printer-friendly PDF includes the two illustrated map images. The illustrated v2.1 PDF (`sha256:b85eb98ee60110e90de90fa04574ae8a5a2b19f4e24d42acd998ec34fdffba41`) has a distinct Greenfields regional map on printed/physical page 4, xref 31, and a Hempholm village map on printed/physical page 8, xref 65. The page-8 Stage B orphan warning comes from a true continuation page without a local heading. It remains visible; no heading was invented to clear the gate.

`scripts/inventory_conks_assets.py` pins the accepted source manifest and illustrated PDF, validates the exact prior evidence package, then checks the page/xref occurrence and PNG geometry before writing private files. `compositor.asset_inventory.project_asset_references` independently reopens that PDF and verifies each declared page/xref occurrence, extracted PNG bytes, dimensions, and placement against the private file and manifest. A manifest and image rehashed together cannot launder an unrelated image into the package. It materializes a new immutable package with the original evidence resources plus two `asset_reference` resources. Their origin points to the illustrated PDF, not to the printer-friendly PDF or Markdown. The images are not embedded in JSON; their status stays `reference_only` pending content and audience review. The prior package revision is unchanged, and its structural and other asset omissions remain visible.

Private replay `conks-illustrated-assets-002` under the independently verified projector produced two PNGs under ignored `.local/private/runs/`, a manifest at SHA-256 `8c76c676572da58421a502c7215cca10cfda7a5231e96515dc3286153c30ad2e`, and derived package revision `a2052f59793b1da38c0663fb62b140b0fefcf0a423199c8acddf2599c926d7b9`. The page-4 map bytes hash to `b0bbbbae4093af6c8986243ea460d49af1db0909d170135e5b3b2c655dbfc3a1` (840 × 649); the page-8 map hashes to `68e405fab7ec51655679a0b50285c5a7cc280ec88c6e079ba8287d6761a2b084` (1000 × 773). Both were visually compared with their rendered source pages. Initial replay `-001` is preserved for development history; `-002` is the cited source-verified result. No image bytes are in Git. `.gitignore` excludes the private run.

Run with the pinned private source manifest and existing offline evidence package:

```sh
PYTHONPATH=src /path/to/RulesIngestion/.venv/bin/python scripts/inventory_conks_assets.py \
  --source-manifest "$PRIVATE_ROOT/gold/conks/source_manifest.json" \
  --base-store "$PRIVATE_ROOT/runs/conks-md-substrate-001/packages" \
  --base-package-id conks-evidence-conks-md-substrate-001 \
  --base-revision a59d277227b906f2b07ec375bdec64adf7c41d40cb99a2807d909eaaf2c46eba \
  --private-root "$PRIVATE_ROOT" --run-id conks-illustrated-assets-002
```

Use a new run ID for another replay because outputs are immutable. Substituting the accepted source manifest fails before output creation. A wrong page/xref fails extraction before output creation. Altered private image bytes fail package projection even if their hash and the manifest hash are recomputed. The real-PDF synthetic regression covers source and image substitution, status escalation, contained paths, and package reload. This offline operation made zero provider calls and no World or Buddy write.

Frozen Conks gold v3 remains the scoring target until a separately reviewed v4 is frozen. The proposed new case covers the Hempholm map's presence and provenance. It does not adjudicate marker-to-location mapping, full map topology, or official setting canon. Other artwork and diagrams still need a complete asset classification before overall asset readiness can be claimed.

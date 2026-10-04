import copy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from compositor.package import CompositionError
from compositor.scene_contribution import load_pinned_context, readback_claim, validate_contribution

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/public/adventure_graph/scene-card-cycle.json"


def _write(path, value):
    path.write_bytes(value)
    return sha256(value).hexdigest()


def lab(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    source = tmp_path / "source.pdf"
    source_hash = _write(source, fixture["synthetic_source"].encode())
    page = tmp_path / "stageB.evidence_units.json"
    page_hash = _write(page, json.dumps({"gates_passed": True, "units": [{"unit_id": fixture["unit_id"], "text": fixture["synthetic_source"]}]}).encode())
    manifest = tmp_path / "manifest.json"
    manifest_hash = _write(manifest, json.dumps({"source_pdf_sha256": source_hash, "pages": [{"page_index": 0, "artifact_sha256": {"stageB.evidence_units.json": page_hash}}]}).encode())
    package = tmp_path / "package.json"
    package_hash = _write(package, json.dumps({"package_id": "synthetic", "revision": "a" * 64}).encode())
    args = dict(source_path=source, source_sha256=source_hash, manifest_path=manifest,
                manifest_sha256=manifest_hash, page_files={0: (page, page_hash)},
                package_path=package, package_sha256=package_hash,
                package_id="synthetic", package_revision="a" * 64)
    context = load_pinned_context(**args)
    contribution = {"id": "bridge", "source": {k: context[k] for k in ("source_sha256", "manifest_sha256", "package_sha256", "package_id", "package_revision")},
                    "claims": fixture["claims"], "choices": fixture["choices"]}
    return args, context, contribution


def test_reopens_supported_claim_and_retains_non_source_states(tmp_path):
    _, context, contribution = lab(tmp_path)
    assert validate_contribution(contribution, context) == {"claim_count": 5, "choice_count": 1, "unresolved_count": 1}
    assert readback_claim(contribution["claims"][0], context)[0]["quote"] == "A traveler reaches the lantern bridge."
    assert readback_claim(contribution["claims"][3], context) == []


def test_pins_and_evidence_fail_visibly(tmp_path):
    args, context, contribution = lab(tmp_path)
    args["page_files"][0][0].write_text("changed")
    with pytest.raises(CompositionError, match="Stage B page changed"):
        load_pinned_context(**args)
    bad = copy.deepcopy(contribution)
    bad["claims"][0]["evidence"][0]["quote"] = "invented"
    with pytest.raises(CompositionError, match="citation"):
        validate_contribution(bad, context)
    bad = copy.deepcopy(contribution)
    bad["claims"][3]["state"] = "source_supported"
    with pytest.raises(CompositionError):
        validate_contribution(bad, context)

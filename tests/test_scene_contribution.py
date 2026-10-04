import copy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from compositor.package import CompositionError, JsonPackageStore, make_source_package
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
    store = JsonPackageStore(tmp_path / "packages")
    saved = make_source_package(store, package_id="synthetic", title="Synthetic bridge",
        resources={fixture["unit_id"]: {"id": fixture["unit_id"], "kind": "evidence_prose",
            "name": "Bridge", "text": fixture["synthetic_source"], "audience": "GM",
            "origin": {"type": "source", "source_id": f"sha256:{source_hash}",
                "page_index": 0, "locator": "rules_ingestion_ab/page-0/stageB.evidence_units.json#/units/0"}}})
    package = store.path_for(saved["package_id"], saved["revision"])
    package_hash = sha256(package.read_bytes()).hexdigest()
    args = dict(source_path=source, source_sha256=source_hash, manifest_path=manifest,
                manifest_sha256=manifest_hash, page_files={0: (page, page_hash)},
                package_path=package, package_sha256=package_hash,
                package_id="synthetic", package_revision=saved["revision"])
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


def test_rejects_unrelated_and_tampered_package(tmp_path):
    args, _, _ = lab(tmp_path)
    package = args["package_path"]
    content = json.loads(package.read_text())
    content["resources"]["bridge-opening"]["origin"]["source_id"] = "sha256:" + "f" * 64
    package.write_text(json.dumps(content))
    args["package_sha256"] = sha256(package.read_bytes()).hexdigest()
    with pytest.raises(CompositionError, match="integrity"):
        load_pinned_context(**args)
    content.pop("revision")
    unrelated = JsonPackageStore(tmp_path / "other-packages")
    saved = unrelated.save(content)
    args["package_path"] = unrelated.path_for(saved["package_id"], saved["revision"])
    args["package_sha256"] = sha256(args["package_path"].read_bytes()).hexdigest()
    args["package_revision"] = saved["revision"]
    with pytest.raises(CompositionError, match="lineage"):
        load_pinned_context(**args)

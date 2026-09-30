"""Deterministic versioned Composition package kernel.

This module does no inference, OCR, network access, or World publication. It
supplies the package boundary and the first project-authored round-trip witness.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Literal


class CompositionError(ValueError):
    """Invalid package, binding, or edit operation."""


def _hash(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(data.encode("utf-8")).hexdigest()


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value in {".", ".."} or any(c in value for c in "/\\\x00"):
        raise CompositionError(f"invalid {label}")
    return value


def _ref(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise CompositionError("package reference must be an object")
    package_id = _id(value.get("package_id"), "package id")
    revision = value.get("revision")
    if not isinstance(revision, str) or len(revision) != 64 or any(c not in "0123456789abcdef" for c in revision):
        raise CompositionError("package reference needs an exact SHA-256 revision")
    return {"package_id": package_id, "revision": revision}


def _resources(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise CompositionError("resources must be an object")
    for key, resource in value.items():
        _id(key, "resource id")
        if not isinstance(resource, dict) or resource.get("id") != key:
            raise CompositionError("resource id does not match its key")
        if resource.get("audience") not in {"GM", "PLAYER"}:
            raise CompositionError(f"resource {key} needs GM or PLAYER audience")
        if any(not isinstance(resource.get(k), str) for k in ("kind", "name", "text")):
            raise CompositionError(f"resource {key} needs kind, name, and text")
        origin = resource.get("origin")
        if not isinstance(origin, dict) or origin.get("type") not in {"source", "authored"}:
            raise CompositionError(f"resource {key} needs an origin")
        if origin["type"] == "source" and (not origin.get("source_id") or not origin.get("locator")):
            raise CompositionError(f"source resource {key} needs a reversible locator")
        if origin["type"] == "authored" and not origin.get("reason"):
            raise CompositionError(f"authored resource {key} needs a reason")
        refs = resource.get("rule_refs", [])
        if not isinstance(refs, list):
            raise CompositionError("rule_refs must be a list")
        coverage = resource.get("review_coverage", [])
        if not isinstance(coverage, list) or any(
                item not in {"worldbuilding", "planning", "playing"} for item in coverage):
            raise CompositionError("review_coverage must list known workflows")
        for rule in refs:
            if not isinstance(rule, dict) or not rule.get("resource_id"):
                raise CompositionError("invalid rule binding")
            if "package_id" in rule or "revision" in rule:
                _ref(rule)
    return value


def _dependencies(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise CompositionError("dependencies must be a list")
    seen = set()
    for dep in value:
        ref = _ref(dep)
        key = (ref["package_id"], ref["revision"])
        if key in seen:
            raise CompositionError("duplicate exact dependency")
        seen.add(key)
        if dep.get("mode") == "bundled":
            _resources(dep.get("resources"))
            if not isinstance(dep.get("permission_basis"), str) or not dep["permission_basis"]:
                raise CompositionError("bundled content needs a recorded permission basis")
            if not isinstance(dep.get("review_issues", []), list) or any(
                    not isinstance(issue, dict) or not issue.get("kind")
                    for issue in dep.get("review_issues", [])):
                raise CompositionError("bundled review issues must be a list")
            if "review_scope_complete" in dep and dep["review_scope_complete"] is not True:
                raise CompositionError("invalid bundled review scope marker")
        elif dep.get("mode") == "linked":
            if "resources" in dep:
                raise CompositionError("linked dependency cannot carry resources")
        else:
            raise CompositionError("dependency mode must be linked or bundled")
    return value


def _relationships(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise CompositionError("relationships must be a list")
    seen = set()
    for relation in value:
        if not isinstance(relation, dict):
            raise CompositionError("relationship must be an object")
        rid = _id(relation.get("id"), "relationship id")
        if rid in seen:
            raise CompositionError("duplicate relationship id")
        seen.add(rid)
        _id(relation.get("source_id"), "relationship source")
        _id(relation.get("target_id"), "relationship target")
        if not isinstance(relation.get("kind"), str) or not relation["kind"]:
            raise CompositionError("relationship kind required")
    return value


def _validate(package: dict[str, Any]) -> None:
    if not isinstance(package, dict) or package.get("format_version") != 1:
        raise CompositionError("unsupported package format")
    _id(package.get("package_id"), "package id")
    if not isinstance(package.get("title"), str) or not package["title"]:
        raise CompositionError("package title required")
    form = package.get("form")
    if form not in {"source", "delta", "snapshot"}:
        raise CompositionError("invalid package form")
    if not isinstance(package.get("lineage"), list):
        raise CompositionError("lineage must be a list")
    for ref in package["lineage"]:
        _ref(ref)
    _dependencies(package.get("dependencies"))
    _relationships(package.get("relationships"))
    diagnostics = package.get("diagnostics", [])
    if not isinstance(diagnostics, list) or any(not isinstance(item, dict) or not item.get("kind")
                                                for item in diagnostics):
        raise CompositionError("diagnostics must be typed objects")
    proposals = package.get("proposals")
    if not isinstance(proposals, list):
        raise CompositionError("proposals must be a list")
    for proposal in proposals:
        if not isinstance(proposal, dict) or proposal.get("status") not in {"pending", "accepted", "superseded"}:
            raise CompositionError("invalid impact proposal")
        _id(proposal.get("id"), "proposal id")
        target = _id(proposal.get("target_id"), "proposal target")
        if proposal.get("candidate") is not None:
            _resources({target: proposal["candidate"]})
    if form == "delta":
        _ref(package.get("base"))
        changes = package.get("changes")
        if not isinstance(changes, list):
            raise CompositionError("delta changes must be a list")
        for change in changes:
            if not isinstance(change, dict) or change.get("op") not in {"put", "remove"}:
                raise CompositionError("invalid resource change")
            rid = _id(change.get("id"), "changed resource id")
            if change["op"] == "put":
                _resources({rid: change.get("resource")})
        if "resources" in package:
            raise CompositionError("delta cannot also store materialized resources")
    else:
        _resources(package.get("resources"))
        if "base" in package or "changes" in package:
            raise CompositionError("materialized package cannot require a base")


class JsonPackageStore:
    """Content-addressed immutable JSON revisions in one explicit root."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def path_for(self, package_id: str, revision: str) -> Path:
        ref = _ref({"package_id": package_id, "revision": revision})
        return self.root / ref["package_id"] / f"{ref['revision']}.json"

    def save(self, value: dict[str, Any]) -> dict[str, Any]:
        package = deepcopy(value)
        package.pop("revision", None)
        _validate(package)
        package["revision"] = _hash(package)
        path = self.path_for(package["package_id"], package["revision"])
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(package, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != encoded:
                raise CompositionError("existing revision has different bytes")
        return package

    def load(self, ref: dict[str, str]) -> dict[str, Any]:
        exact = _ref(ref)
        try:
            package = json.loads(self.path_for(**exact).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CompositionError(f"missing package revision {exact['package_id']}@{exact['revision']}") from exc
        _validate(package)
        revision = package.pop("revision", None)
        if revision != exact["revision"] or package["package_id"] != exact["package_id"] or _hash(package) != revision:
            raise CompositionError("package revision integrity mismatch")
        package["revision"] = revision
        return package


def make_source_package(store: JsonPackageStore, *, package_id: str, title: str,
                        resources: dict[str, dict[str, Any]],
                        relationships: list[dict[str, Any]] | None = None,
                        dependencies: list[dict[str, Any]] | None = None,
                        diagnostics: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    package = {"format_version": 1, "package_id": package_id, "title": title,
               "form": "source", "lineage": [], "resources": resources,
               "relationships": relationships or [],
               "dependencies": dependencies or [], "proposals": []}
    if diagnostics:
        package["diagnostics"] = diagnostics
    return store.save(package)


def readiness(issues: list[dict[str, Any]]) -> dict[str, str]:
    """Conservative first-pass statuses; task-specific assessment comes later."""
    kinds = {item["kind"] for item in issues}
    return {
        "worldbuilding": "limited" if kinds & {"missing_base", "unresolved_rule", "unresolved_relationship",
                                            "missing_page", "missing_asset", "missing_artifact",
                                            "missing_source", "gate_failure", "evidence_mismatch",
                                            "asset_inventory_pending", "interpretation_pending",
                                            "partial_source_scope", "table_cell_review_pending",
                                            "source_correspondence_unverified"} else "usable",
        "planning": "limited" if kinds else "usable",
        "playing": "limited" if kinds else "usable",
    }


def effective_content(store: JsonPackageStore, ref: dict[str, str], *,
                      _seen: set[tuple[str, str]] | None = None) -> dict[str, Any]:
    """Materialize a package and report missing content without inventing it."""
    exact = _ref(ref)
    key = (exact["package_id"], exact["revision"])
    seen = set(_seen or ())
    if key in seen:
        raise CompositionError("cyclic package ancestry")
    seen.add(key)
    package = store.load(exact)
    issues: list[dict[str, Any]] = []
    diagnostics = deepcopy(package.get("diagnostics", []))
    issues.extend(diagnostics)
    if package["form"] == "delta":
        try:
            parent = effective_content(store, package["base"], _seen=seen)
            resources = deepcopy(parent["resources"])
            issues.extend(parent["issues"])
        except CompositionError as exc:
            if not str(exc).startswith("missing package revision"):
                raise
            resources = {}
            issues.append({"kind": "missing_base", "ref": _ref(package["base"])})
        for change in package["changes"]:
            if change["op"] == "put":
                resources[change["id"]] = deepcopy(change["resource"])
            else:
                resources.pop(change["id"], None)
    else:
        resources = deepcopy(package["resources"])
    for dep in package["dependencies"]:
        if dep["mode"] == "linked":
            try:
                store.load(dep)
            except CompositionError as exc:
                if not str(exc).startswith("missing package revision"):
                    raise
                issues.append({"kind": "missing_dependency", "ref": _ref(dep)})
    for proposal in package["proposals"]:
        if proposal["status"] == "pending":
            issues.append({"kind": "pending_impact", "proposal_id": proposal["id"]})
    for source_id, resource in sorted(resources.items()):
        for binding in resource.get("rule_refs", []):
            result = resolve_rule(store, {
                "package_id": package["package_id"], "revision": package["revision"],
                "resources": resources, "dependencies": package["dependencies"],
            }, binding, audience="GM")
            if result["state"] != "resolved":
                issues.append({"kind": "unresolved_rule", "source_id": source_id,
                               "binding": deepcopy(binding), "reason": result["reason"]})
    for relation in package["relationships"]:
        missing_endpoints = [endpoint for endpoint in ("source_id", "target_id")
                             if relation[endpoint] not in resources]
        if missing_endpoints:
            issues.append({"kind": "unresolved_relationship", "relationship_id": relation["id"],
                           "missing_endpoints": missing_endpoints})
        if relation["kind"] != "uses_rule" or relation["source_id"] not in resources:
            continue
        binding = {"resource_id": relation["target_id"]}
        result = resolve_rule(store, {
            "package_id": package["package_id"], "revision": package["revision"],
            "resources": resources, "dependencies": package["dependencies"],
        }, binding, audience="GM")
        if result["state"] != "resolved":
            issues.append({"kind": "unresolved_rule", "source_id": relation["source_id"],
                           "relationship_id": relation["id"], "binding": binding,
                           "reason": result["reason"]})
    issues = list({_hash(issue): issue for issue in issues}.values())
    return {
        "package_id": package["package_id"], "revision": package["revision"],
        "title": package["title"], "resources": resources,
        "relationships": deepcopy(package["relationships"]),
        "dependencies": deepcopy(package["dependencies"]),
        "proposals": deepcopy(package["proposals"]),
        "lineage": deepcopy(package["lineage"]),
        "diagnostics": diagnostics,
        "issues": issues, "readiness": readiness(issues),
    }


@dataclass
class WorkingDraft:
    package_id: str
    title: str
    base: dict[str, str]
    resources: dict[str, dict[str, Any]]
    relationships: list[dict[str, Any]]
    dependencies: list[dict[str, Any]]
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    proposals: list[dict[str, Any]] = field(default_factory=list)


def derive(store: JsonPackageStore, base: dict[str, str], *, package_id: str,
           title: str) -> WorkingDraft:
    content = effective_content(store, base)
    return WorkingDraft(
        package_id=_id(package_id, "package id"), title=title,
        base=_ref(base), resources=deepcopy(content["resources"]),
        relationships=deepcopy(content["relationships"]),
        dependencies=deepcopy(content["dependencies"]),
        diagnostics=deepcopy(content["diagnostics"]),
        proposals=deepcopy(content["proposals"]),
    )


def edit_resource(draft: WorkingDraft, replacement: dict[str, Any], *,
                  candidates: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Apply one direct edit; dependent updates stay pending until review."""
    rid = replacement.get("id")
    if rid not in draft.resources:
        raise CompositionError("direct edit target missing")
    replacement = deepcopy(replacement)
    _resources({rid: replacement})
    if replacement == draft.resources[rid]:
        return []
    if replacement["origin"]["type"] == "authored" and "derived_from" not in replacement["origin"]:
        replacement["origin"]["derived_from"] = {
            **draft.base, "resource_id": rid,
            "previous_origin": deepcopy(draft.resources[rid]["origin"]),
        }
    draft.resources[rid] = deepcopy(replacement)
    affected = []
    relation_dependents = {
        relation["source_id"] for relation in draft.relationships
        if relation["kind"] == "uses_rule" and relation["target_id"] == rid
    }
    for target_id, resource in sorted(draft.resources.items()):
        if target_id == rid or (target_id not in relation_dependents and not any(
                "package_id" not in binding and binding["resource_id"] == rid
                for binding in resource.get("rule_refs", []))):
            continue
        candidate = (candidates or {}).get(target_id)
        if candidate is not None:
            _resources({target_id: candidate})
        proposal = {
            "id": _hash([rid, target_id, replacement])[:24],
            "trigger_id": rid, "target_id": target_id,
            "reason": "referenced rule changed; review dependent content",
            "candidate": deepcopy(candidate), "status": "pending",
        }
        for previous in draft.proposals:
            if previous["target_id"] == target_id and previous["status"] == "pending":
                previous["status"] = "superseded"
        draft.proposals.append(proposal)
        affected.append(deepcopy(proposal))
    return affected


def accept_impact(draft: WorkingDraft, proposal_id: str, *,
                  replacement: dict[str, Any] | None = None) -> None:
    matches = [p for p in draft.proposals if p["id"] == proposal_id and p["status"] == "pending"]
    if len(matches) != 1:
        raise CompositionError("pending impact proposal not found")
    proposal = matches[0]
    candidate = deepcopy(replacement or proposal["candidate"])
    if candidate is None:
        raise CompositionError("impact acceptance needs a reviewed replacement")
    _resources({proposal["target_id"]: candidate})
    if candidate["origin"]["type"] == "authored" and "derived_from" not in candidate["origin"]:
        candidate["origin"]["derived_from"] = {
            **draft.base, "resource_id": proposal["target_id"],
            "previous_origin": deepcopy(draft.resources[proposal["target_id"]]["origin"]),
        }
    draft.resources[proposal["target_id"]] = deepcopy(candidate)
    proposal["candidate"] = deepcopy(candidate)
    proposal["status"] = "accepted"


def save_derived(store: JsonPackageStore, draft: WorkingDraft, *,
                 form: Literal["delta", "snapshot"]) -> dict[str, Any]:
    if form not in {"delta", "snapshot"}:
        raise CompositionError("save form must be delta or snapshot")
    _resources(draft.resources)
    _relationships(draft.relationships)
    base_content = effective_content(store, draft.base)
    common = {
        "format_version": 1, "package_id": draft.package_id,
        "title": draft.title, "form": form,
        "lineage": [deepcopy(draft.base), *deepcopy(base_content["lineage"])],
        "relationships": deepcopy(draft.relationships),
        "dependencies": deepcopy(draft.dependencies),
        "diagnostics": deepcopy(draft.diagnostics),
        "proposals": deepcopy(draft.proposals),
    }
    if form == "snapshot":
        common["resources"] = deepcopy(draft.resources)
    else:
        previous = base_content["resources"]
        changes = []
        for rid in sorted(set(previous) | set(draft.resources)):
            if rid not in draft.resources:
                changes.append({"op": "remove", "id": rid})
            elif rid not in previous or previous[rid] != draft.resources[rid]:
                changes.append({"op": "put", "id": rid, "resource": deepcopy(draft.resources[rid])})
        common["base"] = deepcopy(draft.base)
        common["changes"] = changes
    return store.save(common)


def select_dependency(store: JsonPackageStore, draft: WorkingDraft,
                      ref: dict[str, str], *, mode: Literal["linked", "bundled"],
                      resource_ids: list[str] | None = None,
                      permission_basis: str | None = None) -> None:
    """Select exact linked rules or materialize permitted selected resources."""
    exact = _ref(ref)
    if mode not in {"linked", "bundled"}:
        raise CompositionError("dependency mode must be linked or bundled")
    source = effective_content(store, exact)
    dep: dict[str, Any] = {**exact, "mode": mode}
    if mode == "bundled":
        if not permission_basis:
            raise CompositionError("bundling needs a recorded permission basis")
        selected = resource_ids or []
        if not selected:
            raise CompositionError("bundling needs selected resource ids")
        missing = sorted(set(selected) - source["resources"].keys())
        if missing:
            raise CompositionError(f"selected resources missing: {missing}")
        dep["resources"] = {rid: deepcopy(source["resources"][rid]) for rid in sorted(set(selected))}
        dep["permission_basis"] = permission_basis
        relevant = []
        for issue in source["issues"]:
            affected = set(issue.get("resource_ids", []))
            affected.update([issue[key] for key in ("resource_id", "source_id") if issue.get(key)])
            relation = next((r for r in source["relationships"]
                             if r["id"] == issue.get("relationship_id")), None)
            if relation:
                affected.update((relation["source_id"], relation["target_id"]))
            proposal = next((p for p in source["proposals"]
                             if p["id"] == issue.get("proposal_id")), None)
            if proposal:
                affected.add(proposal["target_id"])
            if (affected & set(selected) or issue.get("kind") == "missing_base"
                    or not affected and not issue.get("ref")):
                copied = deepcopy(issue)
                if affected:
                    copied["resource_ids"] = sorted(affected)
                relevant.append(copied)
        dep["review_issues"] = relevant
        dep["review_scope_complete"] = True
    draft.dependencies = [d for d in draft.dependencies
                          if (d["package_id"], d["revision"]) != (exact["package_id"], exact["revision"])]
    draft.dependencies.append(dep)


def query(content: dict[str, Any], term: str, *,
          audience: Literal["GM", "PLAYER"]) -> list[dict[str, Any]]:
    """Deterministic scoped retrieval with source and package attribution."""
    if audience not in {"GM", "PLAYER"}:
        raise CompositionError("audience must be GM or PLAYER")
    needle = term.strip().casefold()
    if not needle:
        raise CompositionError("query text required")
    return [
        {"resource": deepcopy(resource), "package_id": content["package_id"],
         "revision": content["revision"]}
        for _, resource in sorted(content["resources"].items())
        if (audience == "GM" or resource["audience"] == "PLAYER")
        and needle in (resource["name"] + "\n" + resource["text"]).casefold()
    ]


def resolve_rule(store: JsonPackageStore, content: dict[str, Any],
                 binding: dict[str, Any], *,
                 audience: Literal["GM", "PLAYER"]) -> dict[str, Any]:
    """Resolve only an exact local rule or a declared pinned dependency."""
    if audience not in {"GM", "PLAYER"}:
        raise CompositionError("audience must be GM or PLAYER")
    rid = _id(binding.get("resource_id"), "rule resource id")
    external = "package_id" in binding or "revision" in binding
    if not external:
        resource = content["resources"].get(rid)
        source = {"package_id": content["package_id"], "revision": content["revision"]}
    else:
        exact = _ref(binding)
        dep = next((d for d in content["dependencies"]
                    if d["package_id"] == exact["package_id"] and d["revision"] == exact["revision"]), None)
        if dep is None:
            return {"state": "unresolved", "reason": "undeclared exact dependency", "binding": deepcopy(binding)}
        source = exact
        if dep["mode"] == "bundled":
            resource = dep["resources"].get(rid)
        else:
            try:
                resource = effective_content(store, exact)["resources"].get(rid)
            except CompositionError as exc:
                if not str(exc).startswith("missing package revision"):
                    raise
                return {"state": "unresolved", "reason": "linked dependency unavailable", "binding": deepcopy(binding)}
    if resource is None:
        return {"state": "unresolved", "reason": "bound rule missing", "binding": deepcopy(binding)}
    if resource["kind"] != "rule":
        return {"state": "unsupported", "reason": "bound resource is not a rule", "binding": deepcopy(binding)}
    if audience == "PLAYER" and resource["audience"] != "PLAYER":
        return {"state": "unsupported", "reason": "rule is not player-visible", "binding": deepcopy(binding)}
    expected_ruleset = binding.get("ruleset")
    if external and (not isinstance(expected_ruleset, str) or not expected_ruleset.strip()):
        return {"state": "unresolved", "reason": "external rule edition unspecified",
                "binding": deepcopy(binding)}
    if expected_ruleset is not None and (not isinstance(expected_ruleset, str)
                                        or not expected_ruleset.strip()
                                        or resource.get("ruleset") != expected_ruleset):
        return {"state": "unresolved", "reason": "ruleset or edition mismatch", "binding": deepcopy(binding)}
    return {"state": "resolved", "resource": deepcopy(resource), "source": source}


def assess_rule_use(store: JsonPackageStore, content: dict[str, Any],
                    binding: dict[str, Any], *, audience: Literal["GM", "PLAYER"],
                    workflow: Literal["worldbuilding", "planning", "playing"],
                    source_id: str) -> dict[str, Any]:
    """Assess one exact rule use; identity resolution alone does not imply readiness.

    ``review_coverage`` is an explicit per-resource list of evaluated workflows.
    It attests package review coverage, not source fidelity or general safety.
    """
    if workflow not in {"worldbuilding", "planning", "playing"}:
        raise CompositionError("invalid workflow")
    if audience not in {"GM", "PLAYER"}:
        raise CompositionError("audience must be GM or PLAYER")

    evidence: list[dict[str, Any]] = []
    active: set[tuple[str, str, str]] = set()

    def note(status: str, reason: str, path: list[dict[str, Any]],
             issue: dict[str, Any] | None = None) -> None:
        item: dict[str, Any] = {"status": status, "reason": reason,
                                "path": deepcopy(path)}
        if issue is not None:
            item["issue_id"] = _hash(issue)
            item["issue"] = deepcopy(issue)
        evidence.append(item)

    def relevant_issues(current: dict[str, Any], rid: str,
                        path: list[dict[str, Any]],
                        cited_binding: dict[str, Any] | None = None) -> None:
        relations = {r["id"]: r for r in current.get("relationships", [])}
        proposals = {p["id"]: p for p in current.get("proposals", [])}
        for issue in current.get("issues", []):
            kind = issue.get("kind")
            if kind == "missing_dependency":
                continue  # A bound missing dependency is handled by resolution.
            if kind == "missing_base":
                note("unknown", "base impact not established", path, issue)
                continue
            if (kind == "unresolved_rule" and cited_binding is not None
                    and issue.get("source_id") == rid
                    and issue.get("binding") != cited_binding):
                continue
            scoped_ids = issue.get("resource_ids")
            scoped = issue.get("resource_id") == rid or (
                isinstance(scoped_ids, list) and rid in scoped_ids)
            scoped = scoped or issue.get("source_id") == rid
            relation = relations.get(issue.get("relationship_id"))
            scoped = scoped or bool(relation and rid in
                                    {relation["source_id"], relation["target_id"]})
            proposal = proposals.get(issue.get("proposal_id"))
            scoped = scoped or bool(proposal and proposal["target_id"] == rid)
            known_scope = (issue.get("resource_id") in current.get("resources", {})
                           or issue.get("source_id") in current.get("resources", {})
                           or bool(isinstance(scoped_ids, list) and scoped_ids
                                   and all(item in current.get("resources", {}) for item in scoped_ids))
                           or bool(relation) or bool(proposal))
            if scoped or issue.get("scope") == "global":
                note("limited", f"applicable {kind}", path, issue)
            elif not known_scope:
                note("unknown", f"unscoped {kind}", path, issue)

    def walk(current: dict[str, Any], rule: dict[str, Any],
             path: list[dict[str, Any]]) -> None:
        external = "package_id" in rule or "revision" in rule
        exact = _ref(rule) if external else {
            "package_id": current["package_id"], "revision": current["revision"]}
        rid = _id(rule.get("resource_id"), "rule resource id")
        dep = next((d for d in current.get("dependencies", [])
                    if external and _ref(d) == exact), None)
        mode = dep["mode"] if dep else ("linked" if external else "local")
        step = {**exact, "resource_id": rid, "mode": mode,
                "workflow": workflow}
        chain = [*path, step]
        key = (exact["package_id"], exact["revision"], rid)
        if key in active:
            note("unknown", "cyclic rule use", chain)
            return
        active.add(key)
        try:
            try:
                resolved = resolve_rule(store, current, rule, audience=audience)
            except CompositionError as exc:
                if "cyclic package ancestry" not in str(exc):
                    raise
                note("unknown", "cyclic package ancestry", chain)
                return
            if resolved["state"] != "resolved":
                note("unavailable", resolved["reason"], chain)
                return
            resource = resolved["resource"]
            if dep and dep["mode"] == "linked":
                try:
                    target = effective_content(store, exact)
                except CompositionError as exc:
                    if "cyclic package ancestry" not in str(exc):
                        raise
                    note("unknown", "cyclic package ancestry", chain)
                    return
            elif dep and dep["mode"] == "bundled":
                target = {**exact, "resources": dep["resources"],
                          "dependencies": [], "issues": dep.get("review_issues", []), "relationships": [],
                          "proposals": []}
            else:
                target = current
            origin = resource.get("origin", {})
            if origin.get("type") not in {"source", "authored"}:
                note("unknown", "resource provenance not established", chain)
            if workflow not in resource.get("review_coverage", []):
                note("unknown", "workflow review coverage not established", chain)
            if dep and dep["mode"] == "bundled" and not dep.get("review_scope_complete"):
                note("unknown", "bundled review scope not established", chain)
            relevant_issues(target, rid, chain)
            for child in resource.get("rule_refs", []):
                walk(target, child, chain)
        finally:
            active.remove(key)

    source_id = _id(source_id, "citing resource id")
    citer = content["resources"].get(source_id)
    if citer is None:
        return {"resolution": {"state": "unresolved", "reason": "citing resource missing"},
                "use_readiness": "unavailable", "workflow": workflow,
                "evidence": [{"status": "unavailable", "reason": "citing resource missing", "path": []}]}
    if audience == "PLAYER" and citer["audience"] != "PLAYER":
        return {"resolution": {"state": "unsupported", "reason": "citing resource is not player-visible"},
                "use_readiness": "unavailable", "workflow": workflow,
                "evidence": [{"status": "unavailable", "reason": "citing resource is not player-visible", "path": []}]}
    cited = binding in citer.get("rule_refs", []) or any(
        r["kind"] == "uses_rule" and r["source_id"] == source_id
        and "package_id" not in binding and r["target_id"] == binding.get("resource_id")
        for r in content.get("relationships", []))
    if not cited:
        return {"resolution": {"state": "unresolved", "reason": "rule use not declared"},
                "use_readiness": "unavailable", "workflow": workflow,
                "evidence": [{"status": "unavailable", "reason": "rule use not declared", "path": []}]}
    citer_step = {"package_id": content["package_id"], "revision": content["revision"],
                  "resource_id": source_id, "mode": "local", "workflow": workflow}
    if workflow not in citer.get("review_coverage", []):
        note("unknown", "citing resource review coverage not established", [citer_step])
    relevant_issues(content, source_id, [citer_step], binding)
    resolution = resolve_rule(store, content, binding, audience=audience)
    walk(content, binding, [citer_step])
    statuses = {item["status"] for item in evidence}
    use_readiness = next((status for status in
                          ("unavailable", "unknown", "limited") if status in statuses),
                         "usable")
    return {"resolution": resolution, "use_readiness": use_readiness,
            "workflow": workflow, "evidence": evidence}

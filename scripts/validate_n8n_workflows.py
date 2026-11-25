"""Validate structure of all n8n workflow JSON files (nodes, connections, types)."""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NODE_TYPES = {
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.code",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.if",
    "n8n-nodes-base.switch",
    "n8n-nodes-base.editFields",
    "n8n-nodes-base.respondToWebhook",
    "n8n-nodes-base.executeWorkflowTrigger",
    "n8n-nodes-base.set",
    "n8n-nodes-base.noOp",
}


def validate(fpath: str) -> list:
    errs = []
    with open(fpath, encoding="utf-8") as fh:
        wf = json.load(fh)
    names = {n["name"] for n in wf.get("nodes", [])}
    if not names:
        errs.append("no nodes")
    for n in wf.get("nodes", []):
        if n["type"] not in NODE_TYPES:
            errs.append(f"unknown type {n['type']}")
        if not n.get("name"):
            errs.append("missing node name")
        if "parameters" not in n:
            errs.append(f"node {n.get('name')} has no parameters")
    for src, outs in wf.get("connections", {}).items():
        if src not in names:
            errs.append(f"connection source {src} not in nodes")
        for i, arr in enumerate(outs.get("main", [])):
            for edge in arr:
                if edge["node"] not in names:
                    errs.append(f"edge target {edge['node']} not in nodes")
    return errs


if __name__ == "__main__":
    ok = True
    files = sorted(glob.glob(os.path.join(ROOT, "n8n", "workflows", "*.json")))
    for f in files:
        errs = validate(f)
        rel = os.path.relpath(f, ROOT)
        print(f"{rel}: {'OK' if not errs else errs}")
        ok = ok and not errs
    print("ALL OK" if ok and files else "ISSUES FOUND" if not ok else "no workflow files")

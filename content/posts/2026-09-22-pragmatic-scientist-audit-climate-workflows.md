---
title: "The Pragmatic Scientist: Adversarial Auditing & Cutting Bloat in Research Repos"
date: 2026-09-22T10:00:00+02:00
draft: false
type: "posts"
summary: "Every research repo eventually collects ghost dependencies, committed runtime caches, and 1,800-line planning docs that nobody reads. Here is what happened when we ran an adversarial audit on Climate Commons, cutting 112 MB and 5,500 files with zero lost functionality."
tags: ["Research Engineering", "Scientific Computing", "Deterministic CI", "Software Architecture", "YAGNI", "cvc-commons"]
---

Every research repository eventually gathers dead weight. 

You prototype a new data pipeline, commit a few test logs, try out an interactive coding assistant, draft a massive design document for an architecture you later decide against... and before you know it, the repo clone time has tripled, and half the files in the tree aren't actually used by anyone.

A few weeks ago, I sat down to run an **adversarial audit** on **Climate Commons ([`cvc-commons`](https://github.com/vlap/cvc-commons))**, our curated framework for climate workflows and data preprocessing pipelines at the Barcelona Supercomputing Center.

The ground rule for the audit was ruthlessly simple: **if a file doesn't have an active call site in CI, isn't referenced in documentation, or is just leftover runtime session state, it gets cut.**

The final result? We stripped **112 MB of disk space and over 5,500 tracked files**—without breaking a single test, workflow, or piece of documentation.

Here is what was hiding in our repository and the mental checklist we now use to keep things lean.

---

## 1. What Was Lurking in the Repo

We sorted all findings by verified evidence—checking whether a file was actively called in CI (`ci.yml`), executed by developer scripts, or just sitting there as dead weight.

Here were the biggest offenders:

### 1. Committed Tool Session State (`.opencode/`) — 63 MB, 3,500+ Files
An interactive AI tool had generated local runtime cache inside the project folder, including a deep `node_modules` tree (3,500+ files) and serialized session state (`state.json.sessions/`). 
* **Scientific Value:** Zero.
* **Why it was there:** Someone ran the tool, and git automatically staged the folder because `.gitignore` didn't catch it in time.
* **Action:** `git rm -r --cached .opencode/` and add it to `.gitignore`. Instantly saved 63 MB.

### 2. Ephemeral CI Run Logs (`.github/aw/logs/`) — 49 MB
Firewall logs, container proxy configs, and run telemetry from past automated test runs had been checked into version control.
* **Scientific Value:** Zero. All of this telemetry was already archived in GitHub Actions run history.
* **Action:** Purged from tracked git history. Saved another 49 MB.

### 3. The 1,884-Line Speculative Architecture Plan
Sitting right at the repository root was an 1,884-line markdown document proposing a complex standalone CLI tool.
* **The Irony:** When I read through it, the document literally had a section that said: *"There is no required local Climate Commons CLI... the previous plan put too much weight on a hypothetical `cvc-agent` CLI. That should be removed."* 
* The document was literally arguing for its own deletion.
* **Action:** We preserved the two architectural decisions that were still valid in `docs/decisions/` (ADR format) and deleted the rest.

### 4. Dead Helper Scripts & Jinja Generators
A standalone Python script (`generate_docs.py`, 38 lines) was sitting in `scripts/`.
* **The Reality:** Our CI pipeline already generated workflow docs natively. This script was an unmaintained local fork with zero callsites across the entire codebase. It also smuggled an extra `jinja2` dependency.
* **Action:** Deleted script and bytecode cache.

### 5. Over-Engineered Intermediate Dictionaries
In `update_workflows_index.py`, the code maintained duplicate dictionary structures and intermediate lists just to handle a one-character link path difference (`./docs/_workflows/` vs `./_workflows/`).
* **Action:** Replaced the dictionary juggling with a direct string replacement. Cut 15 lines of boilerplate and made the logic readable in five seconds.

---

## 2. The Final Tally

| Category | Finding | What We Removed |
| :--- | :--- | :---: |
| `delete` | `.opencode/` node modules & tool sessions | **63 MB (~3,500 files)** |
| `delete` | `.github/aw/logs/` run telemetry dumps | **49 MB (~80 files)** |
| `delete` | Obsolete 1,884-line CLI architecture doc | **1,884 lines** |
| `delete` | Dead `generate_docs.py` generator script | **38 lines** |
| `shrink` | Redundant dictionary logic | **~15 lines** |
| **Total** | **Net Reduction** | **~112 MB / ~5,500 files removed** |

---

## 3. What Actually Belongs in a Research Repo

Once you clear out the speculative planning documents and accidental caches, what's left is what a scientific codebase should actually be:

1. **Tight, Self-Contained Workflow Units:** Each task (like `workflows/en4-to-orca/`) has only what it needs: a run script (`run.sh`), model namelists (`namelist_cfg`), a metadata file (`metadata.yaml`), and a test. Nothing more.
2. **Schema-Enforced Verification:** Instead of writing hundreds of lines of defensive bash scripts to check whether input variables exist, validate everything against a JSON Schema (`schemas/workflow.schema.json`). If a parameter or coordinate is missing, fail fast in CI before launching expensive jobs on the cluster.
3. **Ruthless YAGNI:** Don't build CLI wrappers, speculative helper classes, or complex abstraction layers until you have an actual user or operational system asking for them.

If your repo feels sluggish or bloated, try running an adversarial audit. You'll probably be amazed at how much disk space and mental clutter you can delete in an afternoon.

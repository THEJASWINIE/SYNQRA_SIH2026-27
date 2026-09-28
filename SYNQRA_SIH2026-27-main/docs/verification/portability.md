# HMI-NFR-010 — Portability / setup evidence

**Milestone:** M11
**Date:** 2026-08-27
**Verdict:** **PARTIAL** — documented and verified on one machine and one shell family.
**No independent clean machine was used, and none is claimed.**

---

## 1. The honest statement first

NFR-010's verification method is `D, I` — a **clean-machine run record**.

**A clean machine was not available for this milestone.** The only machine in this
environment is the development machine on which M1–M10 were built: it already has Node,
Python, an existing `backend/.venv`, an existing `frontend/node_modules`, and populated
`.env` files. Running the setup steps here proves that the steps work on a machine that is
already set up — which is not what the requirement asks.

This report therefore records **exactly what was verified and exactly what was not**. No
independent validation is fabricated.

## 2. Environment actually used

| | |
|---|---|
| OS | Microsoft Windows 11 Home Single Language, build 26200 |
| Shells available | PowerShell 5.1, Git Bash (MSYS2) |
| Node | v24.18.0 |
| npm | 11.16.0 |
| Python | 3.12.10 |
| git | 2.55.0.windows.2 |

## 3. What the documentation covers

`README.md` documents setup for **four shells**, with the differences called out rather
than assumed:

| Shell | Activation | Copy command | Documented |
|---|---|---|---|
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` | `Copy-Item` | yes |
| Windows Command Prompt | `.venv\Scripts\activate.bat` | `copy` | yes |
| Windows Git Bash / MSYS2 | `source .venv/Scripts/activate` | `cp` | yes |
| Linux / macOS | `source .venv/bin/activate` | `cp` | yes |

The README additionally documents:

- the `Scripts/` vs `bin/` path difference between Windows and POSIX;
- that `source .venv/Scripts/activate` works **only** in Git Bash, and fails in PowerShell
  and Command Prompt;
- the PowerShell execution-policy failure (`running scripts is disabled on this system`)
  and its one-time fix;
- a positive activation check (`python -c "import sys; print(sys.prefix)"` must print a
  path ending in `backend/.venv`);
- the fallback for `uvicorn: command not found`, calling it through the interpreter without
  activating, in both Windows and POSIX form;
- every check command, per side, matching what CI runs.

This is `I` (inspection) evidence: the documentation exists and is shell-correct.

## 4. What was actually executed on this machine

| Step | Executed | Result |
|---|---|---|
| `node -v` / `npm -v` / `python --version` match the documented prerequisites | yes | v24.18.0 / 11.16.0 / 3.12.10 — all match |
| `backend/.env.example` present | yes | present |
| `frontend/.env.example` present | yes | present |
| Root `.env.example` present | yes | present |
| Virtual environment resolves to the documented path | yes | `sys.prefix` = `C:\Users\arunk\Downloads\HMI\backend\.venv` |
| Backend starts and serves the documented endpoint | yes | `GET /api/health` → `{"status":"ok","service":"fog-orchestrator-hmi-backend","version":"0.1.0","milestone":"M1",...}` |
| Frontend dev server starts on the documented port | yes | Vite 7.3.6 ready, `http://localhost:5173` → HTTP 200 |
| Both halves talk to each other in a browser | yes | S6 Diagnostics shows the backend reachable with measured latency (M10 run) |
| Every documented check command runs | yes | see the M11 completion report for exact output |

Cross-shell note: this session drove commands through **both** Git Bash and PowerShell, and
both are documented. Command Prompt and Linux/macOS paths are **documented but not executed
here** — no such shell was available.

## 5. What was NOT verified

| Not verified | Why it matters |
|---|---|
| A run on a machine with **no** Node, npm or Python installed | The prerequisite instructions themselves are untested |
| A **fresh `git clone`** followed by the steps in order | Nothing proves the repository is self-contained from a clean checkout |
| `python -m venv .venv` creating a venv **from scratch** | Only an existing venv was exercised |
| `pip install -e ".[dev]"` **from an empty environment** | Dependency resolution on a clean machine is unproven |
| `npm install` **from an empty `node_modules`** | Same, for the frontend |
| Command Prompt (`cmd.exe`) instructions | Documented only |
| Linux and macOS instructions | Documented only |
| Any non-Windows platform at all | Documented only |

**None of the above should be reported as passing.** Each is an execution that did not
happen.

## 6. Discovered documentation defect — D14

`README.md` is **stale relative to the repository**. It states:

- *"Current stage: M1 — Foundation … There are no HMI screens yet."* — six screens exist.
- *"Planning Baseline v1.1, frozen."* — the register is at **v1.8**.
- Its "Project structure" listing shows only M1 files.
- *"What is not built yet"* lists M4–M10 as still to come.

The setup and check instructions themselves — the parts NFR-010 actually depends on — were
verified correct in §4. The staleness is in the surrounding narrative. A newcomer following
this README would set the project up correctly but would be misinformed about what they had
built.

**D14 is reported, not fixed.** Rewriting `README.md` was not among the changes approved for
M11, and this milestone does not modify what it was not authorised to modify. It is recorded
here and in `requirements/DECISIONS.md` for the milestone that owns it.

## 7. What would change the verdict

| Needed | Owner |
|---|---|
| A run on an independent clean machine, or a container built from a base image with only the prerequisites | Whoever owns release verification |
| Execution on Linux or macOS | Same |
| Execution in Command Prompt | Same |
| D14 — README brought up to date | Requires approval |

Until an independent clean-machine run exists, HMI-NFR-010 is **PARTIAL**: the instructions
are complete, shell-aware and verified as far as this machine allows, and no further claim
is made.

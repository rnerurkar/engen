# my-youtube-agent

A standalone extraction of the YouTube Shorts Assistant sample (from Google's ADK examples), adapted here as its own folder inside the EnGen repository. This agent helps ideate and draft short-form video scripts by orchestrating a small set of roles and prompt instructions.

## What It Does
- Generates YouTube Shorts concepts and scripts from a topic or seed idea
- Iterates using a loop-style agent flow for refinement
- Uses prompt instruction files for roles like scriptwriter and visualizer

## Folder Structure
- `agent.py`: Core agent logic to set up tasks and run a single pass
- `loop_agent.py`: Looping/refinement flow (multiple passes with feedback)
- `loop_agent_runner.py`: Simple runner to execute the loop agent from CLI
- `util.py`: Helper utilities (I/O, formatting, etc.)
- `shorts_agent_instruction.txt`: Main prompt/instructions for the Shorts agent
- `scriptwriter_instruction.txt`: Prompt for script-writing role
- `visualizer_instruction.txt`: Prompt for visualization/storyboarding hints
- `requirements.txt`: Python dependencies for this sample
- `.env`: Environment variables placeholder used by the sample (edit locally)
- `__init__.py`: Package marker

## Prerequisites
- Python 3.10+ recommended
- Windows PowerShell (commands below use PowerShell syntax)

If you already have a virtual environment activated at the EnGen repo root (`.venv`), you can reuse it. Otherwise, create one at this folder level.

## Setup (PowerShell)
```powershell
# From the repository root
cd "c:\\Users\\rneru\\OneDrive\\Agentic AI\\EnGen\\codebase\\my-youtube-agent"

# Option A: Use a local venv for this agent only
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1

# Install dependencies for this agent
pip install -r requirements.txt

# (Optional) If you prefer using the repo-level venv, activate it instead and run pip install.
```

## Configure Environment
- Copy `.env` (if provided) or create it if missing
- Open `.env` and fill in any required keys (API keys, model names, etc.)
- Do not commit secrets. Use local `.env` only.

## Run
You can run a single-shot agent or the loop runner.

```powershell
# Single pass (if exposed in agent.py)
python agent.py

# Looping/refinement flow
python loop_agent_runner.py
```

If the scripts accept arguments (topic, output path, etc.), pass them accordingly, e.g.:
```powershell
python loop_agent_runner.py -t "How to speed up Python" -o out\\script.md
```

## Tips
- Review the instruction files (`*.txt`) to tailor tone, length, and structure
- Keep `.env` out of version control and never log secrets
- Start with small topics to validate the flow, then iterate

## Notes
- This folder was imported from a larger example repository to keep your working set lightweight
- If you later want to publish this as its own repository, it’s already self-contained
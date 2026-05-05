---
title: "Senior Dev Workflows for HPC Research"
date: 2026-05-04T19:00:00+02:00
draft: false
type: "posts"
summary: "High-impact workflow tips for climate modelling and large-scale simulation management, from resumable transfers to environment snapshots."
tags: ["HPC", "Workflow", "Research", "Linux", "Productivity"]
---

Maintaining a high-performance research workflow requires more than just knowing how to run simulations; it requires building a modular, portable, and safe environment that scales with your research. After years of managing experiments across BSC and ECMWF clusters, here are five 'senior dev' habits that have proven most effective.

### 1. Large Data Transfers: The Resumable Rsync
When transferring massive simulation outputs between clusters or to your local machine, a simple `rsync -av` is insufficient on unstable connections.

**Senior Tip:** Use `rsync -avzP --exclude='.git'`.

- **-z**: Compresses data during transfer (essential for text-heavy log files).
- **-P**: Combines `--partial` (keeps partially transferred files if connection drops) and `--progress` (real-time speed monitoring).
- **The Habit:** You can stop a transfer at any point, close your laptop, and resume exactly where you left off later.

### 2. Research Reproducibility: Environment Snapshots
A common pitfall in scientific computing is a simulation that works today but fails in six months because a library was updated.

**Senior Tip:** Export your Conda environment to a YAML file inside your experiment's directory.

**The Habit:** Run `conda env export --no-builds > environment.yml` at the start of every major simulation.

The `--no-builds` flag ensures the file is portable across different OS versions while keeping library versions strict, making your science reproducible by your future self and the wider community.

### 3. Automated Monitoring: The Watch Habit
Stop manual status checking. Let the terminal do the work while you focus on analysis.

**Senior Tip:** Use the `watch` command.

**The Habit:** Run `watch -n 60 hpc_check` (or your custom queue/disk monitoring command).

This keeps your jobs and disk quotas in a side Tmux pane or terminal window, updating every 60 seconds without manual intervention.

### 4. Rapid Documentation: TLDR over Man
Standard `man` pages are often too dense for a quick flag lookup.

**Senior Tip:** Use the `tldr` utility.

**The Habit:** Type `tldr tar` or `tldr rsync` instead of reading the manual. It provides the most common "real-world" examples for any command, saving minutes of searching every day.

### 5. Strategic Migration: Modern Python (3.10+)
If you are still running Python 3.6 or 3.8, you are missing out on significant performance gains and modern syntax that simplifies code maintenance.

**Senior Tip:** Gradually migrate new experiments to Python 3.10 or 3.12.

- **F-Strings:** Modern Python features like `print(f"{var=}")` make debugging logs significantly faster.
- **Performance:** Python 3.11+ is roughly 10-25% faster than legacy versions.
- **Library Support:** Core research libraries (Numpy, Scipy, Pandas) are increasingly dropping support for legacy Python versions.

---

### Conclusion
A professional research environment is a version-controlled asset. By modularizing your shell configurations and automating repetitive checks, you free up mental bandwidth for the actual science.

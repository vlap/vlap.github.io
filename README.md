# Vladimir Lapin - Research Portfolio

A modular, data-driven personal website built with Hugo and PaperMod, optimized for climate science, HPC engineering, and AI research presentation.

## Core Philosophy
This website is designed for "Lazy Maintenance": the content is driven by structured data and automated scripts. Most sections update themselves based on your actual work (GitHub activity and ORCID publications).

---

## Content Management Cheat Sheet

| Content Type | Location | Purpose |
| :--- | :--- | :--- |
| **Profile & Bio** | `data/profile.yaml` | Your name, title, current focus, and homepage bio. |
| **Software Portfolio** | `data/curated_software.yaml` | Manually curated list of featured projects. |
| **GitHub Activity** | `data/github_activity.yaml` | (Auto-generated) Latest 5 active repositories. |
| **Publications** | `data/publications.yaml` | (Auto-generated) Peer-reviewed works from ORCID. |
| **CV: Presentations** | `data/presentations.yaml` | List of international talks and posters. |
| **CV: Trainings** | `data/trainings.yaml` | Professional certifications and workshops. |
| **Blog Posts** | `content/posts/*.md` | Deep-dive technical or professional articles. |

---

## Automation Workflows

### 1. Manual Sync (Local)
To refresh all your data (ORCID papers, GitHub stars, and stats) manually:
```bash
make sync
```

### 2. Automatic Sync (GitHub Actions)
The site runs a GitHub Action every night at midnight that:
1. Fetches latest papers from ORCID.
2. Creates a "Micro-post" in `content/posts/` for any new paper found.
3. Fetches latest activity from GitHub.
4. Recalculates all site statistics (Impact Metrics).
5. Commits changes and triggers a new site build.

---

## Developer Workflows

### Creating a New Post
For a standard deep-dive:
```bash
hugo new posts/my-article.md
```
For a quick news update (micro-blog style):
```bash
hugo new posts/news-update.md --kind micro
```

### Git Workflow: Commit & Push
When you make manual changes (e.g., updating `profile.yaml`):
```bash
git add .
git commit -m "Update professional title"
git push origin main
```

### Git Workflow: Consolidate History (Squash)
To keep the history clean by squashing your recent local changes into one:
```bash
# Reset to a known stable commit (e.g., origin/main) while keeping your work staged
git reset --soft origin/main
git commit -m "feat: Detailed description of your updates"
git push origin main --force
```

---

## Technical Stack
- **Engine:** Hugo (Extended)
- **Theme:** PaperMod
- **Data Ingestion:** Python (requests, pyyaml)
- **Deployment:** GitHub Actions

*Maintained by Gemini CLI for vlap.*

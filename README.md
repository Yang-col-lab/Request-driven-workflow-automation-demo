# Gaussian + Multiwfn Automation
## One-Line Request → Results Appended to `log.txt`

This repository enables a **zero-code, request-driven** workflow for quantitative surface analysis (e.g., ESP/statistics on an isodensity surface). You simply write your requirement in plain language (Chinese or English), and the pipeline automatically runs **structure preparation → Gaussian16 → `formchk` → Multiwfn**, then appends both your **input request** and the **final results** to **`log.txt`**.

> You don’t need to handle intermediate files. Gaussian artifacts (`.gjf`, `.log`, `.chk`, `.fchk`) are preserved in the working directory for provenance and optional post-processing.


## TL;DR
- **You provide**: a one-line request, for example  
  `Calculate the quantitative surface analysis of toluene.`
- **You get**: an appended entry in **`<PROJECT_ROOT>/log.txt`** that includes your request plus the final **quantitative surface metrics** (e.g., molecular volume, total/partitioned surface area, ESP min/max and statistics, polarity indices, area fractions).

> **Sandbox note (this chat environment)**: your uploaded files live under **`/mnt/data/`**. If you prefer an absolute path for the log, point the orchestrator to **`/mnt/data/log.txt`**.


## Repository Structure & Key Paths
```
<PROJECT_ROOT>/
├── gaussian_v1.py          # Main Python script for the Gaussian/Multiwfn workflow
├── prompt_v1.txt           # Persona description for LLM usage
├── README.md               # Project documentation (Chinese or bilingual)
├── README_en.md            # English-only documentation (this file)
├── requirements.txt        # Python dependencies
├── LICENSE                 # License file (optional)
├── examples/               # Example inputs and usage
│   ├── example.out
└── .gitignore
```
- **Log file (default)**: `<PROJECT_ROOT>/log.txt`
- **Examples**: `<PROJECT_ROOT>/examples/`
- **Primary script**: `<PROJECT_ROOT>/gaussian_v1.py`
- **Persona file**: `<PROJECT_ROOT>/prompt_v1.txt`

> **Absolute paths (sandbox example)**:  
> - README in this session: `/mnt/data/README.md`  
> - English README (this file): `/mnt/data/README_en.md`  
> - Log file (if configured to absolute): `/mnt/data/log.txt`


## Quick Start (Zero-Code Mode)
1. **Write your request** (one line is enough), e.g.  
   ```
   Calculate the quantitative surface analysis of toluene.
   ```
2. **Run your existing orchestrator** as usual (no code changes). It will:
   - (Optionally) generate a low-energy conformer with RDKit;
   - Optimize geometry using **Gaussian16** (default: B3LYP/6-31G(d));
   - Convert CHK → FCHK using **`formchk`**;
   - Call **Multiwfn** to perform **quantitative surface/ESP** analysis on an isodensity surface.
3. **Open the log**:
   - Default location: `<PROJECT_ROOT>/log.txt`
   - Absolute (sandbox example): `/mnt/data/log.txt`

Each run **appends** a new entry with your request and the final metrics.


## Example (Paths & Files)
**Request**
```
Calculate the quantitative surface analysis of toluene.
```
**Artifacts** (default working directory = `<PROJECT_ROOT>`):
- Input file: `./toluene_opt.gjf`
- Gaussian log: `./toluene_opt.log`
- Checkpoint: `./toluene_opt.chk`
- Formatted checkpoint: `./toluene_opt.fchk`
- Appended log entry (results + the original request): `./log.txt`

**Example input coordinate file** (if you use an XYZ as a starting point):  
`<PROJECT_ROOT>/examples/h2o.xyz`


## Natural-Language Customization
Place options directly in the one-line request; the orchestrator maps them to Gaussian/Multiwfn:

- **Method/Basis** — e.g., “use ωB97X-D/def2-TZVP”, “use B3LYP/6-311+G(d,p)”
- **Isodensity Surface** — e.g., “ESP on 0.001 a.u. isodensity surface”
- **Resources** — e.g., “use 8 cores and 8 GB memory”
- **Solvent Model** — e.g., “PCM water”
- **Job Name** — e.g., “name the job toluene_opt”

If not specified, sensible defaults are used (e.g., B3LYP/6-31G(d)).


## (Optional) Programmatic API & Paths
Python examples showing **explicit file paths**:

```python
# File: <PROJECT_ROOT>/scripts/run_gaussian_example.py
from pathlib import Path
from gaussian_v1.py import xyz_to_gaussian_opt, gaussian_exec  # adjust import if needed

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
LOG_PATH = PROJECT_ROOT / "log.txt"  # Or Path('/mnt/data/log.txt') in sandbox

xyz_text = (EXAMPLES_DIR / "h2o.xyz").read_text(encoding="utf-8")

# Build Gaussian input and run
gjf_text = xyz_to_gaussian_opt(xyz_text, jobname="h2o_opt")
gaussian_exec(gjf_text, filename=str(PROJECT_ROOT / "h2o_opt.gjf"))

# ... formchk & Multiwfn steps handled by the orchestrator ...
# ... append results to LOG_PATH ...
```

**Where to find results**
- Working directory (default): `<PROJECT_ROOT>/`
- Logs (appended): `<PROJECT_ROOT>/log.txt` (or `/mnt/data/log.txt`)
- Gaussian artifacts: `<PROJECT_ROOT>/{jobname}.(gjf|log|chk|fchk)`


## Paths to External Tools
- **Gaussian 16 (`g16`)**: ensure `g16` and `formchk` are in the system `PATH`.  
  Typical locations: `/usr/local/g16/` (Linux); `C:\g16\` (Windows).
- **Multiwfn**: set the orchestrator to call the Multiwfn binary.  
  Typical locations: `/usr/local/bin/Multiwfn` (Linux); `C:\Multiwfn\Multiwfn.exe` (Windows).

> If these tools are not in `PATH`, configure your orchestrator with **absolute paths**.


## Requirements
- **Gaussian 16 (g16)** installed (including `formchk` utility)
- **Multiwfn** accessible by the orchestrator
- **Python 3.8+** runtime (RDKit optional for conformers)
- Suggested Python packages (see `<PROJECT_ROOT>/requirements.txt`):
  ```bash
  pip install -r requirements.txt
  # typical contents:
  # mcp
  # rdkit
  ```


## Troubleshooting (with Paths)
- **Gaussian failures (Link 9999 / no convergence)**  
  Try a better initial geometry, tighter grid, different functional/basis.
- **`formchk` not found**  
  Ensure the binary is on `PATH` or use an absolute path, e.g., `/usr/local/g16/formchk`.
- **Multiwfn path issues**  
  Point to an absolute binary path, e.g., `/usr/local/bin/Multiwfn`.
- **Empty/partial log**  
  Verify you’re reading/writing the intended file: `<PROJECT_ROOT>/log.txt` or `/mnt/data/log.txt`.


## License & Acknowledgements
- Code under **MIT License** (see `<PROJECT_ROOT>/LICENSE`).  
- Acknowledgements: **Gaussian 16** (Gaussian, Inc.), **Multiwfn** (Tian Lu), and **RDKit**.

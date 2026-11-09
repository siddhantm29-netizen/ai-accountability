# Incident-grounded scenarios for AI accountability and redress by 2030

Group 11 · Team Iron Men · Siddhant Mathapati and Weican Ye

Research implementation for a proposed submission to *Futures*. The workflow connects the AI Incident Database (AIID) to accountability coding, documentation sensitivity and conditional scenarios. Publication readiness remains subject to evidence verification, methodological review and manuscript evaluation.

## Run locally

Use Python 3.12 or newer and run commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/export_review_workbook.py /path/to/Final_Review_and_Scenarios.xlsx
export PROJECT11_DATA_PATH=/absolute/path/to/AIID_Excel_Export-20261019.xlsx
export PROJECT11_REVIEW_DIR="$PWD/data/review"
export PROJECT11_OUTPUT_DIR="$PWD/results"
python src/project11.py
```

For Windows activate `.venv\Scripts\activate` and set equivalent environment variables in PowerShell. To use Jupyter, launch it from the repository root with the same environment and open `notebooks/Project_11_Final_Code.ipynb`. For Kaggle, attach the source workbook and six CSVs, set PROJECT11_DATA_PATH and PROJECT11_REVIEW_DIR before running, and use `/kaggle/working` for output. The delivered notebook is unexecuted; the equivalent script was run for verification.

The export script refuses to overwrite existing review CSVs. Export to a fresh directory with `--output PATH` when updating inputs, then point PROJECT11_REVIEW_DIR there. Extra workbook provenance columns are preserved. Raw data, review inputs, workbook files and results are excluded from git by default; review permissions and AIID terms before publishing derived data separately.

## Research questions and outputs

- RQ1: actor/risk configurations and accountability: exhibits 1A–1D.
- RQ2: response and documented redress evidence by coded actor group: 2A–2D.
- RQ3: classification, unclear-label and report-depth sensitivity: 3A–3D.
- RQ4: conditional scenarios, observable signposts and later-case challenges: 4A–4D.

Each run creates a fresh results folder and ZIP containing CSVs, PDF/300-dpi PNG figures, evidence-linked data, agreement statistics, exhibit status, file hashes and source/software provenance. Missing inputs yield explicit pending statuses. Completed inputs are validated structurally; validation cannot establish the truth of a source claim.

## Statistical interpretation

The primary RQ2 contrast is the sampling-weighted difference in **documented-redress coverage** (multiple minus one organization), retaining unclear cases in the denominator. It measures documentation, not true remedy availability or successful compensation. Unknown actor groups remain visible in tables but are excluded from this two-group contrast. Weights address the designed review sample only.

An optional complete-case contrast excludes unclear outcomes, but returns unavailable if all remaining outcomes have the same label. Approximate stratified bootstrap intervals use 1,000 replicates and are suppressed if either group has fewer than 10 cases, fewer than five documented or five other outcomes, or fewer than 95% valid draws. Sparse-data point estimates remain descriptive. Worst-case bounds and hypothetical unclear-label assignments are reported separately; unclear codes are never overwritten as observed absence.

The data are media-selected, not a representative sample of AI harms. The 2026 snapshot is partial and has substantial classification lag. Report-depth restrictions change the target subset. No causal effects are estimated. Scenario thresholds are illustrative author judgments, not validated cutoffs. The threshold-sensitivity CSV checks alternative values. Sparse supporting evidence for scenario S3 must remain explicit.

## AI assistance and review provenance

Reviewer label sets originated from shared AI-assisted draft passes followed by reported team verification and adjudication. Agreement and Cohen's kappa describe the saved label sets; they do not establish unaided independent human reliability. Final labels in the supplied workbook coincide with reviewer slot 2. Adjudication explanations and source verification should justify that choice rather than presenting it as an independent reference standard.

Scenario narratives, claims, challenges and monitoring thresholds are AI-assisted exploratory interpretations of archive summaries. Actual source checks and any subsequent researcher revisions must be documented. Completing the input schema does not turn these judgments into validated forecasts. See `docs/METHODS_AND_LIMITATIONS.md`.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover documentation-coverage contrasts, no-variation complete-case suppression, sparse intervals, missing actor comparisons, notebook/script synchronization and unexecuted cells. GitHub Actions runs these checks without needing private review inputs or the source workbook. Full-run checks and the tested environment are recorded in `docs/VALIDATION.md`.

## References

- Alon et al. (2025), *The future of artificial intelligence: Insights from recent Delphi studies*. https://doi.org/10.1016/j.futures.2024.103514
- Richards, Benn and Zilka (2025), *From Incidents to Insights: Patterns of Responsibility following AI Harms*. https://doi.org/10.1145/3757887.3763018
- Fehér et al. (2026), *Next-generation strategic foresight for responsible AI governance and technology policy: Introducing the Archer Model*. https://doi.org/10.1016/j.futures.2026.103879
- AIID public snapshot: https://incidentdatabase.ai/research/snapshots/

## Repository

https://github.com/siddhantm29-netizen/ai-accountability

Clone with:

```bash
git clone https://github.com/siddhantm29-netizen/ai-accountability.git
cd ai-accountability
```

No project-wide redistribution license has been assigned. Authors should select one deliberately; it must not override third-party data terms.

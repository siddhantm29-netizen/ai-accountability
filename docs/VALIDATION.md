# Validation

The equivalent Python script completed a full run using the pinned AIID workbook and all six review CSVs exported from Final_Review_and_Scenarios.xlsx. All 16 exhibit statuses are GENERATED. All 48 exported-file hashes match the archived manifest. This validates execution and structure, not source truth.

Six automated tests pass, covering the documentation contrast, unsupported complete cases, missing actor comparisons, sparse intervals, bootstrap behavior and notebook/script synchronization. The delivered notebook remains unexecuted. For the submitted labels, the documentation contrast is approximately -0.0202 (multiple minus one organization), the complete-case contrast is unavailable, and sparse intervals are suppressed. This finding measures archive documentation, not remedy access.

Tested versions: {"pandas": "2.2.3", "numpy": "2.3.5", "matplotlib": "3.10.8", "scikit-learn": "1.8.0", "openpyxl": "3.1.5"}

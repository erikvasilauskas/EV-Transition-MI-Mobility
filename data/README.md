# Data Directory

This folder stores datasets and intermediate outputs for the EV-Transition staffing analysis project.

- `raw/`: Unmodified source files pulled from public data providers or partners.
- `external/`: Reference datasets used for joins (e.g., NAICS crosswalks, occupational taxonomies).
- `interim/`: Cleaned or lightly transformed tables ready for feature engineering.
- `processed/`: Analysis-ready tables that can be shared with downstream collaborators.
- `lookups/`: Controlled vocabularies and mapping tables, such as NAICS-to-segment assignments.

Keep personally identifying information (PII) or restricted-use data out of this repository. Use `.gitignore` rules if you need to stage sensitive files locally.

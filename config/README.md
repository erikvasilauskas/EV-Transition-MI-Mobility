# Configuration

Centralize configuration files, such as file paths, segment definitions, and analysis parameters.

Example files:

- `project.yml`: Global settings (data directories, default year/quarter).
- `segments.yml`: Authoritative mapping between industries and supply-chain segments.

Keep sensitive credentials out of version control. Use environment variables or local-only `.env` files that are gitignored.

# Agent Instructions

## Local environment file

- Do **not** delete, remove, overwrite, or commit/push the `.env` file in the project root.
- `.env` is ignored by Git and contains local Docker Compose / runtime configuration for this workspace.
- If environment variables need to change, update `.env.example` or document the changes; do not modify `.env` unless explicitly asked.

## Testing

- Use the dedicated unit-tier virtualenv. **Never** create, modify, install into, or delete `.venv/` — it belongs to the host.
- Unit tier (no Docker / no LaTeX / no DB): `make test-unit`, or a single file: `.venv-cline/bin/python -m pytest tests/<file> -q`.
- Integration tier needs Docker on the host and skips automatically when `LATEX_ON_HTTP_API_URL` is unset.
- Full instructions, environment map, test tiers, and container limitations: read `.agents/skills/testing/SKILL.md` before running or debugging tests.

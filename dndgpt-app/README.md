# DnDGPT application

See the [project README](../README.md) for architecture and setup.

From this directory, install `requirements.txt` and run `python -m pytest -q`. Start the API with `python -m uvicorn app.server:app --host 127.0.0.1 --port 8765`.

`/api/health` is public; saved campaign tools require OAuth. Set environment variables explicitly; `.env.example` documents them but is not automatically loaded by the app. Keep the database outside ephemeral deployment storage.

ChatGPT-led play is the primary mode. Supported typed engine mechanics remain incremental; see `RULES_COVERAGE.md`. The complete rules and hardener are in `rules/` and remain separate from claims about executable coverage.

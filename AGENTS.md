# Agent instructions

## Project

This Home Assistant integration gives per-person clothing advice from hourly weather forecasts, including sandals, jackets, and rain protection.

## Working in this repository

- Read `README.md` before changing profile settings, forecast lookahead, or recommendation thresholds.
- Keep the recommendations for different household profiles independent and update user-facing integration text when changing their options.
- Before changing CI, check [pschmitt/ci-workflows](https://github.com/pschmitt/ci-workflows) for reusable components and preserve this repository's existing checks.

## Validation

- Run `uvx ruff check .` and `uvx ruff format --check .` for Python changes.
- CI runs Hassfest and the shared Ruff checks; it currently has no test job.

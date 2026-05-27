# BeeSense

A Python project scaffold for BeeSense.

## Project layout

- `src/beesense/` - package source code
- `tests/` - automated tests
- `pyproject.toml` - build and project metadata
- `.gitignore` - ignored files for Git

## Quick start

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
2. Activate it:
   - Windows: `.
   .venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
3. Install dependencies:
   ```bash
   python -m pip install -U pip
   python -m pip install -r requirements-dev.txt
   ```
4. Run tests:
   ```bash
   python -m pytest
   ```

## Package usage

```bash
python -m beesense
```

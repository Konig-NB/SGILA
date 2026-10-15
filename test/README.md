# Running the SGILA Playwright functional suite

The browser test code is in `test/test_ui.py`. Pytest starts Django's live test server and Playwright opens Chromium; you do not need to click through the scenarios manually.

## In this workspace

Open PowerShell in the repository root (`C:\Users\sithe\Music\SGILA`) and run:

```powershell
.venv\Scripts\python.exe -m pytest test/test_ui.py -q --junitxml=test/playwright-report.xml -p no:cacheprovider
```

The suite exits only after all tests have run. A failure means an expected UI behavior or assertion did not match; it does not automatically mean the app should be changed. Check the traceback and the coverage report. The enterprise pricing hand-off currently fails as described in `FUNCTIONAL_TEST_REPORT.md`.

## If setting up a separate environment

1. Create/activate a Python environment and install the application's dependencies from `requirements.txt`.
2. Install the test-only packages `pytest`, `pytest-django`, and `pytest-playwright` if they are not already available.
3. Install the Playwright Chromium browser with `python -m playwright install chromium`.
4. Run the command above from the repository root. The Django test server/database must be able to run with the project's configured test settings.

The suite uses Django's test database and isolated test accounts. AI generation is stubbed at the job/provider boundary, and card details are test values handled by the app's local test flow; no real AI request or external card charge is made.

## Reading the outputs

- `test/FUNCTIONAL_COVERAGE_MATRIX.md` maps roles/features to current test coverage and lists gaps.
- `test/FUNCTIONAL_TEST_REPORT.md` records the most recent full-run summary, failures and caveats.
- `test/playwright-report.xml` is JUnit XML for CI tools. Pytest's terminal output is the quickest human-readable summary.

# SGILA Playwright functional test report

**Run:** 4 October 2026 (Africa/Johannesburg)  
**Result:** 11 passed, 1 failed, 0 skipped  
**Browser:** Chromium, Playwright 1.63.0  
**Duration:** 82.84 seconds  
**Command:** `.venv\Scripts\python.exe -m pytest test/test_ui.py -q --junitxml=test/playwright-report.xml -p no:cacheprovider`

## What ran

The 12 Playwright cases cover parent and teacher registration/OTP/trials, parent and learner sign-in, learner creation and teacher class-code linking, story reading and comprehension/progress, AI-story UI with a deterministic job fixture, parent/teacher reports, Grade 1–4 page families, Grade 3 score saving, all eight Grade 4 activity types, visual matching, pronunciation UI with a stubbed browser voice, all three spelling formats, pause/resume, messaging, help search/support/feedback, password recovery, card payment, extra-seat debit-order flow, package-code redemption, subscription cancellation, and parent/teacher/learner account activation controls.

The detailed feature-to-test mapping and remaining gaps are in [FUNCTIONAL_COVERAGE_MATRIX.md](FUNCTIONAL_COVERAGE_MATRIX.md). The Playwright source is [test_ui.py](test_ui.py), and setup/run instructions are in [README.md](README.md).

## Failure found

`test_parent_password_recovery_and_new_password_login` fails when the enterprise pricing dialog hands off a selected school to package activation. After selecting “Playwright Primary School” (quintile 3, 120 learners), the activation link is `/subscription/redeem-package?school_type=quintile_1&learners=100`: it omits the selected school ID and carries different pricing inputs. This is recorded as an app failure; no app behavior was changed.

Package-code redemption and cancellation are tested independently and passed, so they still execute despite that hand-off failure.

## Scope and caveats

This is broad end-to-end feature coverage, not proof of every possible invalid input, permission boundary, API status, concurrency case, or screen-reader/browser combination. Grade 3’s score-saving endpoint is covered, but all six Grade 3 activity types are not individually completed through the UI. AI, payment, and speech dependencies are deterministic local stubs/test flows, not live third-party integrations. See the matrix for all identified gaps.

**Warning:** One dependency deprecation warning was emitted during the run.

Machine-readable JUnit results: [playwright-report.xml](playwright-report.xml).

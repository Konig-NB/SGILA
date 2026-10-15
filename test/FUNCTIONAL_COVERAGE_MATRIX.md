# Playwright functional coverage matrix

This matrix is based on the app's Django URL configurations and user-facing flows. “Covered” means the current Playwright suite exercises that flow; page-load checks and mocked integrations are called out separately so they are not mistaken for full behavioral coverage.

| Role / surface | Feature or route group | Playwright coverage | Status / limitation |
| --- | --- | --- | --- |
| Public | Home, terms, help, UI flow diagram, account-access page | Entry-page assertions; article search, support ticket and feedback; UI flow PDF download | Covered |
| Parent | Sign-up, required fields, OTP verification, free Family trial, welcome and dashboard | Complete sign-up journey, verifies account/subscription and opens dashboard | Happy path covered; invalid signup/OTP/resend cases not covered |
| Parent | Sign-in and password recovery | Wrong/correct password; request reset, set new password, sign in with new password | Main paths covered; malformed/expired token branches not covered |
| Parent | Add learner and link teacher class code | Create learner with grade/password; teacher journey creates linked learner | Main path covered; duplicate/invalid code and capacity boundaries not covered |
| Parent | Child progress, story report, yearly grade confirmation, pause/reactivate learner | Reads report, confirms grade promotion, toggles learner activation | Main paths covered; grade-stays-same and blocked/reactivation edge cases not covered |
| Learner | Login and Grade 1–4 homes | Learner login and each grade home | Covered |
| Learner | Story, questions, visual, pronunciation, spelling, results, dashboard | Grade-matched page render; Grade 1 comprehension and completion; visual correct match; pronunciation English/isiZulu speech UI with browser speech mocked; all three spelling types answered and submitted | Main happy paths exercised; wrong-answer and media/network error cases remain |
| Learner | Grade 3 activity set | Submits an activity question and exercises the final score-saving endpoint through the browser session | Partial: final score save is exercised, but every one of the six interactive activity types is not completed through its UI |
| Learner | Grade 4 vocabulary, sequencing, inference, prediction, feelings, cause/effect, theme, written response | Each page is opened; vocabulary, sequencing, inference, prediction, feelings, cause/effect, theme, written response, and results are interacted with in the Grade 4 journey | Main happy paths covered |
| Learner | Pause/resume activity | Pause modal, saved resume point, and “Continue where I paused” are exercised on the Grade 4 vocabulary activity | Covered |
| Learner | AI story generation | Browser request, status polling, ready state, generated story navigation | Provider/background job is stubbed to deterministic completion; real-provider behavior is not covered |
| Teacher | Registration, OTP, class code, free trial, dashboard and plan page | Signup and subscription state assertions | Main path covered; invalid school search is not fixed or disguised; custom school entry is tested |
| Teacher | Linked learners, reports and parent/teacher messages | Creates linked learner, exchanges messages in both roles, opens report | Main path covered |
| Teacher | Deactivate/reactivate account | OTP email is captured in test and entered through UI | Main path covered; invalid/expired reactivation codes not covered |
| Parent / teacher | Individual/family subscription card payment | Parent selects Family, submits test card, confirms active subscription | Main path covered; external payment processor is not contacted |
| Parent | Add seats with bank debit order | Adds two seats and verifies stored payment details | Main path covered; other payment and invalid-data branches not covered |
| Parent / teacher | Enterprise school lookup, quote, activation hand-off | Searches/selects directory school and checks activation URL | **Fail:** selected school id/type/enrolment do not propagate into activation URL |
| Parent / teacher | Enterprise package redemption | Separate manual-school/code journey verifies plan and redemption count | Covered independently of the failing pricing hand-off |
| Parent / teacher | Subscription cancellation | Confirmation submitted and status checked | Covered for package redemption journey; other plan states not covered |
| Public/API | API login, OTP, AI, lesson and activity APIs | Exercised where invoked by current browser journeys | Endpoint-by-endpoint request/response and all error statuses are not independently covered |
| Public/API | School, help center, messaging APIs | School search, help search/ticket/feedback and messages run through UI | Main paths exercised; permission/error/pagination branches not covered |
| Staff | Django admin and content management | No Playwright staff login journey | Not covered |
| Cross-cutting | Authorization, validation, accessibility, browser/device matrix, concurrency | A few role-gated journeys and semantic locators | Not exhaustive; multiple roles use Chromium only |

## Meaning of “exhaustive”

This matrix covers the discovered front-end feature areas and route families, but the current suite is not exhaustive at the branch/API/error-case level. To claim exhaustive coverage for a release, every “Not covered” and “Partial” row needs an explicit Playwright assertion or a documented reason it is out of scope, then the whole suite must be rerun. Some integrations also need a separate staging run with safe test credentials; the local functional run deliberately avoids real charges and AI-provider calls.



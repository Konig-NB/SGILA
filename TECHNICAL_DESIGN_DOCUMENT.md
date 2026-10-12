# SGILA Technical Design Document

## 1. Project Overview

SGILA is a Django-based reading and learning application for foundation-phase learners. The project supports reading comprehension, curriculum-aligned lesson activities, learner tracking, parent/teacher oversight, and subscription management. The application is structured as a web system with a public-facing front-end, a role-aware access model, and an API layer serving lesson and activity content.

The current codebase shows that the application is designed around a South African schooling context and supports learner flows across Grades 1 to 4. The app includes story-based lessons, comprehension tasks, spelling, visual matching, sequencing, and Grade 4 content such as vocabulary, inference, prediction, and written-response activities. It also includes school lookup, class code linking, account verification, and pricing management for individual, family, and school packages.

## 2. Project Background and Context

The project is built around the SGILA educational model: a reading support system for children in the foundation phase. The application aims to provide structured reading lessons, progress tracking, and adaptive practice in a safe, monitored digital environment.

From the application structure and project documentation:

- The app is a Django web platform with multiple user roles: learner, parent, and teacher.
- The core educational content is stored as story lessons with activities and progress records.
- Learner access is tied to grade, registration, and account status controls.
- Parents and teachers can manage learners, link classes, and review learner dashboards.
- School-based packages, subscription plans, and enterprise pricing are supported.
- AI-assisted story generation is also integrated into the platform, showing a learning system that can expand content beyond static curriculum definitions.

This means SGILA is not just a simple reading app; it is a digital education platform with content management, account lifecycle handling, payments, access rules, and reporting.

## 3. Project Objectives

The main objectives of SGILA are as follows:

1. Provide a structured reading-learning experience for foundation-phase learners.
2. Support curriculum-aligned stories and activities for multiple grades.
3. Ensure learner progress can be stored and reviewed by parents and teachers.
4. Support secure user registration, OTP verification, login, password reset, and account reactivation.
5. Allow parents and teachers to manage learner access and classroom relationships through class codes.
6. Support school lookups and school-based enterprise pricing.
7. Offer a clear subscription and plan-management experience for individual, family, and school accounts.
8. Ensure maintainability through a modular Django architecture and reusable app structure.

## 4. Requirements Specification

### 4.1 Functional Requirements

The application implements the following functional requirements, derived from the project structure and routing:

#### User Management
- Users can register as learner, parent, or teacher.
- New accounts use OTP-based email verification before full activation.
- Users can resend OTP codes and reset forgotten passwords.
- Inactive or deactivated users can reactivate their account.

#### Learner Management
- Parents can add learners to their account.
- Teachers can link learners through class codes.
- Learners can confirm grade information for the school year.
- Learner access can be paused or reactivated based on account or plan status.

#### Lesson and Activity Content
- The app contains grade-based lessons and reading activities.
- Each lesson includes story content, reading questions, and activity groupings.
- Grade 1, 2, 3, and 4 activity types include comprehension, spelling, visual matching, sequencing, prediction, inference, feelings, cause-effect, theme, and written-response work.
- Grade 2 activities are explicitly managed through blueprint-based loading and synchronization.

#### Progress and Reporting
- Reading progress is recorded for each learner.
- Parent and teacher dashboards summarize learner status and activity completion.
- Reports can be generated for individual stories and learner activity history.

#### School and Subscription Management
- Parents and teachers can search for schools.
- Class codes are issued and used to associate learners to classrooms.
- Individual, family, and school subscription flows exist.
- Enterprise pricing is calculated from school type, learner count, and pricing mode.
- Package-code redemption and seat management are supported.

#### AI and Content Support
- The project includes optional AI-assisted story generation.
- AI story jobs are tracked through job status endpoints.
- AI-generated content is validated and saved into the lesson structure.

### 4.2 Non-Functional Requirements

The project demonstrates several non-functional requirements:

- Security: secure session management, password hashing, OTP handling, and access gating.
- Maintainability: clear separation of concerns into `api`, `lessons`, and `schools` apps.
- Scalability: modular design for adding content, pricing logic, and user roles.
- Usability: role-aware web pages and dashboard flows for parents, learners, and teachers.
- Reliability: validation, session checks, and model logic for grade confirmation, account state, and access restrictions.
- Internationalisation: the app is designed in English and uses South African settings, including timezone and pricing context.

## 5. System Architecture

The SGILA system follows a Django Model-View-Template (MVT) architecture, with a REST-style API layer and role-based front-end routes.

### 5.1 Architectural Layers

#### Presentation Layer
The presentation layer is implemented through Django templates under `templates/` and route handlers in `lessons/views.py`.

It handles:
- welcome pages and registration/login screens
- parent dashboards and teacher dashboards
- learner lesson pages
- story, activity, and results pages
- subscription and package redemption screens

#### Application Layer
The application logic is distributed between:

- `lessons/views.py` — web UI and route-specific logic
- `api/views.py` — API endpoints and JSON responses
- `api/models.py` — domain models and business rules
- `lessons/pricing.py` — central pricing logic
- `schools/context.py` and `schools/models.py` — school lookup and school metadata

#### Data Layer
The data layer uses Django ORM with SQLite as the default database and PostgreSQL support configured through environment variables.

Important data domains include:
- Account records: Parent, Teacher, Child
- Learning records: Lesson, StoryPage, Progress, GradeHistory
- Activities: ComprehensionQuestion, VisualActivityItem, SpellingActivity, SequencingActivity, VocabularyQuestion, etc.
- School data: School records from DBE school data
- Subscription and enterprise structures: Subscription, PackageCode

### 5.2 Core Architectural Components

#### Django Project Configuration
The project configuration is centralized in `sgila_project/settings.py` and defines:

- installed apps
- database configuration
- template settings
- static/media handling
- email backend configuration
- security settings
- pricing configuration for Enterprise and family plans

#### URL Routing
The root URL configuration (`sgila_project/urls.py`) directs requests to the app-specific URL sets:

- `api/` for application programming interfaces
- `schools/` for school search and school-related pages
- `lessons/` for user interface routes and educational screens

This structure separates the REST API from the user-facing web pages, which is a strong architectural practice.

#### Middleware and Access Control
The project includes `lessons/middleware.py` and account access logic to enforce account access restrictions. The application checks session role, id, and account status before allowing certain pages or actions. This is particularly important because learner, parent, and teacher flows each have different access boundaries.

#### School Data Domain
The `schools` app is designed specifically for schools database integration. It stores school metadata and supports search and classification by province, quintile, district, and status. This modeling allows the app to support school-linked packages and enterprise pricing logic.

## 6. Detailed Design by Module

### 6.1 `api` App
The `api` app is the domain and service backbone of the system. It contains:

- Core models for Parent, Teacher, Child, Lesson, Progress, and GradeHistory
- Activity question models and story content definitions
- OTP and password reset token handling
- Subscription and package-code logic
- Messaging endpoints between parent and teacher
- AI story generation and status tracking

This is the main business logic module of the application.

### 6.2 `lessons` App
The `lessons` app forms the front-end layer of the application. It contains:

- page routes and views
- dashboard logic
- lesson pages and result views
- account management screens
- subscription flows
- teacher and parent operations

This app is responsible for converting business logic and models into specific user experiences.

### 6.3 `schools` App
The `schools` app manages school-related data and contexts. It supports:

- school search
- province-based filtering
- school identification and metadata storage
- enterprise pricing context based on school classification

### 6.4 `lessons/pricing.py`
This module is a key design feature because it centralizes the rules for all product pricing:

- individual plan price
- family plan price
- school enterprise pricing by quintile
- minimum learner count
- pricing mode selection
- annual prepay calculations

The code explicitly separates pricing logic from templates and JavaScript, which reduces inconsistency and improves maintainability.

## 7. Data Design

### 7.1 User Model Design
The application stores separate user entities rather than a single unified user table:

- `Parent` — manages one or more learners
- `Teacher` — monitors classroom progress and teaches a class
- `Child` — represents each learner profile

This design is appropriate because the app handles different lifecycles, permissions, and access behaviors for each role.

### 7.2 Educational Content Design
The content model supports a lesson-based structure where each lesson contains:

- story text
- activity content
- progress results

The actual structure includes components such as:
- `StoryPage`
- `ComprehensionQuestion`
- `VisualActivityItem`
- `PronunciationWord`
- `SpellingActivity`
- `SequencingActivity`
- `VocabularyQuestion`
- `WrittenResponsePrompt`

This approach enables a modular content pipeline where each learning activity can be managed independently.

### 7.3 Progress Tracking Design
The app records both content access and mastery through `Progress` and related history tables. This allows the app to:

- know what a learner has completed
- generate dashboards
- identify suitable next learning steps
- maintain evidence of learner growth over time

## 8. Architectural Strengths

The current application demonstrates several well-structured design decisions:

1. Separation of concerns between UI, business logic, and data models.
2. Clear app decomposition by domain (`api`, `lessons`, `schools`).
3. Centralized configuration in the Django project settings.
4. Consistent naming conventions and role-based routing.
5. Pricing logic centralized away from templates and JavaScript.
6. Business rules embedded in model methods and view logic rather than spread arbitrarily across the codebase.

## 9. Design Challenges and Considerations

The app also contains complexity that must be managed carefully:

- many role-based access rules and deactivation flows
- multiple grade logic paths and grade-confirmation decisions
- class code and parent/teacher linking logic
- AI content generation and validation pipelines
- subscription boundary rules and plan caps

These concerns suggest that the system is not a small static site; it is a domain-rich digital education platform with real operational logic.

## 10. Conclusion

SGILA is a Django-based educational platform designed to support learners, parents, and teachers in reading development and curriculum engagement. Its architecture is well-structured around modular apps, role-based access, lesson-driven content, and centralized pricing rules. The project's goals align with a strong educational digital system: improve reading engagement, support learner monitoring, and manage access and subscription flows in a way that is secure and maintainable.

This design is appropriate for a real-world educational application because it supports both content delivery and operational governance.

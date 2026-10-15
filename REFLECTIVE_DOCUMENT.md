# Reflective Document: Project Background, Objectives, Requirements, and Architecture

## 1. Project Background and Objectives

The SGILA project is a digital reading and learning application developed for foundation-phase learners. It is designed to support children in Grades 1 to 4 by providing reading stories, comprehension exercises, activity-based learning, and progress tracking. The application targets three main user groups: learners, parents, and teachers.

The system’s background is rooted in the educational need to provide structured literacy support in a digital environment. The project includes story-based learning, grade-specific activities, and progress dashboards so that learners can read stories, complete reading tasks, and receive feedback in a guided format. Teachers and parents can monitor learner activity and manage access, while learners can work through reading tasks in a secure and role-aware environment.

The key objectives of the project are:

1. To create a web application that supports reading development for foundation-phase learners.
2. To provide a modular structure of lessons, stories, and comprehension activities that is aligned to grade levels.
3. To allow parents and teachers to monitor learner progress and manage classroom or family-linked learning access.
4. To maintain secure and role-aware user sessions for learners, parents, and teachers.
5. To support subscription, school, and package flows through a practical pricing and school-association model.
6. To use a Django-based architecture that is maintainable, extendable, and aligned with real-world educational software requirements.

In summary, the SGILA project is an educational platform designed to make reading practice more engaging, structured, and supportive for learners while providing strong oversight tools for adults managing the child’s education.

## 2. Requirements and Analysis of the System

The application’s requirements can be understood from the actual project implementation and documentation. The project is not a simple front-end website; it is a full web application with multiple user roles and educational workflows.

### 2.1 Functional Requirements

The functional requirements implemented by the app include:

- User registration and account creation for parents, learners, and teachers.
- OTP-based verification and secure login.
- Password reset and account reactivation.
- Grade-based lesson delivery.
- Story reading and comprehension activities.
- Automated activity scoring and progress updates.
- Parent and teacher dashboards.
- Learner class linking through class codes and school data.
- School lookup and enterprise package calculations.
- Subscription flows and package redemptions.
- AI-assisted story generation support.

### 2.2 Non-Functional Requirements

The system also reflects non-functional requirements such as:

- security through hashed passwords and session-based access control
- maintainability through modular app separation
- reliability through validation and role-based business logic
- usability through clear dashboards and user-facing forms
- configurability through environment-driven settings and pricing tables

## 3. Architecture and Requirements Part of the Analysis and Design

The architecture of SGILA follows the standard Django Model-View-Template pattern, with an additional API layer that supports JSON-based endpoints for programmatic access. This is important because the application combines a traditional web interface with educational data services.

### 3.1 Architectural Components

The project is split into three main functional apps:

- `api` — the core data and service layer for accounts, learner models, lessons, activities, subscriptions, and reporting.
- `lessons` — the front-end application layer containing templates, views, dashboards, and user-facing flows.
- `schools` — the component that handles school metadata and school-search logic.

The project-level settings file defines global configurations such as the database, middleware, templates, static assets, email backend, and pricing configuration. The root URL configuration then routes requests into the correct application areas.

### 3.2 Requirements Aligned to the Architecture

The design reflects the project’s requirements in the following way:

- The `api` app holds the core domain model and business data.
- The `lessons` app translates that data into interactive educational screens.
- The `schools` app connects the system to school metadata needed for enterprise pricing and organization-based access.
- The URL layer cleanly separates public pages from API endpoints.
- The middleware and access rules ensure that pages and features are accessible only to the correct user roles.

This architecture supports the educational and operational goals of the platform while keeping the codebase organized and extensible.

## 4. System Design Reflection

From a reflective and design perspective, the application demonstrates good separation of concerns and sensible domain breakdown. The use of distinct models for `Parent`, `Teacher`, and `Child` shows an understanding that these are different user types with different responsibilities. Likewise, the presence of pricing logic in a dedicated module shows that the project recognizes the importance of separating business rules from the front end.

The design also shows awareness of user experience and operational needs. OTP verification, account reactivation, and class code linking are all examples of workflow design needed in real educational systems. The lesson activity structure indicates that the project is built around reusable content, tracking, and scoring rather than isolated static pages.

## 5. Conclusion

The SGILA project is a well-structured educational web application that combines reading content, user-account management, reporting, and subscription functionality in one Django-based system. Its background is grounded in real educational support needs, while its architecture and requirements reflect a carefully considered design for learners, parents, teachers, and school-based administration.

The system’s practical strength lies in its modular design and the alignment between requirements and implementation: the app’s content models, role-based access control, navigation structure, and pricing logic all work together to create a coherent digital learning platform.

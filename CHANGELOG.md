# Changelog
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), with links to [Semantic Versioning](https://semver.org).

---

## [1.3.0] - 2025-02-12
### Added
- Switched from stadium-based to team-based city mapping for match determination.
- Introduced API response caching with 7-day retention.
- Automatic deletion of old cache files after notifications are sent.
- Moved all test files to the `/test` directory and added comprehensive test suites.
- Updated timezone display to use "CET" for clarity.

### Changed
- Refactored `fetcher.py` for improved reliability and performance in match fetching and caching.

---

## [1.2.0] - 2025-02-12
### Added
- Introduced admin interface improvements:
  - Separated the admin template into the `templates/admin.html` file.
  - Added database context (`db`) for dynamic access control operations.
- Built-in Docker deployment improvements.

### Fixed
- Resolved issues with missing module imports (e.g., `sessionmaker` from SQLAlchemy).
- Fixed deployment errors with dependencies such as `Flask-HTTPAuth`.

---

## [1.1.0] - 2025-02-11
### Added
- Initial integration of Docker-based deployments.
- Automated release publishing via GitHub Actions.
- Basic admin interface with Flask for managing user access.

### Changed
- Dependency versions updated in `requirements.txt`.

---

## [1.0.0] - 2025-02-11
### Added
- Initial release of the bot project.
- Basic user management and access control.
- Dockerfile for containerized deployments.
- Initial implementation of the Telegram bot and scheduler.

---

For more details, please refer to the commit history.

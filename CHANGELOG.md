# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
from version 1.20.0 onwards.

## [Unreleased]

- n/a

## [2.0.1] - 2019-04-06

### Fixed
- Fixed deprecation warnings on Python 3.7

## [2.0.0] - 2019-03-17

### Removed
- **API break**: cleaned up all module namespaces, with various duplicate or
  external names removed. Clients using only documented API are unaffected.

## [1.20.2] - 2019-02-23

### Changed
- Minor packaging improvements; add project_urls for PyPI

## [1.20.1] - 2019-02-15

### Changed
- Minor packaging improvements

## [1.20.0] - 2019-01-19
### Changed
- `cancel()` now terminates retries from RetryExecutor
  ([#51](https://github.com/rohanpm/more-executors/issues/51))


## [1.19.0] - 2019-01-16
### Fixed
- Fixed TimeoutExecutor thread leak when `shutdown()` is never called

### Added
- Introduced `more_executors.futures` module for composing futures


## [1.18.0] - 2019-01-15

### Fixed
- Fixed deadlock when awaiting a future whose executor was garbage collected
  ([#114](https://github.com/rohanpm/more-executors/issues/114))

### Changed
- Reduced log verbosity
  ([#115](https://github.com/rohanpm/more-executors/issues/115))


## [1.17.1] - 2019-01-09

### Fixed
- Exception tracebacks are now propagated correctly on python2
  via `exception_info`


## [1.16.0] - 2019-01-06

### Added
- Minor usability improvements to retry API
- Introduced flat_bind
  ([#97](https://github.com/rohanpm/more-executors/issues/97))

### Removed
- **API break**: removed `new_default` methods in retry module


## [1.15.0] - 2019-01-03

### Fixed
- Fixed possible deadlock in CancelOnShutdownExecutor
  ([#98](https://github.com/rohanpm/more-executors/issues/98))
- Fixed `Executors.bind` with `functools.partial`
  ([#96](https://github.com/rohanpm/more-executors/issues/96))
- Fixed ThrottleExecutor thread leak when `shutdown()` is never called
  ([#93](https://github.com/rohanpm/more-executors/issues/93))


## [1.14.0] - 2018-12-26

### Fixed
- Fixed thread leaks when `shutdown()` is never called
  ([#87](https://github.com/rohanpm/more-executors/issues/87))
- Refactors to avoid pylint errors from client code
  ([#86](https://github.com/rohanpm/more-executors/issues/86))

### Removed
- **API break**: removed `Executors.wrap` class method


## [1.13.0] - 2018-12-15

### Added
- Introduced Executors.bind


## [1.12.0] - 2018-12-09

### Added
- Introduced FlatMapExecutor


## [1.11.0] - 2018-04-28

### Fixed
- Fixed hangs on executor shutdown


## [1.10.0] - 2018-04-28

### Fixed
- Fixed a race condition leading to RetryExecutor hangs

### Added
- Improved RetryPolicy API
- Added `logger` argument to each executor


## [1.9.0] - 2018-04-15

### Added
- Introduced ThrottleExecutor


## [1.8.0] - 2018-04-07

### Fixed
- Fixed missing long_description in package


## [1.7.0] - 2018-04-07

### Added
- Introduced AsyncioExecutor

### Changed
- Revised TimeoutExecutor concept to "cancel after timeout"


## [1.6.0] - 2018-03-22

### Fixed
- Avoid some uninterruptible sleeps on Python 2.x

### Added
- Introduce TimeoutExecutor

### Changed
- Use monotonic clock in RetryExecutor
- Minor improvements to logging


[Unreleased]: https://github.com/rohanpm/more-executors/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/rohanpm/more-executors/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/rohanpm/more-executors/compare/v1.20.2...v2.0.0
[1.20.2]: https://github.com/rohanpm/more-executors/compare/v1.20.1...v1.20.2
[1.20.1]: https://github.com/rohanpm/more-executors/compare/v1.20.0...v1.20.1
[1.20.0]: https://github.com/rohanpm/more-executors/compare/v1.19.0...v1.20.0
[1.19.0]: https://github.com/rohanpm/more-executors/compare/v1.18.0...v1.19.0
[1.18.0]: https://github.com/rohanpm/more-executors/compare/v1.17.1...v1.18.0
[1.17.1]: https://github.com/rohanpm/more-executors/compare/v1.16.0...v1.17.1
[1.16.0]: https://github.com/rohanpm/more-executors/compare/v1.15.0...v1.16.0
[1.15.0]: https://github.com/rohanpm/more-executors/compare/v1.14.0...v1.15.0
[1.14.0]: https://github.com/rohanpm/more-executors/compare/v1.13.0...v1.14.0
[1.13.0]: https://github.com/rohanpm/more-executors/compare/v1.12.0...v1.13.0
[1.12.0]: https://github.com/rohanpm/more-executors/compare/v1.11.0...v1.12.0
[1.11.0]: https://github.com/rohanpm/more-executors/compare/v1.10.0...v1.11.0
[1.10.0]: https://github.com/rohanpm/more-executors/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/rohanpm/more-executors/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/rohanpm/more-executors/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/rohanpm/more-executors/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/rohanpm/more-executors/compare/v1.5.0...v1.6.0

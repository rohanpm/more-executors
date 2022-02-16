# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
from version 1.20.0 onwards.

## [Unreleased]

- n/a

## [2.8.2] - 2022-02-16

### Fixed

- Fix a bug where `f_proxy` may trigger a `RecursionError`, if used with a
  future raising an `AttributeError`.

## [2.8.1] - 2021-07-21

### Fixed

- Fix a bug specific to Python 2 where mixing `f_proxy` with other future
  composition functions such as `f_map` could result in the proxy future being
  eagerly evaluated.

## [2.8.0] - 2021-07-14

### Added
- Type stubs are now included. These have been tested with mypy and pylance.
  Type information is not complete, but is sufficient for most typical
  scenarios for composing executors and futures. Requires Python 3.9 or later.

## Changed
- Internal refactoring to improve usability of prometheus metrics.
- Improved consistency of shutdown behavior. Previously, the behavior on
  incorrect usage of executors such as submit-after-shutdown or multiple calls
  to shutdown was not strictly defined and could differ between executors.
  Every executor will now raise an exception on submit-after-shutdown and
  will tolerate multiple calls to shutdown.

## [2.7.0] - 2021-07-11

### Added
- Introduced support for prometheus instrumentation.
- All executors now accept a `name` argument. If given, the name is used
  in prometheus metrics and in the name of any threads created by an executor.

## [2.6.0] - 2021-06-19

### Added
- Support the `cancel_futures` argument introduced onto `Executor.shutdown`
  in Python 3.9.

### Changed
- `DEBUG` log events are now only generated if the `MORE_EXECUTORS_DEBUG`
  environment variable is set to `1`. This change was made due to the extreme
  verbosity of debug logs if executors are used heavily.

## [2.5.1] - 2020-06-01

### Fixed
- Fixed a potential hang on exit when executors are not explicitly shut down
 ([#176](https://github.com/rohanpm/more-executors/issues/176))

## [2.5.0] - 2019-09-23

### Added
- `ThrottleExecutor` now accepts a callable for `count`, for dynamic throttling.

### Changed
- Internal refactoring to simplify backtraces in certain cases
  ([#169](https://github.com/rohanpm/more-executors/issues/169)).

## [2.4.0] - 2019-09-15

### Fixed
- `RetryExecutor` now logs an error and terminates retries of a future if the
  configured `RetryPolicy` raises an exception. Previously, futures would hang
  indefinitely in the case of a broken policy.

## [2.3.1] - 2019-09-11

### Fixed
- Fixed some scaling/performance issues with functions dealing with collections
  of futures (`f_or`, `f_and`, `f_sequence`, `f_zip`). These functions now support
  up to 100,000 input futures. In earlier versions of the library, these would
  break with approximately ~1,000 inputs.

## [2.3.0] - 2019-09-07

### Added
- Introduced proxy futures via `f_proxy`

### Fixed
- `more_executors.futures.*` can now be referenced after an `import more_executors`;
  there is no need to explicitly `import more_executors.futures`.

## [2.2.0] - 2019-08-31

### Added
- map/flat_map now accept an `error_fn` to transform the result of an
  unsuccessful future ([#153](https://github.com/rohanpm/more-executors/issues/153)).
- Introduced `PollExecutor.notify` to wake up a `PollExecutor` early
  ([#152](https://github.com/rohanpm/more-executors/issues/152)).

## [2.1.2] - 2019-06-26

### Fixed
- Fixed a race condition with RetryExecutor which could occasionally result in a future
  being retried after a request to cancel
  ([#150](https://github.com/rohanpm/more-executors/issues/150))

## [2.1.1] - 2019-06-16

### Fixed
- Avoid spurious "cannot schedule new futures after interpreter shutdown" tracebacks
  ([#144](https://github.com/rohanpm/more-executors/issues/144))

### Changed
- Most functions in `more_executors.futures` will now immediately raise a
 `TypeError` if invoked with a non-future value where a future is expected.
 ([#146](https://github.com/rohanpm/more-executors/issues/146))

## [2.1.0] - 2019-06-05

### Changed
- It is now possible to call `f_return` with no arguments. This produces a future
  with a return value of `None`.

## [2.0.2] - 2019-05-03

### Fixed
- Fixed an import error from autotests on Python 3.8

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


[Unreleased]: https://github.com/rohanpm/more-executors/compare/v2.8.2...HEAD
[2.8.2]: https://github.com/rohanpm/more-executors/compare/v2.8.1...v2.8.2
[2.8.1]: https://github.com/rohanpm/more-executors/compare/v2.8.0...v2.8.1
[2.8.0]: https://github.com/rohanpm/more-executors/compare/v2.7.0...v2.8.0
[2.7.0]: https://github.com/rohanpm/more-executors/compare/v2.6.0...v2.7.0
[2.6.0]: https://github.com/rohanpm/more-executors/compare/v2.5.1...v2.6.0
[2.5.1]: https://github.com/rohanpm/more-executors/compare/v2.5.0...v2.5.1
[2.5.0]: https://github.com/rohanpm/more-executors/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/rohanpm/more-executors/compare/v2.3.1...v2.4.0
[2.3.1]: https://github.com/rohanpm/more-executors/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/rohanpm/more-executors/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/rohanpm/more-executors/compare/v2.1.2...v2.2.0
[2.1.2]: https://github.com/rohanpm/more-executors/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/rohanpm/more-executors/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/rohanpm/more-executors/compare/v2.0.2...v2.1.0
[2.0.2]: https://github.com/rohanpm/more-executors/compare/v2.0.1...v2.0.2
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

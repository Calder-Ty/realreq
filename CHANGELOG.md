# Changelog

## [unreleased]

## 0.7.2
### Fixes/Improvements
- fixed bug where infinite loop could be created

## 0.7.1
### Fixes/Improvements
- realreq now works when the sourcefile is a python module (single python file)

## 0.7.0
### Added
- new `-i/--invert` flag will print out your dependencies in an inverted tree format


## 0.6.0
### Added
- Added help messages for CLI

## 0.5.2
### Fixes/Improvements
- Resolves a bug with alias-file specification that doesn't strip newlines

## 0.5.1
### Fixes/Improvements
- Resolve a [bug](https://github.com/Calder-Ty/realreq/issues/11) where realreq would crash on
unrecognized version format.

## 0.5.0
### Fixes/Improvements
- Significant performance improvements for larger codebases, when doing a deep search (14x improvements in some cases).

## 0.4.0
### Added

- New CLI flag `--alias` which can be used to specify aliases for packages with import names that
don't match their install names.

## 0.3.0 and prior
### Added

- Ability to switch between shallow and deep dependency searches (default is shallow).
- Initial Beta Release

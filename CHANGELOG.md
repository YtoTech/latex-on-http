# CHANGELOG

## 2025-02-13-1

* Fix build with XelaTeX [#43](https://github.com/YtoTech/latex-on-http/issues/43)

## 2024-06-28-2

* Run all commands in same directory to simplify path resolution for `filecontents` and uploaded resources

## 2024-06-28-1

* Set `cwd` for latexrun.py so the `filecontents` directives can work as expected #42

## 2023-06-12-1

* Timeout long LaTeX compilations and prevent zombie processes (the timeout is of 100 seconds for now)

## 2022-12-07-1

* Add clearer input spec (payload) validation

## 2022-08-03-1

* Add ghostscript runtime to the base Docker image

## 2022-07-31-1

* Make sync cache socket more reliable with lazy pirate pattern (prevent dead-lock on server crash)

## 2022-07-30-4

* Fix missing import on `app_cache.py`

## 2022-07-30-1

* Fix caching API

## 2022-05-23-1

* Fix Sentry Flask integration import

## 2022-05-17-3

* Add an environment variable `SENTRY_DSN` for Sentry tracking

## 2022-05-17-2

* Forget Alpine as Context seems [not to run](https://mailman.ntg.nl/pipermail/ntg-context/2021/101979.html) on it, keep to Debian

## 2022-05-17-1

* Use Alpine as default base image

## 2022-05-16-2

* Fix some Hy implementations after `1.0a4` bump 

## 2022-05-16-1

* Update Hy to `1.0a4`, as a consequence LaTeX-on-HTTP now require Python 3.7+

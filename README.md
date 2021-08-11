# realreq: real requirements for real projects

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/calder-ty/realreq/test?style=plastic) ![PyPI - Downloads](https://img.shields.io/pypi/dm/realreq?style=plastic) ![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/calder-ty/realreq?style=plastic)

`realreq` is _the_ lightweight tool that provides you with the actual
dependencies used by your project.

## Why use realreq?

### Better dependency management

It is not a secret that python package management is not the easiest.
Determining what packages you have installed are being used by your code, and
what their dependencies are is a hassle. `realreq` fixes this for you by
examining your source files and parsing out the dependencies for you.

### Lightweight

`realreq` does not depend on any third party package, except for `pip`. It
does not make any assumptions about the presence or absence of a virtual
environment, or what tool you used to make your virtual environment. This
means it will work with whatever tool set you are already using, without
getting in the way of your workflow

## Install

`realreq` is available for install via pip.

`pip install realreq`

## Usage

`realreq -s mypackage > requirements.txt`

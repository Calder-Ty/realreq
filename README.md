# realreq: real requirements for real projects

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/calder-ty/realreq/test?style=plastic) ![PyPI - Downloads](https://img.shields.io/pypi/dm/realreq?style=plastic) ![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/calder-ty/realreq?style=plastic)[![PyPI pyversions](https://img.shields.io/pypi/pyversions/realreq.svg)](https://pypi.python.org/pypi/realreq/)

`realreq` is _the_ lightweight tool that provides you with the actual
dependencies used by your project.

## Why use realreq?

### Better dependency management

It is not a secret that python package management is not easy.
Separating package dependencies from tool dependencies is enough to make you pull
your hair out. Determining what packages are actual being used by your code, and
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

### Shallow Dependencies
By default realreq delivers a "shallow" dependency specification, giving you a list of the packages
directly used by your code:

```
realreq -s ./path/to/mypackage > requirements.txt
```

This is useful for Library maintainers who want to make sure the minimal essentials are there,
without over specifying the actual requirements for their library.

### Deep Dependencies
Alternatively, you can get a "deep" dependency list by using the `-d` flag

```
realreq -d -s ./path/to/mypackage > requirements.txt
```

This is beneficial for maintaining executable/standalone programs, by defining the exact requirements under which
the program will function.

### Adding aliases

Due to the way python packaging works, it is possible for a python package to have a different _install_
name than _import_ name. Realreq works by inspecting your _imports_ and then checking the versions
they were installed with. If the names mismatch, there will be an issue with realreq being unable to
find them.

This can be resolved by adding an `--alias`/`-a` flag, mapping the _import_ name to the _install_ name.


```
realreq -d -s ./path/to/mypackage -a bs4=beautifulsoup4 > requirements.txt
```

If you have a lot of these aliases you can also specify them in an alias-file:

```
cat << EOF > realreq-aliases.txt
bs4=beautifulsoup4
airflow=apache-airflow
dateutil=python-dateutil
EOF
realreq -d -s ./path/to/mypackage --alias-file realreq-aliases.txt > requirements.txt
```




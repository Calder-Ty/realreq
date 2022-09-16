test:
	PYTHONPATH=. pytest

clean:
	rm dist/* || true

build: clean
	python3 -m build

push_pypi: build
	twine upload dist/*

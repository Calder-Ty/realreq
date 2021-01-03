import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="realreq",
    version="0.2.1",
    author="Tyler Calder",
    author_email="calder-ty@protonmail.com",
    description="CLI tool to gather dependencies for imports actually used by your code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Calder-Ty/realreq",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
    ],
    packages=["_realreq"],
    package_data={"_realreq": ["*.json"]},
    python_requires=">=3.5",
    entry_points={"console_scripts": ["realreq=_realreq.realreq:main"]},
)


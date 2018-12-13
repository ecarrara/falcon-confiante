import io
import re
import setuptools


with io.open("README.md", "r") as fh:
    long_description = fh.read()


with io.open("falcon_confiante/__init__.py", "rt", encoding="utf8") as f:
    version = re.search(r"__version__ = \"(.*?)\"", f.read()).group(1)


setuptools.setup(
    name="falcon-confiante",
    version="0.0.1",
    author="Erle Carrara",
    author_email="carrara.erle@gmail.com",
    description="Custom router an middleware to Spec Driven Development using OpenAPI v3 and Falcon.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ecarrara/falcon-confiante",
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    install_requires=["jsonschema>=2.6.0", "falcon>=1.4.0"],
    tests_require=["pytest", "pyyaml"],
    packages=["falcon_confiante"],
    keywords=["falcon", "openapi", "api", "swagger"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

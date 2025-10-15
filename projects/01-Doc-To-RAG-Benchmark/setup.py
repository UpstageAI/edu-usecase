from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as build_py_orig

ROOT = Path(__file__).parent.resolve()


class build_py(build_py_orig):  # type: ignore[override]
    """Custom build command that ensures the frontend bundle is up-to-date."""

    def run(self) -> None:  # noqa: D401
        script = ROOT / "scripts" / "build_frontend.py"
        skip_frontend = os.environ.get("SKIP_FRONTEND_BUILD") == "1"
        if script.exists() and not skip_frontend:
            try:
                subprocess.run([sys.executable, str(script)], check=True)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError('Frontend build failed. See the log above for details.') from exc
        super().run()


def read_readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


setup(
    name="pypi-upload-demo",
    version="0.1.4",
    description="FastAPI + React file upload demo packaged for PyPI distribution",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Your Name",
    url="https://example.com/pypi-upload-demo",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.115.5",
        "numpy>=1.24",
        "opencv-python-headless>=4.8",
        "Pillow>=10.0",
        "PyMuPDF>=1.24.0",
        "PyPDF2>=3.0.0",
        "langgraph>=0.6.0",
        "pdfplumber>=0.11.0",
        "pdfminer.six>=20231206",
        "pypdf>=4.0.0",
        "pypdfium2>=4.30.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "SQLAlchemy>=2.0",
        "aiosqlite>=0.19",
        "uvicorn>=0.32.1",
        "python-multipart>=0.0.20",
        "transformers>=4.36.2",
        "huggingface_hub>=0.15.0",
        "datasets>=2.16.2",
        "faiss-cpu>=1.7.4",
        "pydantic>=2.5.2",
        "openai>=1.42.1",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "pypi-test-app=pypi_test_app.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: FastAPI",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    cmdclass={"build_py": build_py},
)

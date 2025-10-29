"""Setup script for GitLab Secrets Manager."""
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="gitlab-secrets-manager",
    version="1.0.0",
    author="Nathaniel Koranteng",
    author_email="kora.nathaniel@gmail.com",
    description="A command-line tool for managing GitLab CI/CD variables (secrets)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/smylbb/gitlab_secrets_manager",
    py_modules=["gitlab_secrets", "gitlab_client", "config"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "gitlab-secrets=gitlab_secrets:cli",
        ],
    },
)


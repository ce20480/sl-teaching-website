# Poetry Package Manager Guide

This document explains how to use Poetry for dependency management in our project.

## What is Poetry?

Poetry is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.

## Installation

### Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Or on Windows:

```bash
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### Add Poetry to your PATH

The installer will add Poetry to your PATH, but you may need to restart your terminal or add it manually:

```bash
# For Linux/MacOS
export PATH="$HOME/.local/bin:$PATH"

# For Windows (PowerShell)
$Env:Path += ";$Env:APPDATA\Python\Scripts"
```

## Using Poetry in Our Project

### Initialize a New Project

```bash
cd your-project-directory
poetry init
```

This will create a `pyproject.toml` file.

### Add Dependencies

```bash
# Add a production dependency
poetry add sl-detection

# Add a development dependency
poetry add pytest --dev
```

### Install Dependencies

```bash
# Install all dependencies
poetry install

# Install without dev dependencies
poetry install --no-dev
```

### Update Dependencies

```bash
# Update all dependencies
poetry update

# Update a specific package
poetry update sl-detection
```

### Run Commands in Virtual Environment

```bash
# Run a Python script
poetry run python app.py

# Run a command
poetry run pytest

# Open a shell in the virtual environment
poetry shell
```

### Export Dependencies

```bash
# Export to requirements.txt
poetry export -f requirements.txt --output requirements.txt

# Include development dependencies
poetry export -f requirements.txt --dev --output dev-requirements.txt
```

## Integration with Our Sign Language Detection Project

### Setting Up for Development

1. Clone the repository

   ```bash
   git clone https://github.com/yourusername/asl-teaching-website.git
   cd asl-teaching-website
   ```

2. Install dependencies with Poetry

   ```bash
   cd backend/python
   poetry install
   ```

3. Install the sl-detection package
   ```bash
   poetry add sl-detection
   ```

### Specifying Package Versions

For our project, we recommend using semantic versioning constraints:

```toml
[tool.poetry.dependencies]
python = "^3.11"
sl-detection = "^0.1.6"
fastapi = "^0.100.0"
uvicorn = "^0.23.0"
```

### Developing with the sl-detection Package

If you're developing both our application and the sl-detection package simultaneously:

1. Install the package in development mode

   ```bash
   poetry add ../path/to/SignLanguageDetection/
   ```

2. Or use a direct GitHub reference
   ```bash
   poetry add git+https://github.com/ce20480/SignLanguageDetection.git
   ```

## Troubleshooting

### Lock File Issues

If you encounter conflicts in the lock file:

```bash
poetry lock --no-update
```

### Virtual Environment Issues

If you need to recreate the virtual environment:

```bash
poetry env remove python
poetry install
```

### Package Not Found

Make sure the PyPI repository is accessible:

```bash
poetry config repositories.pypi https://pypi.org/simple
```

## Additional Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [Poetry GitHub Repository](https://github.com/python-poetry/poetry)
- [Poetry Cheat Sheet](https://gist.github.com/CarlosAMolina/57eb688d896743be1b7d7774d65a5792)

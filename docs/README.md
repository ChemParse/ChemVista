# ChemVista Documentation

This directory contains the Sphinx documentation for ChemVista.

## Building the Documentation

### Prerequisites

Install documentation dependencies:

```bash
pip install -r requirements.txt
```

Or with Poetry:

```bash
poetry install
```

### Build HTML Documentation

```bash
cd docs
make html
```

The built documentation will be in `docs/build/html/index.html`.

### Other Build Formats

```bash
# PDF (requires LaTeX)
make latexpdf

# ePub
make epub

# Plain text
make text

# Check for broken links
make linkcheck
```

### Clean Build Files

```bash
make clean
```

## Documentation Structure

```
docs/
├── source/
│   ├── index.rst              # Main documentation page
│   ├── conf.py                # Sphinx configuration
│   ├── user_guide/            # User documentation
│   │   ├── installation.rst
│   │   ├── cli.rst
│   │   ├── gui.rst
│   │   └── file_formats.rst
│   ├── tutorials/             # Step-by-step tutorials
│   │   ├── basic_visualization.rst
│   │   ├── trajectory_export.rst
│   │   ├── scalar_fields.rst
│   │   └── scene_management.rst
│   ├── api/                   # API reference
│   │   ├── scene_manager.rst
│   │   ├── exporter.rst
│   │   ├── renderer.rst
│   │   └── scene_objects.rst
│   └── developer/             # Developer documentation
│       ├── architecture.rst
│       ├── testing.rst
│       └── contributing.rst
├── build/                     # Generated documentation (gitignored)
├── Makefile                   # Build automation
└── requirements.txt           # Documentation dependencies
```

## Viewing Documentation

### Local Preview

After building, open in browser:

```bash
# Linux/macOS
open build/html/index.html

# Or use Python's HTTP server
cd build/html
python -m http.server 8000
# Then visit http://localhost:8000
```

### Online Hosting

The documentation can be hosted on:

- **Read the Docs**: Automatic builds from GitHub
- **GitHub Pages**: Static hosting
- **Self-hosted**: Any web server

## Contributing to Documentation

### Style Guide

- Use reStructuredText (`.rst`) format
- Follow Sphinx conventions
- Include code examples where appropriate
- Add cross-references with `:doc:`, `:class:`, `:meth:`
- Keep line length reasonable (~100 characters)

### Adding New Pages

1. Create new `.rst` file in appropriate directory
2. Add to relevant `toctree` directive in `index.rst` or parent page
3. Build and verify links work

### API Documentation

API documentation is auto-generated from docstrings using:

- `sphinx.ext.autodoc`: Extract from source code
- `sphinx.ext.napoleon`: Support Google/NumPy style docstrings

### Examples

**Code Block:**

```rst
.. code-block:: python

   from chemvista import SceneManager
   scene = SceneManager()
```

**Cross-reference:**

```rst
See :class:`chemvista.scene_manager.SceneManager` for details.
```

**Note Box:**

```rst
.. note::
   This is an important note.
```

**Warning Box:**

```rst
.. warning::
   Be careful with this feature.
```

## Troubleshooting

### Module import errors

If Sphinx can't import ChemVista modules:

```bash
# Ensure ChemVista is installed
pip install -e ..

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
```

### Missing theme

If RTD theme is not found:

```bash
pip install sphinx-rtd-theme
```

### LaTeX errors (for PDF)

PDF generation requires LaTeX:

```bash
# Ubuntu/Debian
sudo apt-get install texlive-latex-full

# macOS
brew install --cask mactex
```

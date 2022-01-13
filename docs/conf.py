# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config


# -- Project information -----------------------------------------------------
import importlib.metadata

metadata = importlib.metadata.metadata("slotscheck")

project = metadata["Name"]
author = metadata["Author"]

version = metadata["Version"]
release = metadata["Version"]

# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_click",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "emacs"

autodoc_member_order = "bysource"


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_material"

# html_static_path = ['_static']
# highlight_language = "python3"

# Material theme options (see theme.conf for more information)
html_theme_options = {
    "nav_title": "🎰 Slotscheck",
    # Set the color and the accent color
    "color_primary": "red",
    "color_accent": "light-red",
    # Set the repo location to get a badge with stats
    "repo_url": "https://github.com/ariebovenberg/slotscheck/",
    "repo_name": "slotscheck",
    # Visible levels of the global TOC; -1 means unlimited
    "globaltoc_depth": 3,
    # If False, expand all TOC entries
    "globaltoc_collapse": False,
    # If True, show hidden TOC entries
    "globaltoc_includehidden": False,
}


html_sidebars = {
    "**": [
        "logo-text.html",
        "globaltoc.html",
        "localtoc.html",
        "searchbox.html",
    ]
}


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

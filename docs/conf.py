# -- Project information -----------------------------------------------------
import importlib.metadata

metadata = importlib.metadata.metadata("slotscheck")

project = metadata["Name"]
author = metadata["Author"]

version = metadata["Version"]
release = metadata["Version"]

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_click",
]

templates_path = ["_templates"]

source_suffix = ".rst"

# The master toctree document.
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output ----------------------------------------------

html_theme = "furo"
pygments_style = "tango"
highlight_language = "python3"
pygments_style = "default"
pygments_dark_style = "lightbulb"
autodoc_member_order = "bysource"

toc_object_entries_show_parents = "hide"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Configuration file for the Sphinx documentation builder.
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('../..'))

# Project information
project = 'ndp-ep'
copyright = '2025, NDP EP Team'
author = 'NDP EP Team'
release = '0.1.0'
version = '0.1.0'

# Extensions - keep minimal for RTD compatibility
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

# Templates and exclusions
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML output options
html_theme = 'sphinx_rtd_theme'
html_static_path = []

# Theme options
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

# Mock imports for packages that might not be available during build
autodoc_mock_imports = []

# Suppress warnings
suppress_warnings = ['toc.not_readable', 'ref.any']

# Master document
master_doc = 'index'

# Language
language = 'en'
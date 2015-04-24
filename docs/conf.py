# -*- coding: utf-8 -*-

import sys
import os

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'safepy2'
copyright = u'2015, Sangoma Technologies Corp.'

version = '1'
release = '1'

exclude_patterns = ['_build']

pygments_style = 'sphinx'


# -- Options for HTML output ----------------------------------------------

try:
    import sphinx_rtd_theme
except ImportError:
    html_theme = 'default'
    html_theme_path = []
else:
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# html_static_path = ['_static']
htmlhelp_basename = 'safepy2doc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

latex_documents = [
  ('index', 'safepy2.tex', u'safepy2 Documentation',
   u'Sangoma Technologies Corp.', 'manual'),
]

# -- Options for manual page output ---------------------------------------

man_pages = [
    ('index', 'safepy2', u'safepy2 Documentation',
     [u'Sangoma Technologies Corp.'], 1)
]

# -- Options for Texinfo output -------------------------------------------

texinfo_documents = [
  ('index', 'safepy2', u'safepy2 Documentation',
   u'Sangoma Technologies Corp.', 'safepy2',
   'One line description of project.', 'Miscellaneous'),
]

OceanVal
========

Automated validation of ocean models in Python.

OceanVal matches model output with gridded and point observations, then
creates reproducible validation reports covering bias, correlation,
seasonality, spatial patterns, and vertical profiles.

Start here
----------

1. :doc:`installing` - install OceanVal and its scientific dependencies.
2. :doc:`quickstart` - run your first matchup and validation report.
3. :doc:`obs_data` - configure observations and built-in recipes.
4. :doc:`api` - find functions and parameters.

The usual workflow is to register observations, match model output with
:func:`oceanval.matchup`, and build an HTML report with
:func:`oceanval.validate`.

Documentation
-------------


.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   installing.rst
   quickstart.rst
   how_to_use.rst
   q_a.rst


.. toctree::
   :maxdepth: 1
   :caption: Data handling

   obs_data.rst
   info.rst



**Help & reference**


.. toctree::
   :maxdepth: 1
   :caption: Help & reference

   api.rst
   




















OceanVal
========

Automated validation of ocean models in Python.

OceanVal matches model output with gridded and point observations, then
creates reproducible validation reports covering bias, correlation,
seasonality, spatial patterns, and vertical profiles.

Start here
----------

.. list-table::
    :widths: 28 72
    :class: oceanval-start-here
    :header-rows: 1

    * - Goal
       - Page
    * - Install OceanVal
       - :doc:`installing`
    * - Run a first validation
       - :doc:`quickstart`
    * - Configure observations
       - :doc:`obs_data`
    * - Find functions and parameters
       - :doc:`api`

The usual workflow is to register observations, match model output with
:func:`oceanval.matchup`, and build an HTML report with
:func:`oceanval.validate`.

Documentation
-------------


.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installing.rst
   quickstart.rst
   how_to_use.rst
   examples.rst
   q_a.rst


.. toctree::
   :maxdepth: 1
   :caption: Data handling

   obs_data.rst
   recipes.rst
   info.rst



**Help & reference**


.. toctree::
   :maxdepth: 1
   :caption: Help & reference

   api.rst
   




















NDP EP Python Client Library
=============================

.. image:: https://github.com/sci-ndp/ndp-ep-py/workflows/CI/badge.svg
   :target: https://github.com/sci-ndp/ndp-ep-py/actions
   :alt: CI Status

.. image:: https://codecov.io/gh/sci-ndp/ndp-ep-py/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/sci-ndp/ndp-ep-py
   :alt: Coverage

.. image:: https://badge.fury.io/py/ndp-ep.svg
   :target: https://badge.fury.io/py/ndp-ep
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/ndp-ep.svg
   :target: https://pypi.org/project/ndp-ep/
   :alt: Python versions

**ndp-ep** is a Python client library for interacting with the National Data Platform (NDP) EP API. 
This library provides a simple and intuitive interface for managing datasets, organizations, 
resources, and services through the API.

Features
--------

* **Complete API Coverage**: Support for all API endpoints including Kafka topics, S3 resources, URL resources, organizations, and services
* **Authentication**: Token-based and username/password authentication
* **Search Functionality**: Advanced search capabilities across datasets and resources
* **Error Handling**: Comprehensive error handling with meaningful error messages
* **Type Hints**: Full type hint support for better IDE integration
* **Testing**: Extensive test coverage (>89%) with unit and integration tests

Quick Start
-----------

Install the library:

.. code-block:: bash

   pip install ndp-ep

Basic usage:

.. code-block:: python

   from ndp_ep import APIClient

   # Initialize client with token
   client = APIClient(
       base_url="http://155.101.6.191:8003",
       token="your-access-token"
   )

   # List organizations
   organizations = client.list_organizations()
   print(organizations)

   # Search datasets
   results = client.search_datasets(
       terms=["climate", "temperature"],
       server="global"
   )

Interactive Examples
-------------------

Try the library interactively:

.. raw:: html

   <p>
   <a href="https://colab.research.google.com/github/sci-ndp/ndp-ep-py/blob/main/docs/source/tutorials/getting_started.ipynb" target="_blank">
   <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
   </a>
   </p>

.. raw:: html

   <p>
   <a href="https://mybinder.org/v2/gh/sci-ndp/ndp-ep-py/main?filepath=docs%2Fsource%2Ftutorials%2Fgetting_started.ipynb" target="_blank">
   <img src="https://mybinder.org/badge_logo.svg" alt="Launch Binder"/>
   </a>
   </p>

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart
   authentication

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/organizations
   user_guide/resources
   user_guide/search
   user_guide/system_info

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/getting_started
   tutorials/data_management_workflow
   tutorials/advanced_search

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api_reference

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
NDP EP Python Client Library
=============================

**ndp-ep** is a Python client library for interacting with the National Data Platform (NDP) EP API.

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

**Try our interactive tutorial first!**

.. raw:: html

   <p>
   <a href="https://colab.research.google.com/github/sci-ndp/ndp-ep-py/blob/main/docs/source/tutorials/getting_started.ipynb" target="_blank">
   <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
   </a>
   <a href="https://mybinder.org/v2/gh/sci-ndp/ndp-ep-py/main?filepath=docs%2Fsource%2Ftutorials%2Fgetting_started.ipynb" target="_blank">
   <img src="https://mybinder.org/badge_logo.svg" alt="Binder"/>
   </a>
   </p>

The tutorial includes:

* 🔧 **Client setup and authentication** - Secure token configuration
* 🏢 **Working with organizations** - Create and manage data containers
* 🔍 **Searching datasets** - Simple and advanced search techniques  
* 📊 **Registering resources** - URL, S3, and Kafka topic registration
* 🛡️ **Error handling** - Best practices for robust applications

Documentation
-------------

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

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api_reference

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
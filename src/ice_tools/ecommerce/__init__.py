"""iceOS *e-commerce* toolkit (initial scaffold).

This package will house the next-generation, commerce-focused tools that power
Kim’s end-to-end listing workflow:

* CSV ingestion (already implemented upstream in ``ice_tools.csv_loader``)
* Dynamic pricing strategy
* Marketplace HTTP client
* LLM-backed copy generator (title & description)
* Aggregation / post-processing utilities

The modules will be added incrementally – for now this ``__init__`` only
exposes basic package metadata so that other layers can import
``ice_tools.ecommerce`` without breaking.
"""

from __future__ import annotations

__all__: list[str] = []  # Will be populated as tools are added

__version__: str = "0.1.0"

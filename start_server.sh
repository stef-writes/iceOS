#!/bin/bash
PYTHONPATH=$PYTHONPATH:src ./venv/bin/uvicorn src.app.main:app --reload 
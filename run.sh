#!/bin/bash
uvicorn app:sio_app --host 0.0.0.0 --port 5069 --reload

#!/bin/bash
echo "=========================================="
echo "  EmoLearn v2 — Starting Server 🚀"
echo "=========================================="
cd "$(dirname "$0")/emolearn-backend"
pip install -r requirements.txt -q
python app.py

#!/bin/bash
python3 -m venv venv_test
source venv_test/bin/activate
pip install pip -U
pip install datasets "huggingface-hub>=0.30" "hf-transfer>=0.1.4" "protobuf<4" "click<8.1"
pip install -r requirements.txt gradio[oauth,mcp]==6.13.0 "uvicorn>=0.14.0" "websockets>=10.4" spaces

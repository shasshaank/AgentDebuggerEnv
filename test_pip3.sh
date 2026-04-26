#!/bin/bash
python3 -m venv venv_test3
source venv_test3/bin/activate
pip install pip -U
pip install datasets "huggingface-hub>=0.30" "hf-transfer>=0.1.4" "protobuf<4" "click<8.1"
pip install -r req_test2.txt spaces

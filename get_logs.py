import urllib.request
import json
import sys

url = "https://huggingface.co/api/spaces/shashaank0707/AgentDebugger-training-v3"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    
# Not sure where the build logs are in the API, but I can check the state
print(data.get('runtime', {}).get('stage'))

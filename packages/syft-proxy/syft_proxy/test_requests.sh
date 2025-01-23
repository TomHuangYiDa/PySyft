#!/bin/bash

# Configuration
# should be http://syftbox.localhost/...
URL="http://0.0.0.0:9081/rpc?method=get&datasite=shubham%40openmined.org&path=%2Fpublic%2Frpc"
CONTENT_TYPE="Content-Type: application/json"

# Basic RPC call with empty body
echo "Testing RPC endpoint with simple message..."
curl -X POST "${URL}" \
  -H "${CONTENT_TYPE}" \
  -d 'ping'

echo -e "\n"

# # RPC call with parameters
# echo "Testing RPC endpoint with parameters..."
# curl -X POST "${API_URL}/rpc" \
#   -H "${CONTENT_TYPE}" \
#   -d '{"param1": "value1", "param2": "value2"}'

# echo -e "\n"

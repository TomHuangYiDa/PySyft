#!/bin/bash

# Configuration
HOST="http://0.0.0.0:9081"
REQUEST_ID="01JJ75KZ9Y2Q4MX5M3CAQMMX35"
PARAMS="method=get&datasite=yash%40openmined.org&path=%2Fpublic%2Frpc"

# Construct URL
URL="${HOST}/rpc/reply/${REQUEST_ID}?${PARAMS}"

# Make the request
curl -X POST "${URL}" \
  -H "Content-Type: application/json" \
  -d '{"your": "response data"}'
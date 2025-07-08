#!/bin/bash
echo "Testing backend health endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool

echo -e "\n\nTesting PagerDuty endpoint exists..."
curl -I http://localhost:8000/pagerduty/token/test
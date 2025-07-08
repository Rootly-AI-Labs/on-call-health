#!/bin/bash

echo "Fetching your PagerDuty services..."
echo "================================="

curl --request GET \
  --url https://api.pagerduty.com/services \
  --header 'Accept: application/vnd.pagerduty+json;version=2' \
  --header 'Authorization: Token token=u+yU3VeLnT_d1HuYzDrg' \
  --header 'Content-Type: application/json' \
  | python3 -m json.tool | grep -E '"id"|"name"|"status"' | head -20

echo ""
echo "Look for the 'id' field after your service name"
echo "That's your Service ID to use for creating incidents"
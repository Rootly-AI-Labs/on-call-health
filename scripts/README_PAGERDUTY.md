# PagerDuty Test Incident Scripts

This directory contains scripts to create test incidents in PagerDuty for testing the burnout detector.

## Two Approaches

### 1. Events API (Recommended - Simpler)
**File:** `create_pagerduty_events.py`

This uses PagerDuty's Events API v2 and only requires an integration key.

#### Setup:
1. Go to PagerDuty → Services → Your Service
2. Go to the Integrations tab
3. Add an integration → Events API V2
4. Copy the Integration Key (Routing Key)

#### Usage:
```bash
# Make the script executable
chmod +x create_pagerduty_events.py

# Create 5 test incidents
python create_pagerduty_events.py --key YOUR_INTEGRATION_KEY

# Create 10 incidents
python create_pagerduty_events.py --key YOUR_INTEGRATION_KEY --count 10

# Create incidents and auto-resolve after 30 seconds
python create_pagerduty_events.py --key YOUR_INTEGRATION_KEY --count 5 --auto-resolve 30

# Create a custom incident
python create_pagerduty_events.py --key YOUR_INTEGRATION_KEY --custom "Database connection failed" --severity critical
```

### 2. REST API (More Control)
**File:** `create_pagerduty_incidents.py`

This uses PagerDuty's REST API and provides more control over incident properties.

#### Setup:
1. Go to PagerDuty → User Icon → My Profile → User Settings
2. Create an API User Token
3. Copy the token

#### Usage:
```bash
# Make the script executable
chmod +x create_pagerduty_incidents.py

# List available services
python create_pagerduty_incidents.py --token YOUR_API_TOKEN --list-services

# List available users
python create_pagerduty_incidents.py --token YOUR_API_TOKEN --list-users

# Create 5 test incidents for a service
python create_pagerduty_incidents.py --token YOUR_API_TOKEN --service-id SERVICE_ID --count 5

# Create incidents with random user assignment
python create_pagerduty_incidents.py --token YOUR_API_TOKEN --service-id SERVICE_ID --count 10 --assign-randomly

# Create with 50% high urgency incidents
python create_pagerduty_incidents.py --token YOUR_API_TOKEN --service-id SERVICE_ID --count 10 --urgency-high-pct 50

# Create and auto-resolve after 60 seconds
python create_pagerduty_incidents.py --token YOUR_API_TOKEN --service-id SERVICE_ID --count 5 --auto-resolve 60
```

## Test Scenarios

Both scripts create realistic test incidents including:
- High CPU usage alerts
- Database connection issues
- API performance degradation
- Memory leaks
- Disk space warnings
- SSL certificate expiration
- Security alerts
- Queue backlogs
- Health check failures

## Tips for Testing Burnout Detection

1. **Create incidents over time**: Run the script multiple times with delays to simulate real incident patterns
   ```bash
   # Create 5 incidents every hour for 4 hours
   for i in {1..4}; do
     python create_pagerduty_events.py --key YOUR_KEY --count 5
     sleep 3600
   done
   ```

2. **Vary urgency levels**: Use different severity levels to test how the burnout detector handles different incident types

3. **Assign to specific users**: Use the REST API script with `--assign-randomly` to distribute incidents across team members

4. **Weekend/after-hours testing**: Run the scripts outside business hours to test after-hours incident detection

5. **Burst patterns**: Create many incidents quickly to simulate incident storms
   ```bash
   # Create 20 incidents in rapid succession
   python create_pagerduty_events.py --key YOUR_KEY --count 20
   ```

## Cleanup

To clean up test incidents:
1. Use the `--auto-resolve` flag when creating incidents
2. Or manually resolve/delete them in the PagerDuty UI
3. Or use PagerDuty's bulk operations in the web interface

## Requirements

```bash
pip install requests
```

Both scripts only require the `requests` library.
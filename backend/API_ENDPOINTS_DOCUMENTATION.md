# Burnout Analysis API Endpoints

This document describes the new burnout analysis API endpoints implemented for the Rootly burnout detector app.

## Overview

The API provides endpoints for running burnout analyses, retrieving analysis results, and managing analysis history. The system uses Rootly integration data to analyze incident patterns and calculate burnout risk scores for team members.

## Endpoints

### 1. POST /analyses/run

**Purpose**: Run a new burnout analysis for a specific integration and time range.

**Request Body**:
```json
{
  "integration_id": 1,
  "time_range": 30,
  "include_weekends": true
}
```

**Response**:
```json
{
  "id": 123,
  "integration_id": 1,
  "status": "pending",
  "created_at": "2023-12-01T10:00:00Z",
  "completed_at": null,
  "time_range": 30,
  "analysis_data": null
}
```

**Process**:
1. Validates that the integration belongs to the current user
2. Creates a new analysis record in the database
3. Starts background analysis task
4. Returns immediately with analysis ID and status

### 2. GET /analyses

**Purpose**: List all previous analyses for the current user.

**Query Parameters**:
- `integration_id` (optional): Filter by specific integration
- `limit` (optional, default: 20): Maximum number of results
- `offset` (optional, default: 0): Pagination offset

**Response**:
```json
{
  "analyses": [
    {
      "id": 123,
      "integration_id": 1,
      "status": "completed",
      "created_at": "2023-12-01T10:00:00Z",
      "completed_at": "2023-12-01T10:05:00Z",
      "time_range": 30,
      "analysis_data": { ... }
    }
  ],
  "total": 1
}
```

### 3. GET /analyses/{id}

**Purpose**: Get a specific analysis result.

**Path Parameters**:
- `id`: Analysis ID

**Response**:
```json
{
  "id": 123,
  "integration_id": 1,
  "status": "completed",
  "created_at": "2023-12-01T10:00:00Z",
  "completed_at": "2023-12-01T10:05:00Z",
  "time_range": 30,
  "analysis_data": {
    "analysis_timestamp": "2023-12-01T10:05:00Z",
    "metadata": {
      "days_analyzed": 30,
      "total_users": 5,
      "total_incidents": 42,
      "include_weekends": true
    },
    "team_health": {
      "overall_score": 7.2,
      "risk_distribution": {
        "low": 2,
        "medium": 2,
        "high": 1,
        "critical": 0
      },
      "average_burnout_score": 2.8,
      "health_status": "good",
      "members_at_risk": 1
    },
    "team_analysis": {
      "members": [
        {
          "user_id": 1,
          "user_name": "John Doe",
          "user_email": "john@example.com",
          "burnout_score": 4.5,
          "risk_level": "high",
          "incident_count": 15,
          "factors": {
            "workload": 6.2,
            "after_hours": 3.8,
            "weekend_work": 2.1,
            "incident_load": 5.7,
            "response_time": 3.2
          },
          "metrics": {
            "incidents_per_week": 3.5,
            "after_hours_percentage": 0.27,
            "weekend_percentage": 0.13,
            "avg_response_time_minutes": 25.4,
            "severity_distribution": {
              "critical": 2,
              "high": 5,
              "medium": 6,
              "low": 2
            }
          }
        }
      ]
    },
    "insights": [
      {
        "type": "warning",
        "category": "team",
        "message": "1 team member is at high or critical burnout risk",
        "priority": "high"
      }
    ],
    "recommendations": [
      "Schedule 1-on-1s with the 1 team member at high/critical risk",
      "Review weekend on-call compensation and rotation frequency"
    ]
  }
}
```

## Analysis Data Structure

### Team Health Score
- **overall_score**: 0-10 scale (10 = excellent health)
- **risk_distribution**: Count of members at each risk level
- **average_burnout_score**: Team average burnout score
- **health_status**: "excellent", "good", "fair", or "poor"

### Individual Member Analysis
- **burnout_score**: 0-10 scale (10 = maximum burnout risk)
- **risk_level**: "low", "medium", "high", or "critical"
- **factors**: Individual burnout factors (0-10 scale each)
  - **workload**: Based on incident frequency
  - **after_hours**: Work outside business hours (9AM-6PM)
  - **weekend_work**: Weekend incident involvement
  - **incident_load**: Severity-weighted incident count
  - **response_time**: Average time to respond to incidents

### Metrics
- **incidents_per_week**: Average incidents per week
- **after_hours_percentage**: Percentage of incidents outside business hours
- **weekend_percentage**: Percentage of incidents on weekends
- **avg_response_time_minutes**: Average response time in minutes
- **severity_distribution**: Count of incidents by severity level

## Background Processing

Analyses are processed asynchronously in the background to avoid blocking the API:

1. **Pending**: Analysis request received, queued for processing
2. **Running**: Background task is fetching data and running analysis
3. **Completed**: Analysis finished successfully, results available
4. **Failed**: Analysis failed due to error (check error_message field)

## Data Sources

The analysis fetches data from Rootly API including:
- **Incidents**: For the specified time period
- **Users**: Team member information
- **Incident assignments**: Who created, acknowledged, and resolved incidents
- **Timestamps**: For after-hours and weekend work analysis
- **Severity levels**: For weighted incident load calculation

## Authentication

All endpoints require authentication. The system uses JWT tokens and ensures that:
- Users can only access their own analyses
- Integration ownership is verified before running analyses
- Background tasks are scoped to the requesting user

## Error Handling

Common error responses:
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **404 Not Found**: Analysis or integration not found
- **500 Internal Server Error**: Server error during analysis

## Rate Limiting

Consider implementing rate limiting for the POST /analyses/run endpoint to prevent abuse, as each analysis involves significant API calls to Rootly.
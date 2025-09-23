# Automated DM Burnout Survey System - Implementation Plan

## Executive Summary
Transform from slash command-driven to **proactive bot-initiated DM surveys** as the primary burnout detection method, while maintaining slash command as backup.

---

## Current State Analysis

### ✅ Existing Infrastructure:
- Slack bot with `/burnout-survey` command ✅
- 3-question burnout survey modal ✅
- User correlation system ✅
- Organization workspace mapping ✅
- Survey response collection ✅
- Analysis integration ✅

### 🔄 Required Changes:
- **Primary**: Automated DM-based survey delivery
- **Secondary**: Keep slash command as fallback option

---

## Proposed Architecture: Automated DM Survey System

### 1. Bot Triggering Mechanisms

#### A. Analysis-Driven Triggers (Primary)
```python
# Trigger surveys after burnout analysis completion
@router.post("/internal/analysis-completed")
async def trigger_post_analysis_surveys(analysis_id: int):
    """Send DM surveys to all team members after analysis completes."""

    # Get analysis results and identify users needing surveys
    high_risk_users = get_high_risk_members(analysis_id)
    all_team_members = get_analysis_team_members(analysis_id)

    # Prioritize high-risk users (immediate)
    await send_priority_dm_surveys(high_risk_users, urgency="high")

    # Send to all other team members (24h delay)
    await schedule_dm_surveys(all_team_members, delay_hours=24)
```

#### B. Schedule-Based Triggers (Secondary)
```python
# Weekly/monthly scheduled check-ins
@scheduler.cron("0 10 * * 1")  # Monday 10 AM
async def weekly_burnout_checkin():
    """Proactive weekly burnout check-in for all active teams."""
    active_orgs = get_active_organizations()

    for org in active_orgs:
        team_members = get_slack_users(org.slack_workspace_id)
        await send_scheduled_surveys(team_members, survey_type="weekly")
```

#### C. Event-Driven Triggers (Advanced)
```python
# Incident-based triggers
@router.post("/webhooks/incident-spike")
async def incident_spike_survey():
    """Send immediate surveys after incident spikes."""

# Manager-requested surveys
@router.post("/api/manager/request-team-survey")
async def manager_initiated_survey():
    """Allow managers to trigger team surveys."""
```

### 2. Direct Message Delivery System

#### A. DM Survey Architecture
```python
class DMSurveyService:
    async def send_dm_survey(self, user_slack_id: str, survey_config: dict):
        """Send direct message with survey modal to user."""

        # 1. Open DM channel
        dm_channel = await self.slack_client.conversations_open(users=[user_slack_id])

        # 2. Send contextual message with survey button
        message_blocks = self.create_survey_message(survey_config)

        # 3. Post message with modal trigger
        await self.slack_client.chat_postMessage(
            channel=dm_channel["channel"]["id"],
            blocks=message_blocks,
            text="Quick burnout check-in"
        )
```

#### B. Message Templates by Context
```python
DM_TEMPLATES = {
    "post_analysis": {
        "title": "📊 Your Team Analysis Results Are Ready",
        "message": "Hi {name}! We just completed your team's burnout analysis. Could you help us validate our findings with a quick 2-minute check-in?",
        "urgency": "normal"
    },

    "high_risk": {
        "title": "🤝 Quick Wellness Check-In",
        "message": "Hi {name}! Our analysis suggests you might be under higher stress lately. Would you mind sharing how you're feeling? Your response helps us support you better.",
        "urgency": "high",
        "follow_up": True
    },

    "weekly": {
        "title": "📈 Weekly Team Health Check",
        "message": "Hi {name}! Time for our weekly wellness check-in. How has your workweek been?",
        "urgency": "low"
    }
}
```

### 3. Enhanced Survey Modal Design

#### A. Context-Aware Questions
```python
def create_contextual_survey_modal(user_data: dict, trigger_context: str):
    """Create survey modal adapted to user context and trigger reason."""

    base_questions = get_core_burnout_questions()

    if trigger_context == "high_risk":
        # Add targeted questions for high-risk users
        questions.extend([
            {
                "question": "What's been your biggest source of work stress lately?",
                "type": "select",
                "options": ["Workload", "On-call burden", "Deadlines", "Team dynamics", "Technical challenges"]
            }
        ])

    elif trigger_context == "post_incident_spike":
        # Add incident-specific questions
        questions.extend([
            {
                "question": "How did the recent incidents affect your stress level?",
                "type": "scale",
                "range": [1, 10]
            }
        ])

    return build_modal(questions, context=trigger_context)
```

#### B. Progressive Survey Logic
```python
# Adaptive questioning based on responses
SURVEY_FLOW = {
    "burnout_score_low": ["basic_wellness", "workload_check"],
    "burnout_score_medium": ["stress_sources", "support_needs", "workload_check"],
    "burnout_score_high": ["urgent_support", "stress_sources", "intervention_preferences"]
}
```

### 4. Smart Delivery System

#### A. Timing Optimization
```python
class SmartDeliveryScheduler:
    async def optimize_delivery_time(self, user_id: str):
        """Find optimal time to send DM survey based on user activity."""

        # Analyze user's Slack activity patterns
        activity_pattern = await self.analyze_user_activity(user_id)

        # Avoid busy periods (high message volume)
        # Target low-activity, high-availability windows
        optimal_times = self.calculate_optimal_windows(activity_pattern)

        return optimal_times[0]  # Best time
```

#### B. Frequency Management
```python
SURVEY_FREQUENCY_RULES = {
    "max_surveys_per_week": 2,
    "min_hours_between_surveys": 72,
    "high_risk_exception": {
        "max_per_week": 3,
        "min_hours_between": 48
    },
    "user_opt_out_respected": True
}
```

### 5. Response Collection & Integration

#### A. Enhanced Response Processing
```python
@router.post("/slack/survey-response")
async def process_dm_survey_response(response: SlackSurveyResponse):
    """Process survey response from DM-initiated survey."""

    # 1. Store response with context metadata
    survey_response = UserBurnoutReport(
        user_id=response.user_id,
        analysis_id=response.analysis_id,
        delivery_method="dm_bot",
        trigger_context=response.context,  # post_analysis, high_risk, weekly
        response_data=response.answers,
        response_time_seconds=response.completion_time
    )

    # 2. Real-time analysis integration
    await update_user_risk_profile(survey_response)

    # 3. Trigger follow-up actions if needed
    if survey_response.indicates_high_risk():
        await trigger_support_workflow(survey_response)
```

#### B. Follow-Up Automation
```python
async def handle_survey_follow_ups(response: UserBurnoutReport):
    """Automated follow-up based on survey responses."""

    if response.burnout_score >= 70:  # High risk
        # Immediate manager notification
        await notify_manager(response.user_id, urgency="high")

        # Schedule check-in in 3 days
        await schedule_follow_up_survey(response.user_id, days=3)

    elif response.burnout_score >= 50:  # Medium risk
        # Weekly follow-up
        await schedule_follow_up_survey(response.user_id, days=7)
```

---

## Implementation Roadmap

### Phase 1: Core DM Infrastructure (Week 1-2)
- [ ] **DM Service Setup**
  - Slack bot DM capabilities
  - Message template system
  - Modal delivery via DM

- [ ] **Basic Triggers**
  - Post-analysis survey dispatch
  - Manual trigger for testing

- [ ] **Response Integration**
  - DM survey response handling
  - Existing analysis integration

### Phase 2: Smart Delivery (Week 3-4)
- [ ] **Timing Optimization**
  - User activity analysis
  - Optimal delivery windows
  - Frequency management

- [ ] **Context-Aware Surveys**
  - High-risk targeted surveys
  - Incident-based triggers
  - Personalized messaging

### Phase 3: Advanced Features (Week 5-6)
- [ ] **Scheduled Surveys**
  - Weekly/monthly check-ins
  - Team-wide campaigns
  - Manager-initiated surveys

- [ ] **Follow-Up Automation**
  - Risk-based follow-ups
  - Manager notifications
  - Support workflow triggers

### Phase 4: Analytics & Optimization (Week 7-8)
- [ ] **Response Analytics**
  - DM vs slash command comparison
  - Response rate optimization
  - Delivery time analysis

- [ ] **User Experience**
  - Survey fatigue prevention
  - Personalization improvements
  - Opt-out management

---

## Technical Implementation Details

### New Files/Components Needed:

```
backend/app/services/
├── dm_survey_service.py          # Core DM survey logic
├── survey_scheduler.py           # Timing and frequency management
├── survey_trigger_service.py     # Event-based trigger handling
└── survey_analytics_service.py   # Response analytics

backend/app/models/
├── survey_delivery_log.py        # Track all survey deliveries
└── survey_trigger_event.py       # Log trigger events

backend/app/api/endpoints/
├── dm_survey.py                  # DM survey endpoints
└── survey_admin.py               # Manager/admin controls

backend/app/tasks/
├── scheduled_surveys.py          # Background job for scheduled surveys
└── survey_follow_ups.py          # Automated follow-up tasks
```

### Database Schema Changes:
```sql
-- Track survey delivery methods and success
CREATE TABLE survey_delivery_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    delivery_method VARCHAR(20), -- 'dm_bot', 'slash_command'
    trigger_context VARCHAR(50), -- 'post_analysis', 'high_risk', 'scheduled'
    sent_at TIMESTAMP DEFAULT NOW(),
    delivered BOOLEAN DEFAULT FALSE,
    opened BOOLEAN DEFAULT FALSE,
    completed BOOLEAN DEFAULT FALSE,
    completion_time_seconds INTEGER
);

-- Enhanced user preferences
ALTER TABLE users ADD COLUMN survey_preferences JSONB DEFAULT '{}';
-- Example: {"dm_surveys": true, "frequency": "weekly", "opt_out": false}
```

---

## Success Metrics

### Primary KPIs:
- **Response Rate**: Target 80%+ (vs current slash command ~30%)
- **Response Time**: <48 hours average completion
- **User Satisfaction**: Survey experience rating >4.5/5

### Secondary KPIs:
- **Coverage**: 90%+ of team members surveyed monthly
- **Risk Detection**: 95%+ of high-risk individuals identified
- **Follow-up Effectiveness**: 70%+ improved scores after interventions

---

## Risk Mitigation

### User Experience Risks:
- **Survey Fatigue**: Strict frequency limits + smart timing
- **Privacy Concerns**: Clear opt-out + transparent data use
- **Notification Overload**: Respectful delivery windows

### Technical Risks:
- **Slack API Limits**: Rate limiting + retry logic
- **Bot Permissions**: Comprehensive permission requests
- **Delivery Failures**: Fallback to slash command

---

## Migration Strategy

### Parallel Deployment:
1. **Week 1-2**: Deploy DM system alongside existing slash command
2. **Week 3-4**: A/B test with 50% DM, 50% slash command
3. **Week 5-6**: Shift to 80% DM, 20% slash command based on results
4. **Week 7+**: Full DM primary, slash command as backup

### Rollback Plan:
- Keep slash command fully functional
- Feature flag for DM system enable/disable
- Quick switch back to slash-only if needed

---

## User Experience Flow

### DM Survey Experience:
1. **User receives DM** from burnout bot with contextual message
2. **Clicks survey button** → Modal opens with personalized questions
3. **Completes 2-3 minute survey** with adaptive questioning
4. **Receives confirmation** with next steps/resources if needed
5. **Automatic follow-up** scheduled based on risk level

### Manager Experience:
1. **Receives dashboard notifications** for high-risk team members
2. **Can trigger team surveys** for specific events/periods
3. **Gets aggregated insights** without individual details
4. **Accesses support resources** and intervention guides

---

## Privacy & Compliance

### Data Protection:
- Individual survey responses remain confidential
- Only aggregate trends shared with managers
- Full opt-out capability for all users
- GDPR/SOC2 compliant data handling

### Transparency:
- Clear communication about survey purpose
- Regular reminders about data usage
- Easy access to privacy settings
- Option to view/delete personal data

---

This plan transforms the burnout detection system into a **proactive, bot-driven experience** while maintaining the reliability of existing infrastructure.
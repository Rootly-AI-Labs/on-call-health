# Rootly Burnout Detector
## 3-Minute Project Overview

---

### **The Problem** (30 seconds)
- **Developer burnout is a silent epidemic** affecting 83% of software teams
- Traditional surveys are subjective, infrequent, and often ignored
- Teams lack real-time visibility into burnout risk before it's too late
- Current solutions don't integrate with existing development workflows

---

### **Our Solution** (45 seconds)
**AI-powered burnout detection using your existing data sources**

#### **Multi-Platform Analysis:**
- **Primary:** PagerDuty/Rootly incident data (workload, after-hours activity)
- **Enhanced:** GitHub code patterns (commit timing, PR activity)
- **Comprehensive:** Slack communication sentiment analysis

#### **Science-Based Methodology:**
- Built on the **Maslach Burnout Inventory** (clinical gold standard)
- Three key dimensions measured:
  - **Emotional Exhaustion** (40% weight) - workload pressure, after-hours activity
  - **Depersonalization** (30% weight) - response time pressure, weekend disruption
  - **Personal Accomplishment** (30% weight) - resolution success, code quality

---

### **Key Features** (60 seconds)

#### **Real-Time Dashboard**
- Team burnout overview with individual risk assessments
- Historical trends showing burnout progression over time
- Actionable insights with specific risk factors identified

#### **Smart Integrations**
- **One-click OAuth** connections to GitHub, Slack, PagerDuty, Rootly
- **Automated analysis** - no manual data entry required
- **Privacy-first** - only analyzes patterns, not content

#### **Advanced Analytics**
- **Risk categorization:** Low (0-40%), Medium (40-70%), High (70-100%)
- **Trend analysis** showing 30/60/90-day patterns
- **Individual member profiles** with specific burnout factors

#### **User Experience**
- **Skeleton loaders** for smooth performance
- **Intelligent caching** prevents unnecessary API calls
- **Responsive design** works on all devices

---

### **Technical Architecture** (30 seconds)
- **Frontend:** Next.js 14 with TypeScript, Tailwind CSS
- **Backend:** FastAPI with SQLAlchemy, PostgreSQL
- **AI Integration:** Multiple LLM providers for sentiment analysis
- **Deployment:** Docker containerization, cloud-ready
- **Security:** OAuth 2.0, secure token management

---

### **Business Impact** (15 seconds)
- **Prevent costly turnover** - early intervention before burnout peaks
- **Improve team performance** - identify workload imbalances automatically  
- **Data-driven decisions** - objective metrics replace subjective guesswork
- **Zero workflow disruption** - works with tools teams already use

---

### **Demo Ready**
✅ Full OAuth integration with GitHub, Slack, PagerDuty, Rootly  
✅ Real-time burnout analysis with Maslach methodology  
✅ Historical trend tracking and individual risk assessments  
✅ Optimized user experience with caching and skeleton loaders  

**Next Steps:** Schedule team pilot, integrate with your incident management workflow, and start preventing burnout before it impacts your team.
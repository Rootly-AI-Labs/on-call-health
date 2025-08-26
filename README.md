# Rootly Burnout Detector - Web Application

A modern web application for detecting burnout risk in engineering teams using Rootly incident data, GitHub activity, and Slack communication patterns.

## 🎯 Overview

This web application provides an intuitive interface for analyzing team burnout risk using scientific methods based on the Maslach Burnout Inventory. It integrates with Rootly's incident management platform to provide actionable insights for engineering managers.

## ✨ Features

- **🔐 Social Authentication**: Login with Google or GitHub
- **📊 Interactive Dashboard**: Visual burnout risk analysis
- **👥 Team Management**: Individual and team-level insights
- **📈 Real-time Analysis**: Progress tracking during data processing
- **🔄 Analysis History**: Access previous assessments
- **📱 Responsive Design**: Works on desktop and mobile

## 🏗️ Architecture

### Tech Stack
- **Frontend**: React.js + TypeScript (Vercel)
- **Backend**: FastAPI + Python (Railway)
- **Database**: PostgreSQL (Railway)
- **Authentication**: OAuth (Google/GitHub) + JWT

### Project Structure
```
rootly-burnout-detector-web/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── main.py         # FastAPI entry point
│   │   ├── core/           # Business logic & config
│   │   ├── models/         # Database models
│   │   ├── auth/           # Authentication
│   │   └── api/            # API endpoints
│   └── requirements.txt
├── frontend/               # Next.js application  
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- Rootly API token

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration

# Run the server
python -m app.main
```

The API will be available at `http://localhost:8000`

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

## 🔧 Configuration

### Environment Variables
```bash
# Required
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./test.db

# OAuth (optional for development)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Rootly Integration
ROOTLY_API_BASE_URL=https://api.rootly.com
FRONTEND_URL=http://localhost:3000
```

## 🧪 Testing

```bash
cd backend
python -m pytest
```

## 📊 Burnout Analysis

The application uses a **three-factor burnout methodology** with equal weighting:

1. **Personal Burnout** (33.3% weight)
   - Incident frequency and clustering
   - After-hours work patterns
   - Resolution time pressure

2. **Work-Related Burnout** (33.3% weight)
   - Escalation patterns
   - Team collaboration metrics
   - Communication quality

3. **Accomplishment Burnout** (33.4% weight)
   - Resolution success rates
   - Knowledge sharing
   - Improvement trends

### Enhanced Analysis (Optional)
- **GitHub Integration**: Coding stress patterns
- **Slack Integration**: Communication sentiment analysis

## 🚢 Deployment

### Railway (Backend)
1. Connect GitHub repository
2. Set environment variables
3. Deploy automatically

### Vercel (Frontend)
1. Connect GitHub repository
2. Configure build settings
3. Deploy automatically

## 🔐 Security

- OAuth with Google/GitHub (no password storage)
- JWT tokens for session management
- Encrypted API token storage
- HTTPS enforcement
- Input validation and sanitization

## 📝 API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🔗 Related Projects

- [Rootly CLI Burnout Detector](https://github.com/your-org/rootly-burnout-detector) - Command-line version
- [Rootly MCP Server](https://github.com/Rootly-AI-Labs/Rootly-MCP-server) - Model Context Protocol integration

---

Built with ❤️ for engineering teams everywhere.
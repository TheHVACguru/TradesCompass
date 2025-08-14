# TradesCompass Pro 🔨

AI-powered recruitment platform specialized for hiring skilled tradesmen in construction, HVAC, electrical, plumbing, and other trades. Built with Flask and PostgreSQL, featuring intelligent resume analysis and trades-specific candidate matching.

## 🌟 Features

### Core Recruitment Features
- **Multi-Format Resume Processing** - Supports PDF, DOCX, and TXT files
- **AI-Powered Analysis** - Uses OpenAI GPT-4o for intelligent resume parsing
- **Trades-Specific Matching** - Specialized algorithms for construction and trade skills
- **Candidate Database** - Advanced search with filtering by skills, certifications, and location
- **External Candidate Search** - GitHub integration for finding technical professionals

### Trades-Focused Capabilities
- **License & Certification Tracking** - OSHA, EPA, state licenses, union status
- **Safety Compliance Monitoring** - Track safety certifications and training
- **Skill-Based Matching** - Match candidates to specific trade requirements
- **Hourly Rate Management** - Track pay expectations and negotiate rates
- **Tool Ownership Verification** - Document equipment and tool ownership
- **Travel Willingness Tracking** - Monitor geographic flexibility

### Advanced Features
- **Talent Pool Management** - Create and manage candidate pools by trade
- **Email Resume Processing** - Automatic intake from email attachments
- **Job Board Integration** - Search 150,000+ sources via JSearch API
- **Task Management** - Track background checks and verifications
- **Bonus Recommendations** - AI-powered compensation suggestions

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tradescompass-pro.git
cd tradescompass-pro
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Required
export OPENAI_API_KEY="your-openai-api-key"
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
export SESSION_SECRET="your-secret-key"

# Optional - Job Board APIs
export RAPIDAPI_KEY="your-rapidapi-key"  # For JSearch
export GITHUB_TOKEN="your-github-token"  # For candidate search

# Optional - Email Processing
export EMAIL_USER="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export IMAP_SERVER="imap.gmail.com"
export IMAP_PORT="993"
```

4. Initialize the database:
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

5. Run the application:
```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

## 📊 Database Schema

### Key Models
- **ResumeAnalysis** - Stores parsed resume data with trades-specific fields
- **CandidateSkill** - Tracks trade skills (electrical, plumbing, HVAC, etc.)
- **CandidateTag** - Custom tags for specializations and certifications
- **TalentPool** - Manages candidate pools by trade and criteria
- **RecruiterTask** - Tracks verification and compliance tasks

## 🔍 Search Capabilities

### Internal Database Search
- Filter by trade skills (HVAC, electrical, plumbing, carpentry)
- Search by certifications (OSHA 10/30, EPA, NATE, state licenses)
- Location-based filtering with radius search
- Experience level and hourly rate filtering

### External Search (GitHub)
- Find technical professionals and engineers
- Search for automation and IoT specialists
- Locate developers with trade-related projects

## 📋 Supported Trade Categories

- **HVAC** - Installation, repair, maintenance, ductwork
- **Electrical** - Residential, commercial, industrial wiring
- **Plumbing** - Pipe fitting, fixtures, water systems
- **Windows/Doors** - Impact windows, hurricane shutters
- **Construction** - Framing, concrete, masonry, roofing
- **Specialized** - Solar, smart home, building automation

## 🛠️ API Integrations

### Job Boards
- **JSearch API** - Access to 150,000+ job sources
- **ZipRecruiter** - Direct job search (fallback)
- **Indeed Publisher** - Job listings (fallback)
- **USAJobs** - Federal opportunities

### AI & Analysis
- **OpenAI GPT-4o** - Resume parsing and analysis
- **GitHub API** - Developer profile search

## 🔐 Security Features

- SQL injection protection via SQLAlchemy ORM
- XSS prevention with proper template escaping
- CSRF protection with Flask sessions
- Secure password hashing
- Environment-based configuration
- Input validation for NaN/Inf values

## 📱 User Interface

- Dark theme optimized for extended use
- Mobile-responsive design
- Advanced filtering and search
- Pagination for large result sets
- Real-time search suggestions
- Interactive candidate cards

## 🧪 Testing

Run tests with:
```bash
python -m pytest tests/
```

## 📝 License

This project is proprietary software. All rights reserved.

## 🤝 Contributing

Please contact the repository owner for contribution guidelines.

## 📞 Support

For support, please open an issue in the GitHub repository.

## 🏗️ Built With

- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **AI**: OpenAI GPT-4o
- **Frontend**: Bootstrap 5, Jinja2
- **File Processing**: PyPDF2, python-docx
- **Deployment**: Gunicorn, Replit

## 🎯 Roadmap

- [ ] Mobile application
- [ ] Advanced analytics dashboard
- [ ] Automated interview scheduling
- [ ] Background check integration
- [ ] Multi-language support
- [ ] SMS notifications
- [ ] Contractor marketplace

## 👥 Target Users

- General contractors
- Subcontractors
- Construction companies
- HVAC companies
- Electrical contractors
- Plumbing services
- Property management firms
- Facilities management
- Trade unions
- Staffing agencies

---

**TradesCompass Pro** - Revolutionizing trades recruitment with AI-powered intelligence.
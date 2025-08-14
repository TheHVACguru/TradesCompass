# Overview

TradesCompass Pro - A specialized Flask-based AI-powered recruitment platform designed specifically for hiring skilled tradesmen in construction, HVAC, electrical, plumbing, window/door installation, hurricane shutters, and other trades. The system provides comprehensive trades-focused features including license/certification verification, safety compliance tracking, union status management, and skill-based matching. Key capabilities include multi-channel resume intake, trades-specific AI analysis, job matching through JSearch API (150,000+ sources), OSHA/EPA certification tracking, hourly rate management, tool ownership verification, travel willingness tracking, and Scout - an AI assistant with self-learning capabilities. Scout can now search external sources (LinkedIn, Indeed, GitHub, trade boards), learn from user interactions, optimize database performance, and continuously improve through feedback. The platform helps contractors and construction companies efficiently source, evaluate, and hire qualified tradesmen while ensuring compliance and safety standards through intelligent guidance and personalized recruiting assistance.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM and PostgreSQL database
- **Database**: PostgreSQL with advanced indexing for candidate search, email processing logs, and relationship management
- **File Processing**: Multi-format support (PDF, DOCX, TXT) with enhanced text extraction and error handling
- **AI Integration**: OpenAI GPT-4o with structured JSON responses for resume analysis and candidate information extraction
- **Multi-Source Job Matching**: Primary integration with JSearch API (Google for Jobs + 150,000+ sources) plus fallback APIs for ZipRecruiter, Indeed Publisher, and USAJobs
- **Email Automation**: IMAP-based email processing for automatic resume intake from email attachments

## Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap dark theme and enhanced UI components
- **Navigation**: Multi-page application with Dashboard, Candidate Database, Email Processing, and Analysis views
- **Interactive Features**: Advanced search filters, candidate tagging system, status management, and pagination
- **Responsive Design**: Mobile-friendly interface with progressive enhancement

## Enhanced Data Model
- **ResumeAnalysis**: Extended model with trades-specific fields including licenses, certifications, union status, years of experience, hourly rate expectations, tool ownership, and travel willingness
- **CandidateSkill**: Trades skill tracking for electrical, plumbing, HVAC, carpentry, masonry, and other construction skills
- **CandidateTag**: Custom tagging for trade specializations, safety certifications, and project types
- **EmailProcessingLog**: Automated resume intake from contractors and staffing agencies
- **RecruiterTask**: Task management for background checks, license verification, and safety training scheduling
- **Database Optimization**: Indexes optimized for license searches, certification queries, and location-based matching

## Advanced Service Layer
- **Trades Job Board Integration**: JSearch API configured for construction and trades positions across 150,000+ sources with focus on Indeed, ZipRecruiter, and specialized trade job boards
- **Trades Candidate Services**: License verification, certification tracking, safety compliance scoring, and union affiliation management
- **Contractor Email Processing**: Automated processing of resumes from general contractors, subcontractors, and trade unions
- **Trades-Focused AI**: Specialized analysis for trade certifications (OSHA, EPA), state licenses, years of hands-on experience, and safety record evaluation

## Self-Learning Capabilities (Added 2025-08-14)
- **Learning Engine**: Tracks user interactions, search patterns, and successful placements to continuously improve
- **Query Optimization**: AI-powered query improvements based on historical success patterns
- **Database Optimization**: Automatic analysis of database usage patterns and performance optimization suggestions
- **Skill Association Learning**: Identifies which skills commonly appear together in successful hires
- **User Preference Learning**: Adapts to user preferences based on feedback and behavior patterns
- **Insights Reporting**: Generates comprehensive reports on learned patterns and optimization opportunities

## Security & Configuration
- **Database Security**: PostgreSQL with connection pooling and environment-based configuration
- **Email Security**: App-specific password support with secure IMAP connections
- **API Management**: Multiple API key support with graceful degradation and error handling
- **Session Security**: Enhanced session management with configurable secret keys

# External Dependencies

## APIs & Services
- **OpenAI API**: GPT-4o model for resume analysis and enhanced candidate information extraction
- **xAI API (Grok-2)**: Enhanced intelligent candidate search with natural language understanding and AI-powered ranking (Added 2025-08-14)
- **JSearch API (RapidAPI)**: Primary job aggregator accessing Google for Jobs and 150,000+ sources including LinkedIn, Indeed, Glassdoor, ZipRecruiter, Monster with comprehensive job data
- **ZipRecruiter API**: Direct job search API (fallback when JSearch unavailable)
- **Indeed Publisher API**: Direct Indeed database access (fallback when JSearch unavailable)
- **USAJobs API**: Federal job opportunities with government position details (supplementary)
- **Email Services**: IMAP integration for Gmail, Outlook, Yahoo, and other providers

## Enhanced Candidate Sourcing APIs (Updated 2025-08-14)
- **GitHub API**: Active - searches public developer profiles and repositories for technical trades
- **LinkedIn Profiles API (RapidAPI)**: Active - searches LinkedIn professional profiles with detailed experience data
- **Indeed Resumes API (RapidAPI)**: Active - searches Indeed's resume database for trade professionals
- **Trade Job Boards (RapidAPI)**: Active - aggregates from specialized construction and trades job boards
- **PeopleDataLabs API**: Professional profiles with contact info, work history, and skills (requires API key)
- **SeekOut API**: Active job seekers with diversity data and availability status (requires API key)
- **SourceHub API**: Candidate profiles with salary expectations and immediate availability (requires API key)

## Enhanced Third-Party Libraries  
- **Flask Ecosystem**: Flask, Flask-SQLAlchemy with PostgreSQL adapter (psycopg2-binary)
- **File Processing**: PyPDF2 (PDFs), python-docx (Word), enhanced text encoding handling
- **Email Processing**: Built-in Python email and imaplib libraries for attachment processing
- **HTTP Client**: Requests with timeout handling and retry logic for API reliability
- **Frontend**: Bootstrap 5 dark theme, Font Awesome icons, enhanced JavaScript interactions
- **AI Models**: OpenAI GPT-4o (primary), xAI Grok-2 (enhanced search and ranking)

## Database Infrastructure
- **Production**: PostgreSQL with advanced indexing and relationship management
- **Connection Management**: SQLAlchemy with connection pooling, health checks, and optimized queries
- **Data Integrity**: Foreign key constraints, unique constraints, and comprehensive indexes
- **Performance**: Strategic indexes on search fields, ratings, and temporal data

## Environment Configuration
- **Required**: OPENAI_API_KEY for AI-powered analysis
- **Job Boards**: RAPIDAPI_KEY (for JSearch - primary job aggregator), ZIPRECRUITER_API_KEY, INDEED_PUBLISHER_ID, USAJOBS_API_KEY, USAJOBS_USER_AGENT (all optional fallbacks)
- **Email Processing**: EMAIL_USER, EMAIL_PASSWORD, IMAP_SERVER, IMAP_PORT for automated resume intake
- **Database**: DATABASE_URL (automatically configured), SESSION_SECRET for secure sessions
- **Optional**: Email folder configuration and processing parameters
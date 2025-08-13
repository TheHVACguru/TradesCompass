# Overview

TalentCompass AI - A comprehensive Flask-based AI-powered recruitment platform that revolutionizes talent acquisition and management. The system provides multi-channel resume intake (manual upload + email automation), advanced smart search capabilities with fuzzy matching and AI semantic search, comprehensive analytics dashboards, task management, AI-powered candidate recommendations, and job matching through JSearch API (aggregating from 150,000+ sources). Features include candidate tagging, status tracking, referral management, talent pools, performance metrics, and a unified recruitment command center.

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
- **ResumeAnalysis**: Extended model with phone, location, source tracking, status management, and recruiter notes
- **CandidateSkill**: Dedicated skill tracking with proficiency levels and experience years
- **CandidateTag**: Custom tagging system with color coding for candidate organization  
- **EmailProcessingLog**: Comprehensive email automation tracking with error logging and processing statistics
- **Database Optimization**: Strategic indexes on ratings, skills, dates, and search fields for performance

## Advanced Service Layer
- **Multi-Job Board Integration**: Primary JSearch API aggregation (150,000+ sources including LinkedIn, Indeed, Glassdoor, ZipRecruiter, Monster) with intelligent fallback to individual APIs
- **Candidate Database Services**: Advanced search, similarity matching, and statistical analysis
- **Email Processing Engine**: IMAP integration with attachment extraction, job description parsing, and automated analysis
- **Enhanced AI Services**: Improved candidate information extraction including phone, location, and skills with better error handling

## Security & Configuration
- **Database Security**: PostgreSQL with connection pooling and environment-based configuration
- **Email Security**: App-specific password support with secure IMAP connections
- **API Management**: Multiple API key support with graceful degradation and error handling
- **Session Security**: Enhanced session management with configurable secret keys

# External Dependencies

## APIs & Services
- **OpenAI API**: GPT-4o model for resume analysis and enhanced candidate information extraction
- **JSearch API (RapidAPI)**: Primary job aggregator accessing Google for Jobs and 150,000+ sources including LinkedIn, Indeed, Glassdoor, ZipRecruiter, Monster with comprehensive job data
- **ZipRecruiter API**: Direct job search API (fallback when JSearch unavailable)
- **Indeed Publisher API**: Direct Indeed database access (fallback when JSearch unavailable)
- **USAJobs API**: Federal job opportunities with government position details (supplementary)
- **Email Services**: IMAP integration for Gmail, Outlook, Yahoo, and other providers

## Enhanced Third-Party Libraries  
- **Flask Ecosystem**: Flask, Flask-SQLAlchemy with PostgreSQL adapter (psycopg2-binary)
- **File Processing**: PyPDF2 (PDFs), python-docx (Word), enhanced text encoding handling
- **Email Processing**: Built-in Python email and imaplib libraries for attachment processing
- **HTTP Client**: Requests with timeout handling and retry logic for API reliability
- **Frontend**: Bootstrap 5 dark theme, Font Awesome icons, enhanced JavaScript interactions

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
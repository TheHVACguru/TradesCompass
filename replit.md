# Overview

A comprehensive Flask-based AI-powered recruitment platform that revolutionizes candidate screening and management. The system provides multi-channel resume intake (manual upload + email automation), advanced candidate database search, AI-powered analysis using OpenAI GPT-4o, and multi-source job matching across ZipRecruiter, Indeed, and USAJobs platforms. Features include candidate tagging, status tracking, email processing automation, and a comprehensive recruitment dashboard.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM and PostgreSQL database
- **Database**: PostgreSQL with advanced indexing for candidate search, email processing logs, and relationship management
- **File Processing**: Multi-format support (PDF, DOCX, TXT) with enhanced text extraction and error handling
- **AI Integration**: OpenAI GPT-4o with structured JSON responses for resume analysis and candidate information extraction
- **Multi-Source Job Matching**: Integrated APIs for ZipRecruiter, Indeed Publisher, and USAJobs federal positions
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
- **Multi-Job Board Integration**: Aggregated search across ZipRecruiter, Indeed, and USAJobs with deduplication
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
- **ZipRecruiter API**: Job search with comprehensive job details and company information
- **Indeed Publisher API**: Access to Indeed's job database with location-based search
- **USAJobs API**: Federal job opportunities with government position details
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
- **Job Boards**: ZIPRECRUITER_API_KEY, INDEED_PUBLISHER_ID, USAJOBS_API_KEY, USAJOBS_USER_AGENT
- **Email Processing**: EMAIL_USER, EMAIL_PASSWORD, IMAP_SERVER, IMAP_PORT for automated resume intake
- **Database**: DATABASE_URL (automatically configured), SESSION_SECRET for secure sessions
- **Optional**: Email folder configuration and processing parameters
# Overview

A Flask-based AI-powered resume screening application that analyzes candidate resumes against job descriptions. The system extracts text from uploaded resume files, uses OpenAI's GPT-4 to provide detailed candidate analysis including strengths, weaknesses, risk/reward assessments, and integrates with ZipRecruiter API to find relevant job matches.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM for database operations
- **Database**: SQLite for local development with configurable PostgreSQL support via DATABASE_URL environment variable
- **File Processing**: Supports PDF, DOCX, and TXT resume formats with dedicated text extraction services
- **AI Integration**: OpenAI GPT-4o integration for resume analysis using structured prompts and JSON responses
- **External API**: ZipRecruiter API integration for job matching and recommendations

## Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap dark theme for responsive UI
- **Styling**: Bootstrap 5 with custom CSS for enhanced user experience
- **JavaScript**: Vanilla JavaScript for form validation, file upload handling, and loading states
- **File Uploads**: 16MB file size limit with client-side validation for supported formats

## Data Model
- **ResumeAnalysis Model**: Central entity storing uploaded resume metadata, extracted candidate information (name, email), full resume text, AI analysis results (strengths, weaknesses, risk/reward scores), and relevant job matches
- **Database Schema**: Uses SQLAlchemy with Text fields for JSON storage of complex analysis data

## Service Layer Architecture
- **Text Extraction Service**: Modular approach with format-specific extractors (PyPDF2 for PDFs, python-docx for Word documents, plain text handling with encoding fallbacks)
- **AI Analysis Service**: Structured prompting system that analyzes resumes against job descriptions, returning standardized JSON responses with candidate assessment metrics
- **Job Matching Service**: ZipRecruiter API integration with configurable search parameters and error handling

## Authentication & Security
- **Session Management**: Flask sessions with configurable secret key
- **File Security**: Werkzeug secure filename handling and restricted file type validation
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies

# External Dependencies

## APIs & Services
- **OpenAI API**: GPT-4o model for resume analysis and candidate assessment
- **ZipRecruiter API**: Job search and matching functionality

## Third-Party Libraries
- **Flask Ecosystem**: Flask, Flask-SQLAlchemy for web framework and ORM
- **File Processing**: PyPDF2 for PDF text extraction, python-docx for Word document processing
- **HTTP Client**: Requests library for external API communication
- **Frontend**: Bootstrap 5 with dark theme, Font Awesome for icons

## Database
- **Development**: SQLite with local file storage
- **Production**: Configurable PostgreSQL via DATABASE_URL environment variable
- **Connection Management**: SQLAlchemy with connection pooling and health checks

## Environment Configuration
- **Required**: OPENAI_API_KEY for AI analysis functionality
- **Optional**: ZIPRECRUITER_API_KEY for job matching, DATABASE_URL for PostgreSQL, SESSION_SECRET for production security
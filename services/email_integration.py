import os
import email
import imaplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime

from app import db
from models import ResumeAnalysis, EmailProcessingLog
from services.text_extraction import extract_text_from_file
from services.ai_analysis import analyze_resume, extract_candidate_info
from services.job_boards import search_relevant_jobs

class EmailResumeProcessor:
    """Process resumes from email attachments"""
    
    def __init__(self):
        self.imap_server = os.environ.get("IMAP_SERVER", "imap.gmail.com")
        self.imap_port = int(os.environ.get("IMAP_PORT", "993"))
        self.email_user = os.environ.get("EMAIL_USER")
        self.email_password = os.environ.get("EMAIL_PASSWORD")
        self.processed_folder = os.environ.get("EMAIL_PROCESSED_FOLDER", "Processed")
        
    def connect_to_email(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to email server"""
        if not self.email_user or not self.email_password:
            logging.warning("Email credentials not configured")
            return None
            
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_user, self.email_password)
            return mail
        except Exception as e:
            logging.error(f"Failed to connect to email: {str(e)}")
            return None
    
    def process_new_emails(self, folder: str = "INBOX", job_description: str = None) -> Dict[str, Any]:
        """
        Process new emails with resume attachments
        
        Args:
            folder: Email folder to check
            job_description: Default job description for analysis
            
        Returns:
            Dictionary with processing results
        """
        mail = self.connect_to_email()
        if not mail:
            return {"error": "Could not connect to email"}
        
        results = {
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "candidates": []
        }
        
        try:
            mail.select(folder)
            
            # Search for unread emails with attachments
            _, message_ids = mail.search(None, 'UNSEEN')
            
            for message_id in message_ids[0].split():
                try:
                    result = self._process_email_message(mail, message_id, job_description)
                    
                    if result["status"] == "processed":
                        results["processed"] += 1
                        if result.get("candidate"):
                            results["candidates"].append(result["candidate"])
                    elif result["status"] == "failed":
                        results["failed"] += 1
                    else:
                        results["skipped"] += 1
                        
                except Exception as e:
                    logging.error(f"Error processing email {message_id}: {str(e)}")
                    results["failed"] += 1
                    
        except Exception as e:
            logging.error(f"Error processing emails: {str(e)}")
            results["error"] = str(e)
        finally:
            mail.close()
            mail.logout()
        
        return results
    
    def _process_email_message(self, mail: imaplib.IMAP4_SSL, message_id: bytes, job_description: str = None) -> Dict[str, Any]:
        """Process a single email message"""
        
        _, msg_data = mail.fetch(message_id, '(RFC822)')
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        # Extract email metadata
        sender = email_message['From']
        subject = email_message['Subject'] or 'No Subject'
        email_id = email_message['Message-ID']
        
        # Check if already processed
        if EmailProcessingLog.query.filter_by(email_id=email_id).first():
            return {"status": "skipped", "reason": "already_processed"}
        
        # Look for resume attachments
        resume_attachments = self._extract_resume_attachments(email_message)
        
        if not resume_attachments:
            # Log as skipped
            log_entry = EmailProcessingLog(
                email_id=email_id,
                sender_email=sender,
                subject=subject,
                status='skipped',
                error_message='No resume attachments found'
            )
            db.session.add(log_entry)
            db.session.commit()
            return {"status": "skipped", "reason": "no_attachments"}
        
        # Process the first resume attachment
        attachment = resume_attachments[0]
        
        try:
            # Save attachment temporarily
            with tempfile.NamedTemporaryFile(suffix=f".{attachment['extension']}", delete=False) as temp_file:
                temp_file.write(attachment['content'])
                temp_filepath = temp_file.name
            
            # Extract text from resume
            resume_text = extract_text_from_file(temp_filepath)
            
            if not resume_text.strip():
                raise Exception("Could not extract text from resume")
            
            # Extract candidate information
            candidate_info = extract_candidate_info(resume_text)
            
            # Use provided job description or extract from email
            analysis_job_description = job_description or self._extract_job_description_from_email(email_message)
            
            # Analyze resume if job description available
            analysis_result = None
            if analysis_job_description:
                analysis_result = analyze_resume(resume_text, analysis_job_description)
            
            # Search for relevant jobs
            relevant_jobs = []
            if candidate_info.get('extracted_skills'):
                skills_query = ' '.join(candidate_info.get('extracted_skills', [])[:3])
                relevant_jobs = search_relevant_jobs(skills_query)
            
            # Save to database
            resume_analysis = ResumeAnalysis(
                filename=attachment['filename'],
                first_name=candidate_info.get('first_name'),
                last_name=candidate_info.get('last_name'),
                email=candidate_info.get('email') or sender,
                resume_text=resume_text,
                source='email',
                candidate_strengths=json.dumps(analysis_result.get('candidate_strengths', [])) if analysis_result else None,
                candidate_weaknesses=json.dumps(analysis_result.get('candidate_weaknesses', [])) if analysis_result else None,
                risk_factor_score=analysis_result.get('risk_factor', {}).get('score') if analysis_result else None,
                risk_factor_explanation=analysis_result.get('risk_factor', {}).get('explanation') if analysis_result else None,
                reward_factor_score=analysis_result.get('reward_factor', {}).get('score') if analysis_result else None,
                reward_factor_explanation=analysis_result.get('reward_factor', {}).get('explanation') if analysis_result else None,
                overall_fit_rating=analysis_result.get('overall_fit_rating') if analysis_result else None,
                justification=analysis_result.get('justification_for_rating') if analysis_result else None,
                relevant_jobs=json.dumps(relevant_jobs)
            )
            
            db.session.add(resume_analysis)
            db.session.flush()  # Get the ID
            
            # Log successful processing
            log_entry = EmailProcessingLog(
                email_id=email_id,
                sender_email=sender,
                subject=subject,
                status='processed',
                resume_analysis_id=resume_analysis.id
            )
            db.session.add(log_entry)
            db.session.commit()
            
            # Clean up temp file
            os.unlink(temp_filepath)
            
            # Mark email as read and optionally move to processed folder
            mail.store(message_id, '+FLAGS', '\\Seen')
            
            return {
                "status": "processed",
                "candidate": resume_analysis.to_dict()
            }
            
        except Exception as e:
            # Log failed processing
            log_entry = EmailProcessingLog(
                email_id=email_id,
                sender_email=sender,
                subject=subject,
                status='failed',
                error_message=str(e)
            )
            db.session.add(log_entry)
            db.session.commit()
            
            # Clean up temp file if it exists
            if 'temp_filepath' in locals():
                try:
                    os.unlink(temp_filepath)
                except:
                    pass
                    
            return {"status": "failed", "error": str(e)}
    
    def _extract_resume_attachments(self, email_message) -> List[Dict[str, Any]]:
        """Extract resume attachments from email"""
        resume_attachments = []
        resume_extensions = ['pdf', 'docx', 'doc', 'txt']
        
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
                
            if part.get('Content-Disposition') is None:
                continue
                
            filename = part.get_filename()
            if not filename:
                continue
                
            # Check if it's a resume file
            extension = filename.lower().split('.')[-1]
            if extension in resume_extensions:
                content = part.get_payload(decode=True)
                if content:
                    resume_attachments.append({
                        'filename': filename,
                        'extension': extension,
                        'content': content
                    })
        
        return resume_attachments
    
    def _extract_job_description_from_email(self, email_message) -> Optional[str]:
        """Try to extract job description from email body"""
        try:
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8')
                        break
            else:
                body = email_message.get_payload(decode=True).decode('utf-8')
            
            # Look for job description keywords
            job_keywords = ['job description', 'position', 'requirements', 'qualifications', 'responsibilities']
            
            if any(keyword in body.lower() for keyword in job_keywords) and len(body) > 100:
                return body.strip()
                
        except Exception as e:
            logging.error(f"Error extracting job description from email: {str(e)}")
            
        return None

def send_candidate_notification(candidate_email: str, recruiter_name: str, message: str) -> bool:
    """Send notification email to candidate"""
    
    # This would require email sending configuration (SMTP)
    # For now, just log the notification
    logging.info(f"Would send notification to {candidate_email}: {message}")
    return True

import json  # Add this import at the top
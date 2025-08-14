import json
import os
import logging
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def analyze_resume(resume_text, job_description):
    """Analyze resume against job description using OpenAI"""
    try:
        system_prompt = """# Overview
You are an expert trades and construction recruiter specializing in skilled tradesmen including electricians, plumbers, HVAC technicians, carpenters, masons, roofers, window/door installers, and other construction professionals. You have been given a job description and a candidate resume. Your task is to analyze the resume in relation to the job description and provide a detailed screening report.

Focus specifically on how well the candidate matches the core requirements including: certifications/licenses, hands-on experience, safety compliance, technical skills, and reliability. Evaluate both technical competency and work ethic/professionalism.

# Analysis Framework
- **Candidate Strengths**: Specific qualifications, skills, and experiences that directly match or exceed job requirements
- **Candidate Weaknesses**: Areas where the candidate falls short of requirements or has potential gaps
- **Risk Factor**: Assessment of potential hiring risks (1-10 scale, 1=low risk, 10=high risk)
- **Reward Factor**: Assessment of potential value/upside (1-10 scale, 1=low reward, 10=high reward)
- **Overall Fit Rating**: Holistic assessment (1-10 scale, 1=poor fit, 10=excellent fit)

Respond with JSON in this exact format:
{
  "candidate_strengths": ["strength1", "strength2", "strength3"],
  "candidate_weaknesses": ["weakness1", "weakness2", "weakness3"],
  "risk_factor": {
    "score": 5,
    "explanation": "Detailed explanation of risk assessment"
  },
  "reward_factor": {
    "score": 7,
    "explanation": "Detailed explanation of reward potential"
  },
  "overall_fit_rating": 6,
  "justification_for_rating": "Comprehensive justification for the overall rating"
}"""

        user_prompt = f"""Job Description:
{job_description}

Candidate Resume:
{resume_text}

Please analyze this candidate's resume against the job description and provide a detailed screening report."""

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        if content:
            result = json.loads(content)
            return result
        else:
            raise Exception("Empty response from OpenAI")
        
    except Exception as e:
        logging.error(f"Error analyzing resume: {str(e)}")
        raise Exception(f"Failed to analyze resume: {str(e)}")

def extract_candidate_info(resume_text):
    """Extract candidate contact information from resume"""
    try:
        system_prompt = """You are an expert at extracting contact information from skilled trades and construction resumes. Extract the candidate's first name, last name, email address, phone number, location, and key trade skills from the resume text.

Also identify the top 5 most relevant trade skills, certifications, and licenses mentioned in the resume. Look specifically for: OSHA certifications, state licenses (electrical, plumbing, HVAC, contractor), EPA certifications, union affiliations, and specific trade skills.

Respond with JSON in this exact format:
{
  "first_name": "John",
  "last_name": "Doe", 
  "email": "john.doe@email.com",
  "phone": "+1-555-123-4567",
  "location": "San Francisco, CA",
  "extracted_skills": ["Python", "Machine Learning", "AWS", "React", "SQL"]
}

If any information is not found, use null for that field."""

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Resume text:\n{resume_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        if content:
            result = json.loads(content)
            return result
        else:
            raise Exception("Empty response from OpenAI")
        
    except Exception as e:
        logging.error(f"Error extracting candidate info: {str(e)}")
        return {
            "first_name": None,
            "last_name": None,
            "email": None,
            "phone": None,
            "location": None,
            "extracted_skills": []
        }

import os
import logging
import requests
from urllib.parse import urlencode

ZIPRECRUITER_API_KEY = os.environ.get("ZIPRECRUITER_API_KEY")

def search_relevant_jobs(search_query, location="United States", max_results=5):
    """Search for relevant jobs using ZipRecruiter API"""
    if not ZIPRECRUITER_API_KEY:
        logging.warning("ZipRecruiter API key not found")
        return []
    
    try:
        # ZipRecruiter API endpoint
        base_url = "https://api.ziprecruiter.com/jobs/v1"
        
        params = {
            'search': search_query,
            'location': location,
            'radius_miles': 50,
            'days_ago': 30,
            'jobs_per_page': max_results,
            'page': 1,
            'api_key': ZIPRECRUITER_API_KEY
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        jobs = []
        
        if 'jobs' in data:
            for job in data['jobs']:
                job_info = {
                    'title': job.get('name', 'N/A'),
                    'company': job.get('hiring_company', {}).get('name', 'N/A'),
                    'location': job.get('location', 'N/A'),
                    'url': job.get('url', '#'),
                    'summary': job.get('snippet', 'No description available'),
                    'posted_date': job.get('posted_time_friendly', 'N/A'),
                    'salary': job.get('salary_interval', {}).get('formatted_salary', 'Not specified')
                }
                jobs.append(job_info)
        
        return jobs
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching jobs from ZipRecruiter: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in job search: {str(e)}")
        return []

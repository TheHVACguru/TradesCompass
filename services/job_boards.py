import os
import json
import logging
import requests
from typing import List, Dict, Any
from urllib.parse import urlencode
import time

class JobBoardAPI:
    """Base class for job board integrations"""
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for jobs - to be implemented by subclasses"""
        raise NotImplementedError

class ZipRecruiterAPI(JobBoardAPI):
    """ZipRecruiter job search integration"""
    
    def __init__(self):
        super().__init__(os.environ.get("ZIPRECRUITER_API_KEY"))
        self.base_url = "https://api.ziprecruiter.com/jobs/v1"
    
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logging.warning("ZipRecruiter API key not found")
            return []
        
        try:
            params = {
                'search': query,
                'location': location,
                'radius_miles': 50,
                'days_ago': 30,
                'jobs_per_page': max_results,
                'page': 1,
                'api_key': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
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
                        'salary': job.get('salary_interval', {}).get('formatted_salary', 'Not specified'),
                        'source': 'ZipRecruiter'
                    }
                    jobs.append(job_info)
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching jobs from ZipRecruiter: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in ZipRecruiter search: {str(e)}")
            return []

class IndeedAPI(JobBoardAPI):
    """Indeed job search integration using their publisher API"""
    
    def __init__(self):
        super().__init__(os.environ.get("INDEED_PUBLISHER_ID"))
        self.base_url = "http://api.indeed.com/ads/apisearch"
    
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logging.info("Indeed Publisher ID not found, skipping Indeed search")
            return []
        
        try:
            params = {
                'publisher': self.api_key,
                'q': query,
                'l': location,
                'sort': 'date',
                'radius': 50,
                'st': 'jobsite',
                'jt': 'fulltime',
                'start': 0,
                'limit': max_results,
                'fromage': 30,
                'format': 'json',
                'v': '2'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            if 'results' in data:
                for job in data['results']:
                    job_info = {
                        'title': job.get('jobtitle', 'N/A'),
                        'company': job.get('company', 'N/A'),
                        'location': f"{job.get('city', '')}, {job.get('state', '')}".strip(', '),
                        'url': job.get('url', '#'),
                        'summary': job.get('snippet', 'No description available'),
                        'posted_date': job.get('formattedRelativeTime', 'N/A'),
                        'salary': job.get('salary', 'Not specified'),
                        'source': 'Indeed'
                    }
                    jobs.append(job_info)
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching jobs from Indeed: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in Indeed search: {str(e)}")
            return []

class USAJobsAPI(JobBoardAPI):
    """USAJobs.gov federal job search integration"""
    
    def __init__(self):
        super().__init__(os.environ.get("USAJOBS_API_KEY"))
        self.base_url = "https://data.usajobs.gov/api/search"
        self.user_agent = os.environ.get("USAJOBS_USER_AGENT", "resume-scanner@example.com")
    
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        try:
            headers = {
                'Host': 'data.usajobs.gov',
                'User-Agent': self.user_agent,
            }
            
            if self.api_key:
                headers['Authorization-Key'] = self.api_key
            
            params = {
                'Keyword': query,
                'LocationName': location,
                'ResultsPerPage': max_results,
                'Page': 1
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            if 'SearchResult' in data and 'SearchResultItems' in data['SearchResult']:
                for item in data['SearchResult']['SearchResultItems']:
                    job = item.get('MatchedObjectDescriptor', {})
                    job_info = {
                        'title': job.get('PositionTitle', 'N/A'),
                        'company': job.get('OrganizationName', 'U.S. Government'),
                        'location': ', '.join(job.get('PositionLocationDisplay', [])),
                        'url': job.get('PositionURI', '#'),
                        'summary': job.get('QualificationSummary', 'Federal position'),
                        'posted_date': job.get('PublicationStartDate', 'N/A'),
                        'salary': f"{job.get('PositionRemuneration', [{}])[0].get('MinimumRange', 'Not specified')} - {job.get('PositionRemuneration', [{}])[0].get('MaximumRange', '')}",
                        'source': 'USAJobs'
                    }
                    jobs.append(job_info)
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching jobs from USAJobs: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in USAJobs search: {str(e)}")
            return []

class MultiJobBoardSearch:
    """Aggregates job searches across multiple job boards"""
    
    def __init__(self):
        self.job_boards = [
            ZipRecruiterAPI(),
            IndeedAPI(),
            USAJobsAPI()
        ]
    
    def search_all_jobs(self, query: str, location: str = "United States", max_per_board: int = 3) -> List[Dict[str, Any]]:
        """Search jobs across all available job boards"""
        all_jobs = []
        
        for board in self.job_boards:
            try:
                jobs = board.search_jobs(query, location, max_per_board)
                all_jobs.extend(jobs)
                # Small delay to be respectful to APIs
                time.sleep(0.5)
            except Exception as e:
                logging.error(f"Error searching {board.__class__.__name__}: {str(e)}")
                continue
        
        # Remove duplicates based on title and company
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = (job['title'].lower(), job['company'].lower())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        return unique_jobs[:15]  # Limit total results

# Convenience function for backward compatibility
def search_relevant_jobs(search_query, location="United States", max_results=5):
    """Search for relevant jobs using multiple job boards"""
    searcher = MultiJobBoardSearch()
    return searcher.search_all_jobs(search_query, location, max_results // 3)
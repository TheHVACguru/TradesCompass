import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from app import db
from models import ResumeAnalysis

class SalesforceIntegration:
    """Salesforce CRM integration for candidate management"""
    
    def __init__(self):
        self.sf_username = os.environ.get("SALESFORCE_USERNAME")
        self.sf_password = os.environ.get("SALESFORCE_PASSWORD")
        self.sf_security_token = os.environ.get("SALESFORCE_SECURITY_TOKEN")
        self.sf_domain = os.environ.get("SALESFORCE_DOMAIN", "login")  # 'login' for production, 'test' for sandbox
        self.sf_client_id = os.environ.get("SALESFORCE_CLIENT_ID")
        self.sf_client_secret = os.environ.get("SALESFORCE_CLIENT_SECRET")
        self.sf = None
        self._connect()
    
    def _connect(self) -> bool:
        """Establish connection to Salesforce"""
        if not all([self.sf_username, self.sf_password, self.sf_security_token]):
            logging.warning("Salesforce credentials not fully configured")
            return False
        
        try:
            self.sf = Salesforce(
                username=self.sf_username,
                password=self.sf_password,
                security_token=self.sf_security_token,
                domain=self.sf_domain
            )
            logging.info("Successfully connected to Salesforce")
            return True
        except SalesforceAuthenticationFailed as e:
            logging.error(f"Salesforce authentication failed: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Error connecting to Salesforce: {str(e)}")
            return False
    
    def create_lead_from_candidate(self, candidate: ResumeAnalysis) -> Dict[str, Any]:
        """Create a Salesforce Lead from a candidate"""
        if not self.sf:
            return {"success": False, "error": "Not connected to Salesforce"}
        
        try:
            # Prepare lead data
            lead_data = {
                'FirstName': candidate.first_name or 'Unknown',
                'LastName': candidate.last_name or 'Candidate',
                'Email': candidate.email,
                'Phone': candidate.phone,
                'Company': 'Candidate Pool',  # Required field
                'LeadSource': 'Resume Submission',
                'Status': 'Open - Not Contacted',
                'Description': self._create_candidate_description(candidate),
                'Rating': self._convert_rating_to_sf_rating(candidate.overall_fit_rating)
            }
            
            # Add location if available
            if candidate.location:
                parts = candidate.location.split(',')
                if len(parts) >= 2:
                    lead_data['City'] = parts[0].strip()
                    lead_data['State'] = parts[1].strip()
            
            # Create the lead
            result = self.sf.Lead.create(lead_data)
            
            if result['success']:
                # Store Salesforce ID in database
                candidate.notes = f"{candidate.notes or ''}\nSalesforce Lead ID: {result['id']}"
                db.session.commit()
                
                return {
                    "success": True,
                    "id": result['id'],
                    "message": f"Lead created successfully in Salesforce"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create lead: {result.get('errors', 'Unknown error')}"
                }
                
        except Exception as e:
            logging.error(f"Error creating Salesforce lead: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_contact_from_candidate(self, candidate: ResumeAnalysis, account_id: str = None) -> Dict[str, Any]:
        """Create a Salesforce Contact from a candidate"""
        if not self.sf:
            return {"success": False, "error": "Not connected to Salesforce"}
        
        try:
            # Prepare contact data
            contact_data = {
                'FirstName': candidate.first_name or 'Unknown',
                'LastName': candidate.last_name or 'Candidate',
                'Email': candidate.email,
                'Phone': candidate.phone,
                'LeadSource': 'Resume Submission',
                'Description': self._create_candidate_description(candidate)
            }
            
            # Add account if provided
            if account_id:
                contact_data['AccountId'] = account_id
            
            # Create the contact
            result = self.sf.Contact.create(contact_data)
            
            if result['success']:
                # Store Salesforce ID in database
                candidate.notes = f"{candidate.notes or ''}\nSalesforce Contact ID: {result['id']}"
                db.session.commit()
                
                return {
                    "success": True,
                    "id": result['id'],
                    "message": f"Contact created successfully in Salesforce"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create contact: {result.get('errors', 'Unknown error')}"
                }
                
        except Exception as e:
            logging.error(f"Error creating Salesforce contact: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_opportunity_for_candidate(self, candidate: ResumeAnalysis, job_title: str, account_id: str = None) -> Dict[str, Any]:
        """Create a recruitment opportunity in Salesforce"""
        if not self.sf:
            return {"success": False, "error": "Not connected to Salesforce"}
        
        try:
            # Create opportunity data
            opp_data = {
                'Name': f"{candidate.first_name} {candidate.last_name} - {job_title}",
                'StageName': 'Qualification',
                'CloseDate': (datetime.now().date() + timedelta(days=30)).isoformat(),  # 30 days from now
                'Amount': 0,  # Can be updated with salary expectations
                'Probability': self._calculate_probability(candidate.overall_fit_rating),
                'Description': self._create_candidate_description(candidate),
                'LeadSource': 'Resume Submission'
            }
            
            if account_id:
                opp_data['AccountId'] = account_id
            
            # Create the opportunity
            result = self.sf.Opportunity.create(opp_data)
            
            if result['success']:
                return {
                    "success": True,
                    "id": result['id'],
                    "message": f"Opportunity created successfully in Salesforce"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create opportunity: {result.get('errors', 'Unknown error')}"
                }
                
        except Exception as e:
            logging.error(f"Error creating Salesforce opportunity: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_duplicate_candidate(self, email: str) -> Optional[Dict[str, Any]]:
        """Check if a candidate already exists in Salesforce"""
        if not self.sf:
            return None
        
        try:
            # Search in Leads
            lead_query = f"SELECT Id, FirstName, LastName, Email, Status FROM Lead WHERE Email = '{email}'"
            lead_results = self.sf.query(lead_query)
            
            if lead_results['totalSize'] > 0:
                return {
                    "type": "Lead",
                    "records": lead_results['records']
                }
            
            # Search in Contacts
            contact_query = f"SELECT Id, FirstName, LastName, Email FROM Contact WHERE Email = '{email}'"
            contact_results = self.sf.query(contact_query)
            
            if contact_results['totalSize'] > 0:
                return {
                    "type": "Contact",
                    "records": contact_results['records']
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Error checking for duplicate candidate: {str(e)}")
            return None
    
    def sync_candidate_to_salesforce(self, candidate_id: int, create_as: str = "lead") -> Dict[str, Any]:
        """Sync a candidate to Salesforce as either a Lead or Contact"""
        try:
            candidate = ResumeAnalysis.query.get(candidate_id)
            if not candidate:
                return {"success": False, "error": "Candidate not found"}
            
            # Check for duplicates first
            if candidate.email:
                duplicate = self.check_duplicate_candidate(candidate.email)
                if duplicate:
                    return {
                        "success": False,
                        "error": f"Candidate already exists as {duplicate['type']} in Salesforce",
                        "duplicate": duplicate
                    }
            
            # Create in Salesforce based on preference
            if create_as == "contact":
                return self.create_contact_from_candidate(candidate)
            else:
                return self.create_lead_from_candidate(candidate)
                
        except Exception as e:
            logging.error(f"Error syncing candidate to Salesforce: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def batch_sync_candidates(self, candidate_ids: List[int], create_as: str = "lead") -> Dict[str, Any]:
        """Sync multiple candidates to Salesforce"""
        results = {
            "successful": [],
            "failed": [],
            "duplicates": []
        }
        
        for candidate_id in candidate_ids:
            result = self.sync_candidate_to_salesforce(candidate_id, create_as)
            
            if result["success"]:
                results["successful"].append({
                    "candidate_id": candidate_id,
                    "salesforce_id": result.get("id")
                })
            elif "duplicate" in result:
                results["duplicates"].append({
                    "candidate_id": candidate_id,
                    "message": result["error"]
                })
            else:
                results["failed"].append({
                    "candidate_id": candidate_id,
                    "error": result["error"]
                })
        
        return results
    
    def update_lead_stage(self, lead_id: str, new_status: str) -> Dict[str, Any]:
        """Update the status of a lead in Salesforce"""
        if not self.sf:
            return {"success": False, "error": "Not connected to Salesforce"}
        
        try:
            result = self.sf.Lead.update(lead_id, {'Status': new_status})
            
            if result == 204:  # HTTP 204 No Content indicates success
                return {"success": True, "message": f"Lead status updated to {new_status}"}
            else:
                return {"success": False, "error": "Failed to update lead status"}
                
        except Exception as e:
            logging.error(f"Error updating lead status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_recruitment_pipeline_stats(self) -> Dict[str, Any]:
        """Get recruitment pipeline statistics from Salesforce"""
        if not self.sf:
            return {"error": "Not connected to Salesforce"}
        
        try:
            # Query leads by status
            lead_query = """
                SELECT Status, COUNT(Id) count 
                FROM Lead 
                WHERE LeadSource = 'Resume Submission' 
                GROUP BY Status
            """
            lead_results = self.sf.query(lead_query)
            
            # Query opportunities by stage
            opp_query = """
                SELECT StageName, COUNT(Id) count 
                FROM Opportunity 
                WHERE LeadSource = 'Resume Submission' 
                GROUP BY StageName
            """
            opp_results = self.sf.query(opp_query)
            
            return {
                "leads_by_status": {
                    record['Status']: record['count'] 
                    for record in lead_results['records']
                },
                "opportunities_by_stage": {
                    record['StageName']: record['count'] 
                    for record in opp_results['records']
                },
                "total_leads": sum(record['count'] for record in lead_results['records']),
                "total_opportunities": sum(record['count'] for record in opp_results['records'])
            }
            
        except Exception as e:
            logging.error(f"Error getting pipeline stats: {str(e)}")
            return {"error": str(e)}
    
    def _create_candidate_description(self, candidate: ResumeAnalysis) -> str:
        """Create a comprehensive description for Salesforce records"""
        description_parts = []
        
        description_parts.append(f"Source: {candidate.source}")
        description_parts.append(f"Upload Date: {candidate.upload_date.strftime('%Y-%m-%d')}")
        
        if candidate.overall_fit_rating:
            description_parts.append(f"Fit Rating: {candidate.overall_fit_rating}/10")
        
        if candidate.risk_factor_score:
            description_parts.append(f"Risk Score: {candidate.risk_factor_score}/10")
        
        if candidate.reward_factor_score:
            description_parts.append(f"Reward Score: {candidate.reward_factor_score}/10")
        
        if candidate.candidate_strengths:
            try:
                strengths = json.loads(candidate.candidate_strengths)
                if strengths:
                    description_parts.append(f"\nStrengths:\n" + "\n".join(f"- {s}" for s in strengths[:3]))
            except:
                pass
        
        if candidate.justification:
            description_parts.append(f"\nAnalysis:\n{candidate.justification[:500]}")
        
        return "\n".join(description_parts)
    
    def _convert_rating_to_sf_rating(self, overall_fit_rating: float) -> str:
        """Convert numeric rating to Salesforce Lead Rating"""
        if not overall_fit_rating:
            return "Cold"
        
        if overall_fit_rating >= 8:
            return "Hot"
        elif overall_fit_rating >= 6:
            return "Warm"
        else:
            return "Cold"
    
    def _calculate_probability(self, overall_fit_rating: float) -> int:
        """Calculate opportunity probability based on fit rating"""
        if not overall_fit_rating:
            return 10
        
        # Map 0-10 rating to 10-90% probability
        return min(90, max(10, int(overall_fit_rating * 9)))

from datetime import timedelta  # Add this import at the top
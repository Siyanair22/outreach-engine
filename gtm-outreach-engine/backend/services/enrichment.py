"""
Enrichment service for fetching company and contact data from external APIs.

Currently supports:
- Hunter.io (email finding and domain search)
- Manual/mock enrichment for development

The service is designed to be modular — each provider implements the same
interface, so adding new sources (Clearbit, Apollo, etc.) is straightforward.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()


async def enrich_prospect(domain: str | None, company_name: str) -> dict:
    """
    Enrich a prospect with company and contact data.
    
    Tries real APIs first (if keys are configured), falls back to
    mock data for development. Returns a dict of enrichment fields
    that map directly to Prospect model columns.
    
    Args:
        domain: Company website domain (e.g., "stripe.com")
        company_name: Company name for fallback searches
    
    Returns:
        Dict with keys: company_description, industry, employee_count,
        location, funding_stage, technologies, contact_email
    """
    
    hunter_key = os.getenv("HUNTER_API_KEY")
    
    result = {}
    
    # Try Hunter.io for domain-based enrichment
    if hunter_key and domain:
        try:
            hunter_data = await _hunter_domain_search(domain, hunter_key)
            result.update(hunter_data)
        except Exception as e:
            print(f"Hunter.io enrichment failed for {domain}: {e}")
    
    # If we didn't get data from APIs, use mock enrichment for development
    if not result.get("company_description"):
        result = _mock_enrich(domain, company_name)
    
    return result


async def _hunter_domain_search(domain: str, api_key: str) -> dict:
    """
    Query Hunter.io's Domain Search API for company and contact info.
    
    Hunter.io free tier: 25 searches/month. The domain search returns
    the organization name, description, and associated email addresses.
    
    API docs: https://hunter.io/api-documentation#domain-search
    """
    
    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": 5  # only need a few contacts
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json().get("data", {})
    
    result = {}
    
    # Extract organization info
    org = data.get("organization") or ""
    if org:
        result["company_description"] = org
    
    # Extract industry and other metadata
    if data.get("industry"):
        result["industry"] = data["industry"]
    
    if data.get("country"):
        result["location"] = data["country"]
    
    # Extract the most relevant contact email
    emails = data.get("emails", [])
    if emails:
        # Prefer contacts with higher confidence scores
        best = sorted(emails, key=lambda e: e.get("confidence", 0), reverse=True)
        top = best[0]
        result["contact_email"] = top.get("value")
        
        # Use their name if we don't already have one
        first = top.get("first_name", "")
        last = top.get("last_name", "")
        if first or last:
            result["contact_name"] = f"{first} {last}".strip()
        if top.get("position"):
            result["contact_role"] = top["position"]
    
    return result


def _mock_enrich(domain: str | None, company_name: str) -> dict:
    """
    Mock enrichment for development and testing.
    
    Returns plausible data so the full pipeline can be tested
    without real API keys. In production, this would be removed
    or used as a fallback.
    """
    
    # Simple lookup for common test companies
    mock_db = {
        "stripe.com": {
            "company_description": "Financial infrastructure platform for internet businesses",
            "industry": "Fintech",
            "employee_count": "8000+",
            "location": "San Francisco, CA",
            "funding_stage": "Series I",
            "technologies": "Ruby, React, Go, AWS",
        },
        "razorpay.com": {
            "company_description": "Full-stack payments and banking platform for businesses in India",
            "industry": "Fintech",
            "employee_count": "3000+",
            "location": "Bangalore, India",
            "funding_stage": "Series F",
            "technologies": "Go, React, Kubernetes, AWS",
        },
        "notion.so": {
            "company_description": "All-in-one workspace for notes, docs, and project management",
            "industry": "Productivity / SaaS",
            "employee_count": "500+",
            "location": "San Francisco, CA",
            "funding_stage": "Series C",
            "technologies": "TypeScript, React, Kotlin, AWS",
        },
    }
    
    # Check if we have mock data for this domain
    if domain and domain.lower() in mock_db:
        return mock_db[domain.lower()]
    
    # Generic fallback
    return {
        "company_description": f"{company_name} is a technology company.",
        "industry": "Technology",
        "employee_count": "Unknown",
        "location": "Unknown",
        "funding_stage": "Unknown",
        "technologies": "Unknown",
    }

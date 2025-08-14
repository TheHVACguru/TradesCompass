# External Sourcing API Keys Setup

## Overview
TradesCompass Pro now supports multiple professional data providers for sourcing candidates. Each provider offers unique data and requires API key configuration.

## Supported Data Providers

### 1. GitHub (Currently Active)
- **Status**: ✅ Configured and working
- **Key Variable**: `GITHUB_TOKEN`
- **Data Access**: Public developer profiles, repositories, skills
- **Free Tier**: 60 requests/hour (5,000 with authentication)
- **Setup**: Already configured in your environment

### 2. PeopleDataLabs
- **Status**: ⏳ API key required
- **Key Variable**: `PEOPLEDATA_KEY`
- **Data Access**: Professional profiles, contact info, work history
- **Website**: https://www.peopledatalabs.com
- **Setup Steps**:
  1. Sign up at https://www.peopledatalabs.com/signup
  2. Choose a plan (Free tier: 100 credits/month)
  3. Get your API key from the dashboard
  4. Add to Replit Secrets: `PEOPLEDATA_KEY`

### 3. SeekOut
- **Status**: ⏳ API key required
- **Key Variable**: `SEEKOUT_API_KEY`
- **Data Access**: Active job seekers, diversity data, skills assessment
- **Website**: https://seekout.com
- **Setup Steps**:
  1. Request API access at https://seekout.com/api
  2. Schedule demo with sales team
  3. Get API credentials
  4. Add to Replit Secrets: `SEEKOUT_API_KEY`

### 4. SourceHub
- **Status**: ⏳ API key required
- **Key Variable**: `SOURCEHUB_API_KEY`
- **Data Access**: Candidate profiles, availability status, salary expectations
- **Website**: https://sourcehub.com
- **Setup Steps**:
  1. Contact sales at https://sourcehub.com/contact
  2. Request API access for recruitment platform
  3. Receive API credentials
  4. Add to Replit Secrets: `SOURCEHUB_API_KEY`

## How to Add API Keys in Replit

1. Click the **"Secrets"** icon in the left sidebar (🔐)
2. Click **"New Secret"**
3. Enter the key name (e.g., `PEOPLEDATA_KEY`)
4. Paste your API key value
5. Click **"Add Secret"**

## Testing Your Configuration

After adding API keys, test external search:
1. Go to **Candidates** page
2. Click **"Find New Candidates"** tab
3. Enter a job title (e.g., "HVAC Technician")
4. Click **"Search External Candidates"**

The system will automatically use all configured APIs and show results from each source.

## Features by Provider

| Provider | Contact Info | Skills | Experience | Salary | Availability |
|----------|-------------|--------|------------|--------|--------------|
| GitHub | ❌ | ✅ | ✅ | ❌ | ❌ |
| PeopleDataLabs | ✅ | ✅ | ✅ | ❌ | ❌ |
| SeekOut | ✅ | ✅ | ✅ | ✅ | ✅ |
| SourceHub | ✅ | ✅ | ✅ | ✅ | ✅ |

## Rate Limits & Costs

- **GitHub**: Free with token (5,000/hour)
- **PeopleDataLabs**: 100 free searches/month, then $0.10/search
- **SeekOut**: Custom pricing based on volume
- **SourceHub**: Subscription-based, typically $299/month

## Troubleshooting

If searches aren't returning results from a provider:
1. Check that the API key is correctly set in Secrets
2. Verify the API key is valid and not expired
3. Check rate limits haven't been exceeded
4. Review the application logs for specific error messages

## Support

For API-specific issues:
- GitHub: https://docs.github.com/en/rest
- PeopleDataLabs: support@peopledatalabs.com
- SeekOut: api-support@seekout.com
- SourceHub: developers@sourcehub.com
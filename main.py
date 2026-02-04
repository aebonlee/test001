import re
import time
import logging
import requests
import httpx
from typing import List, Dict, Any, Optional, Tuple
from unittest.mock import MagicMock

# --- Constants and Globals ---

# Placeholder for the base URL for raw GitHub content.
# You should replace this with the correct URL for your repository.
# e.g., "https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs"
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/user/repo/main"

# Placeholder for the GraphQL query for GitHub repository search.
GITHUB_GRAPHQL_QUERY = """
query($query: String!, $numResults: Int!) {
  search(query: $query, type: REPOSITORY, first: $numResults) {
    edges {
      node {
        ... on Repository {
          nameWithOwner
          url
          description
          owner {
            login
          }
          stargazerCount
          updatedAt
          primaryLanguage {
            name
          }
          repositoryTopics(first: 10) {
            nodes {
              topic {
                name
              }
            }
          }
          licenseInfo {
            name
          }
          openIssues: issues(states: OPEN) {
            totalCount
          }
          forkCount
          homepageUrl
        }
      }
    }
  }
}
"""

_GITHUB_DOC_CACHE = {}
logger = logging.getLogger(__name__)

# --- Models ---

class GitHubDeps:
    client: httpx.AsyncClient
    github_token: str | None = None

# --- GitHub API Functions ---

def github_graphql_request(
    query: str,
    variables: Dict[str, Any],
    token: Optional[str] = None
) -> Dict[str, Any]:
    """Make a request to the GitHub GraphQL API with exponential backoff for rate limiting.

    Args:
        query: The GraphQL query
        variables: Variables for the GraphQL query
        token: Optional GitHub token for authentication

    Returns:
        The JSON response from the API
    """
    headers = {
        'Content-Type': 'application/json',
    }

    # Add authorization header if token is provided
    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        response = requests.post(
            'https://api.github.com/graphql',
            headers=headers,
            json={'query': query, 'variables': variables},
            timeout=10,  # Add 10 second timeout to prevent hanging requests
        )

        # Check for rate limiting
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            # For unauthenticated requests, don't wait - just log and return empty response
            if not token:
                logger.warning(
                    'Rate limited by GitHub API and no token provided. Consider adding a GITHUB_TOKEN.'
                )
                return {'data': {'search': {'edges': []}}}

            # For authenticated requests, check reset time but cap at reasonable value
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            current_time = int(time.time())
            wait_time = min(max(reset_time - current_time, 0), 60)  # Cap at 60 seconds

            if wait_time > 0:
                logger.warning(f'Rate limited by GitHub API. Waiting {wait_time} seconds.')
                time.sleep(wait_time)
                # Retry the request
                return github_graphql_request(query, variables, token)

        # Raise exception for other HTTP errors
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f'GitHub API request error: {str(e)}')
        raise

def github_repo_search_graphql(
    keywords: List[str],
    organizations: List[str],
    num_results: int = 5,
    token: Optional[str] = None,
    license_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Search GitHub repositories using the GraphQL API.

    Args:
        keywords: List of keywords to search for
        organizations: List of GitHub organizations to scope the search to
        num_results: Number of results to return
        token: Optional GitHub token for authentication
        license_filter: Optional list of license names to filter repositories by

    Returns:
        List of GitHub repositories matching the search criteria
    """
    # Build the search query with organization filters
    org_filters = ' '.join([f'org:{org}' for org in organizations])
    keyword_string = ' OR '.join(keywords)
    query_string = f'{keyword_string} {org_filters}'

    logger.info(f'Searching GitHub with GraphQL query: {query_string}')

    try:
        # Make the GraphQL request
        variables = {
            'query': query_string,
            'numResults': num_results * 2,  # Request more than needed to filter
        }

        response = github_graphql_request(GITHUB_GRAPHQL_QUERY, variables, token)

        if 'errors' in response:
            error_messages = [
                error.get('message', 'Unknown error') for error in response['errors']
            ]
            logger.error(f'GitHub GraphQL API errors: {', '.join(error_messages)}')
            return []

        # Extract repository data from response
        search_data = response.get('data', {}).get('search', {})
        edges = search_data.get('edges', [])

        repo_results = []
        processed_urls = set()  # To avoid duplicates

        for edge in edges:
            node = edge.get('node', {})

            # Extract repository information
            repo_url = node.get('url', '')
            name_with_owner = node.get('nameWithOwner', '')
            description = node.get('description', '')
            owner = node.get('owner', {}).get('login', '')

            # Skip if we've already processed this URL or if it's not from one of our target organizations
            if repo_url in processed_urls or owner.lower() not in [
                org.lower() for org in organizations
            ]:
                continue

            processed_urls.add(repo_url)

            # Extract primary language if available
            primary_language = node.get('primaryLanguage', {})
            language = primary_language.get('name') if primary_language else None

            # Extract topics if available
            topics_data = node.get('repositoryTopics', {}).get('nodes', [])
            topics = [
                topic.get('topic', {}).get('name') for topic in topics_data if topic.get('topic')
            ]

            # Extract license information if available
            license_info = node.get('licenseInfo', {})
            license_name = license_info.get('name') if license_info else None

            # Skip if license filter is specified and this repository's license doesn't match
            if license_filter and license_name and license_name not in license_filter:
                continue

            # Extract open issues count
            open_issues = node.get('openIssues', {}).get('totalCount', 0)

            # Add to results with additional metadata
            repo_results.append(
                {
                    'url': repo_url,
                    'title': name_with_owner,
                    'description': description,
                    'organization': owner,
                    'stars': node.get('stargazerCount', 0),
                    'updated_at': node.get('updatedAt', ''),
                    'language': language,
                    'topics': topics,
                    'license': license_name,
                    'forks': node.get('forkCount', 0),
                    'open_issues': open_issues,
                    'homepage': node.get('homepageUrl'),
                }
            )

            # Stop if we have enough results
            if len(repo_results) >= num_results:
                break

        logger.info(f'Found {len(repo_results)} GitHub repositories via GraphQL API')
        return repo_results

    except Exception as e:
        logger.error(f'GitHub GraphQL search error: {str(e)}')
        return []


def github_repo_search_rest(
    keywords: List[str],
    organizations: List[str],
    num_results: int = 5,
    license_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Search GitHub repositories using the REST API.

    This is a fallback for when GraphQL API is rate limited and no token is provided.

    Args:
        keywords: List of keywords to search for
        organizations: List of GitHub organizations to scope the search to
        num_results: Number of results to return
        license_filter: Optional list of license names to filter repositories by

    Returns:
        List of GitHub repositories matching the search criteria
    """
    repo_results = []
    processed_urls = set()

    # Process each organization separately
    for org in organizations:
        try:
            # Build the search query for this organization
            keyword_string = '+OR+'.join(keywords)
            query_string = f'{keyword_string}+org:{org}'

            logger.info(f'Searching GitHub REST API for org {org}')

            # Make the REST API request
            response = requests.get(
                f'https://api.github.com/search/repositories?q={query_string}&sort=stars&order=desc&per_page={num_results}',
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=10,  # Add 10 second timeout to prevent hanging requests
            )

            # Check for errors
            response.raise_for_status()

            # Parse the response
            data = response.json()
            items = data.get('items', [])

            # Process each repository
            for item in items:
                repo_url = item.get('html_url', '')

                # Skip if we've already processed this URL
                if repo_url in processed_urls:
                    continue

                processed_urls.add(repo_url)

                # Extract license information if available
                license_info = item.get('license')
                license_name = license_info.get('name') if license_info else None

                # Skip if license filter is specified and this repository's license doesn't match
                if license_filter and license_name and license_name not in license_filter:
                    continue

                # Extract topics if available
                topics = item.get('topics', [])

                # Add to results with additional metadata
                repo_results.append(
                    {
                        'url': repo_url,
                        'title': item.get('full_name', ''),
                        'description': item.get('description', ''),
                        'organization': org,
                        'stars': item.get('stargazers_count', 0),
                        'updated_at': item.get('updated_at', ''),
                        'language': item.get('language'),
                        'topics': topics,
                        'license': license_name,
                        'forks': item.get('forks_count', 0),
                        'open_issues': item.get('open_issues_count', 0),
                        'homepage': item.get('homepage'),
                    }
                )

                # Stop if we have enough results
                if len(repo_results) >= num_results:
                    break

            # Add a small delay between requests to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            logger.error(f'GitHub REST API error for org {org}: {str(e)}')
            continue

    logger.info(f'Found {len(repo_results)} GitHub repositories via REST API')
    return repo_results

# --- Documentation Fetching ---

def resource_to_github_path(
    asset_name: str, asset_type: str = 'resource', correlation_id: str = ''
) -> Tuple[str, str]:
    """Convert AWS resource type to GitHub documentation file path.

    Args:
        asset_name: The name of the asset to search (e.g., 'aws_s3_bucket' or 'awscc_s3_bucket')
        asset_type: Type of asset to search for - 'resource' or 'data_source'
        correlation_id: Identifier for tracking this request in logs

    Returns:
        A tuple of (path, url) for the GitHub documentation file
    """
    # Validate input parameters
    if not isinstance(asset_name, str) or not asset_name:
        logger.error(f'[{correlation_id}] Invalid asset_name: {asset_name}')
        raise ValueError('asset_name must be a non-empty string')

    # Sanitize asset_name to prevent path traversal and URL manipulation
    # Only allow alphanumeric characters, underscores, and hyphens
    
    if asset_name.startswith('awscc_'):
        sanitized_name = asset_name
        if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized_name.replace('awscc_', '')):
            logger.error(f'[{correlation_id}] Invalid characters in asset_name: {asset_name}')
            raise ValueError('asset_name contains invalid characters')
        resource_name = sanitized_name[6:]
        logger.trace(f"[{correlation_id}] Removed 'awscc_' prefix: {resource_name}")
        
        if asset_type == 'data_source':
            doc_type = 'data-sources'
        else:
            doc_type = 'resources'
        
        file_path = f'{doc_type}/{resource_name}.md'

    elif asset_name.startswith('aws_'):
        sanitized_name = asset_name
        if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized_name.replace('aws_', '')):
            logger.error(f'[{correlation_id}] Invalid characters in asset_name: {asset_name}')
            raise ValueError('asset_name contains invalid characters')
        resource_name = sanitized_name[4:]
        logger.trace(f"[{correlation_id}] Removed 'aws_' prefix: {resource_name}")

        if asset_type == 'data_source':
            doc_type = 'd'
        else:
            doc_type = 'r'
            
        file_path = f'{doc_type}/{resource_name}.html.markdown'
    else:
        raise ValueError("asset_name must start with 'aws_' or 'awscc_'")

    logger.trace(f'[{correlation_id}] Constructed GitHub file path: {file_path}')
    github_url = f'{GITHUB_RAW_BASE_URL}/{file_path}'
    logger.trace(f'[{correlation_id}] GitHub raw URL: {github_url}')

    return file_path, github_url


def fetch_github_documentation(
    asset_name: str, asset_type: str, cache_enabled: bool, correlation_id: str = ''
) -> Optional[Dict[str, Any]]:
    """Fetch documentation from GitHub for a specific resource type.

    Args:
        asset_name: The asset name (e.g., 'awscc_s3_bucket')
        asset_type: Either 'resource' or 'data_source'
        cache_enabled: Whether local cache is enabled or not
        correlation_id: Identifier for tracking this request in logs

    Returns:
        Dictionary with markdown content and metadata, or None if not found
    """
    start_time = time.time()
    logger.info(f"[{correlation_id}] Fetching documentation from GitHub for '{asset_name}'")

    # Create a cache key that includes both asset_name and asset_type
    cache_key = f'{asset_name}_{asset_type}'

    # Check cache first
    if cache_enabled:
        if cache_key in _GITHUB_DOC_CACHE:
            logger.info(
                f"[{correlation_id}] Using cached documentation for '{asset_name}' (asset_type: {asset_type})"
            )
            return _GITHUB_DOC_CACHE[cache_key]

    try:
        # Convert resource type to GitHub path and URL
        try:
            _, github_url = resource_to_github_path(asset_name, asset_type, correlation_id)
        except ValueError as e:
            logger.error(f'[{correlation_id}] Invalid input parameters: {str(e)}')
            return None

        # Validate the constructed URL to ensure it points to the expected domain
        if not github_url.startswith(GITHUB_RAW_BASE_URL):
            logger.error(f'[{correlation_id}] Invalid GitHub URL constructed: {github_url}')
            return None

        # Fetch the markdown content from GitHub
        logger.info(f'[{correlation_id}] Fetching from GitHub: {github_url}')
        response = requests.get(github_url, timeout=10)

        if response.status_code != 200:
            logger.warning(
                f'[{correlation_id}] GitHub request failed: HTTP {response.status_code}'
            )
            return None

        markdown_content = response.text
        content_length = len(markdown_content)
        logger.debug(f'[{correlation_id}] Received markdown content: {content_length} bytes')

        if content_length > 0:
            preview_length = min(200, content_length)
            logger.trace(
                f'[{correlation_id}] Markdown preview: {markdown_content[:preview_length]}...'
            )

        # The user did not provide the parse_markdown_documentation function.
        # I will return the raw content for now.
        # result = parse_markdown_documentation(
        #     markdown_content, asset_name, github_url, correlation_id
        # )
        result = {"content": markdown_content, "url": github_url}


        # Cache the result with the composite key
        if cache_enabled:
            _GITHUB_DOC_CACHE[cache_key] = result

        fetch_time = time.time() - start_time
        logger.info(f'[{correlation_id}] GitHub documentation fetched in {fetch_time:.2f} seconds')
        return result

    except requests.exceptions.Timeout as e:
        logger.warning(f'[{correlation_id}] Timeout error fetching from GitHub: {str(e)}')
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f'[{correlation_id}] Request error fetching from GitHub: {str(e)}')
        return None
    except Exception as e:
        logger.error(
            f'[{correlation_id}] Unexpected error fetching from GitHub: {type(e).__name__}: {str(e)}'
        )
        # Don't log the full stack trace to avoid information disclosure
        return None

# --- Utility Functions ---

def clean_github_url(url: str) -> str:
    """Clean GitHub URLs to get the base repository URL."""
    if 'github.com' in url:
        parts = url.split('/')
        if len(parts) > 4:
            return '/'.join(parts[:5])
    return url

# --- Mocks ---

def mock_github_release():
    """Create mock GitHub release data."""
    return {
        'tag_name': 'v3.14.0',
        'published_at': '2023-02-01T00:00:00Z',
        'name': 'Release 3.14.0',
        'body': "## What's Changed\n* Feature: Added support for IPv6\n* Bug fix: Fixed subnet creation",
    }

def mock_bedrock_agent_client():
    """Create a mock Bedrock Agent client."""
    client = MagicMock()

    # Mock the get_paginator method for list_knowledge_bases
    kb_paginator = MagicMock()
    kb_paginator.paginate.return_value = [
        {
            'knowledgeBaseSummaries': [
                {'knowledgeBaseId': 'kb-12345', 'name': 'Test Knowledge Base'},
                {'knowledgeBaseId': 'kb-67890', 'name': 'Another Knowledge Base'},
                {'knowledgeBaseId': 'kb-95008', 'name': 'Yet another Knowledge Base'},
            ]
        }
    ]

    # Mock the get_paginator method for list_data_sources
    ds_paginator = MagicMock()
    ds_paginator.paginate.return_value = [
        {
            'dataSourceSummaries': [
                {'dataSourceId': 'ds-12345', 'name': 'Test Data Source'},
                {'dataSourceId': 'ds-67890', 'name': 'Another Data Source'},
            ]
        }
    ]

    # Mock the get_knowledge_base method
    client.get_knowledge_base.side_effect = lambda knowledgeBaseId: {
        'knowledgeBase': {
            'knowledgeBaseArn': f'arn:aws:bedrock:us-west-2:123456789012:knowledge-base/{knowledgeBaseId}'
        }
    }

    def list_tags_for_resource_side_effect(resourceArn: str):
        kb_id = resourceArn.split('/')[-1]

        if kb_id == 'kb-95008':
            return {'tags': {'custom-tag': 'true'}}

        return {'tags': {'mcp-multirag-kb': 'true'}}

    # Mock the list_tags_for_resource method
    client.list_tags_for_resource.side_effect = list_tags_for_resource_side_effect

    # Set up the paginator returns
    client.get_paginator.side_effect = lambda operation_name: {
        'list_knowledge_bases': kb_paginator,
        'list_data_sources': ds_paginator,
    }[operation_name]

    return client
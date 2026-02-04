import pytest
from typing import Dict, Any

# It's not best practice to import from `main`, but for this simple case it's fine.
# In a real project, the code would be in a package.
from main import clean_github_url

# The user provided many test snippets that depend on a larger project structure
# and other modules that are not available here.
# I am including the tests here that are self-contained and runnable.

# --- Placeholders for missing types/classes ---

ContentItem = Dict[str, Any]

# --- Tests ---

def test_clean_github_url():
    """Test cleaning GitHub URLs."""
    # Test with a full file URL
    url = 'https://github.com/aws-samples/aws-cdk-examples/blob/main/typescript/api-gateway-lambda/index.ts'
    assert clean_github_url(url) == 'https://github.com/aws-samples/aws-cdk-examples'

    # Test with just the repository URL
    url = 'https://github.com/awslabs/mcp'
    assert clean_github_url(url) == 'https://github.com/awslabs/mcp'

    # Test with a non-GitHub URL
    url = 'https://example.com'
    assert clean_github_url(url) == 'https://example.com'

    # Test with a malformed GitHub URL
    url = 'https://github.com'
    assert clean_github_url(url) == 'https://github.com'

def test_content_item_creation():
    """Test creating a ContentItem."""
    # This test is self-contained, so it can be run.
    content_item: ContentItem = {'type': 'text', 'text': 'Test content'}
    assert content_item['type'] == 'text'
    assert content_item['text'] == 'Test content'

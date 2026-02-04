import pytest
from typing import Dict, Any
from unittest.mock import patch, MagicMock, AsyncMock
import os
import tempfile
import subprocess

# It's not best practice to import from `main`, but for this simple case it's fine.
# In a real project, the code would be in a package.
from main import clean_github_url

# The user provided many test snippets that depend on a larger project structure
# and other modules that are not available here.
# I am including the tests here that are self-contained and runnable.

# --- Placeholders for missing types/classes ---

ContentItem = Dict[str, Any]
class DeploymentStatus:
    FAILED = "FAILED"
__version__ = "1.0.0" # Placeholder

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

# --- Commented out tests that are not runnable ---

# async def test_sam_build_failure(self):
#         """Test SAM build failure."""
#         # This test depends on 'SamBuildTool' and 'awslabs.aws_serverless_mcp_server' which are not defined.
#         error_message = b'Command failed with exit code 1'
#         with patch(
#             'awslabs.aws_serverless_mcp_server.tools.sam.sam_build.run_command',
#             side_effect=subprocess.CalledProcessError(1, 'sam build', stderr=error_message),
#         ):
#             result = await SamBuildTool(MagicMock()).handle_sam_build(
#                 AsyncMock(),
#                 project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
#                 template_file=None,
#                 base_dir=None,
#                 build_dir=None,
#                 use_container=False,
#                 no_use_container=False,
#                 container_env_vars=None,
#                 container_env_var_file=None,
#                 build_image=None,
#                 debug=False,
#                 manifest=None,
#                 parameter_overrides=None,
#                 region=None,
#                 save_params=False,
#                 profile=None,
#             )
#             assert result['success'] is False
#             assert 'Failed to build SAM project' in result['message']
#             assert 'Command failed with exit code 1' in result['message']

# async def test_api_error(self, mock_bedrock_runtime_client):
#         """Test handling of API errors."""
#         # This test depends on 'invoke_nova_canvas' which is not defined.
#         mock_bedrock_runtime_client.invoke_model.side_effect = Exception('API error')
#         request_dict = {
#             'taskType': 'TEXT_IMAGE',
#             'textToImageParams': {'text': 'A beautiful mountain landscape'},
#         }
#         with pytest.raises(Exception, match='API error'):
#             await invoke_nova_canvas(request_dict, mock_bedrock_runtime_client)

# async def test_store_deployment_error_basic(self):
#         """Test store_deployment_error function with basic functionality."""
#         # This test depends on 'store_deployment_error' and 'awslabs.aws_serverless_mcp_server' which are not defined.
#         with patch(
#             'awslabs.aws_serverless_mcp_server.utils.deployment_manager.store_deployment_metadata',
#             new_callable=AsyncMock,
#         ) as mock_store:
#             project_name = 'test-project'
#             error = 'Test error message'
#             await store_deployment_error(project_name, error)
#             mock_store.assert_called_once()
#             args, kwargs = mock_store.call_args
#             assert args[0] == project_name
#             error_metadata = args[1]
#             assert error_metadata['status'] == DeploymentStatus.FAILED
#             assert error_metadata['error'] == error
#             assert 'errorTimestamp' in error_metadata

# def test_basic_connection(self):
#         """Test basic connection creation without cluster mode or SSL."""
#         # This test depends on 'ValkeyConnectionManager' and 'awslabs.valkey_mcp_server' which are not defined.
#         with (
#             patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
#             patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
#         ):
#             mock_cfg.__getitem__.side_effect = {
#                 'cluster_mode': False,
#                 'host': 'localhost',
#                 'port': 6379,
#             }.__getitem__
#             mock_cfg.get.side_effect = lambda key, default=None: {
#                 'username': None,
#                 'password': '',
#                 'ssl': False,
#             }.get(key, default)
#             conn = ValkeyConnectionManager.get_connection()
#             mock_valkey.assert_called_once_with(
#                 host='localhost',
#                 port=6379,
#                 username=None,
#                 password='',
#                 ssl=False,
#                 ssl_ca_path=None,
#                 ssl_keyfile=None,
#                 ssl_certfile=None,
#                 ssl_cert_reqs=None,
#                 ssl_ca_certs=None,
#                 decode_responses=True,
#                 max_connections=10,
#                 lib_name=f'valkey-py(mcp-server_v{__version__})',
#             )
#             self.assertEqual(conn, mock_valkey.return_value)

# async def test_validation_error(
#         self, mock_invoke_nova_canvas, mock_bedrock_runtime_client, sample_text_prompt
#     ):
#         """Test handling of validation errors."""
#         # This test depends on 'generate_image_with_colors' which is not defined.
#         result = await generate_image_with_colors(
#             prompt=sample_text_prompt,
#             colors=['invalid_color'],  # Invalid color format
#             bedrock_runtime_client=mock_bedrock_runtime_client,
#         )
#         assert result.status == 'error'
#         assert 'Validation error' in result.message
#         assert result.paths == []
#         assert result.prompt == sample_text_prompt
#         assert result.colors == ['invalid_color']
#         mock_invoke_nova_canvas.assert_not_called()

# async def test_test_migration_basic(self, mock_elasticache_client):
#         """Test testing migration with basic parameters."""
#         # This test depends on 'create_test_request' and 'test_migration' which are not defined.
#         expected_response = {
#             'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'available'},
#             'TestMigration': {'Status': 'successful'},
#         }
#         mock_elasticache_client.test_migration.return_value = expected_response
#         request = create_test_request()
#         response = await test_migration(request)
#         mock_elasticache_client.test_migration.assert_called_once_with(
#             ReplicationGroupId='test-rg',
#             CustomerNodeEndpointList=[{'Address': '10.0.0.1', 'Port': 6379}],
#         )
#         assert response == expected_response
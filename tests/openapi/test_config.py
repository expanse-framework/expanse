"""Tests for OpenAPIConfig class."""

from __future__ import annotations

import pytest

from expanse.openapi.config import OpenAPIConfig


def test_basic_initialization():
    """Test basic OpenAPIConfig initialization with required parameters."""
    config = OpenAPIConfig(title="Test API", version="1.0.0")

    assert config.title == "Test API"
    assert config.version == "1.0.0"
    assert config.openapi_version == "3.1.0"
    assert config.description is None
    assert config.include_patterns == ["**"]
    assert config.exclude_patterns == []
    assert config.docstring_style == "auto"
    assert config.include_internal_routes is False
    assert config.inference_depth == "deep"
    assert config.generate_examples is True
    assert config.security_schemes == {}
    assert config.servers == []
    assert config.tags == []
    assert config.contact is None
    assert config.license_info is None
    assert config.terms_of_service is None


def test_full_initialization():
    """Test OpenAPIConfig initialization with all parameters."""
    security_schemes = {"bearerAuth": {"type": "http", "scheme": "bearer"}}
    servers = [{"url": "https://api.example.com", "description": "Production"}]
    tags = [{"name": "users", "description": "User operations"}]
    contact = {"name": "Support", "email": "support@example.com"}
    license_info = {"name": "MIT", "url": "https://opensource.org/licenses/MIT"}

    config = OpenAPIConfig(
        title="Advanced API",
        version="2.1.0",
        openapi_version="3.0.3",
        description="A comprehensive API",
        include_patterns=["/api/**", "/v1/**"],
        exclude_patterns=["/internal/**"],
        docstring_style="google",
        include_internal_routes=True,
        inference_depth="medium",
        generate_examples=False,
        security_schemes=security_schemes,
        servers=servers,
        tags=tags,
        contact=contact,
        license_info=license_info,
        terms_of_service="https://example.com/terms",
    )

    assert config.title == "Advanced API"
    assert config.version == "2.1.0"
    assert config.openapi_version == "3.0.3"
    assert config.description == "A comprehensive API"
    assert config.include_patterns == ["/api/**", "/v1/**"]
    assert config.exclude_patterns == ["/internal/**"]
    assert config.docstring_style == "google"
    assert config.include_internal_routes is True
    assert config.inference_depth == "medium"
    assert config.generate_examples is False
    assert config.security_schemes == security_schemes
    assert config.servers == servers
    assert config.tags == tags
    assert config.contact == contact
    assert config.license_info == license_info
    assert config.terms_of_service == "https://example.com/terms"


def test_should_include_route_with_include_patterns():
    """Test route inclusion based on include patterns."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        include_patterns=["/api/**", "/v1/users/**"],
    )

    assert config.should_include_route("/api/users") is True
    assert config.should_include_route("/api/posts/123") is True
    assert config.should_include_route("/v1/users/profile") is True
    assert config.should_include_route("/admin/dashboard") is False
    assert config.should_include_route("/health") is False


def test_should_include_route_with_exclude_patterns():
    """Test route exclusion based on exclude patterns."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        include_patterns=["**"],
        exclude_patterns=["/internal/**", "/debug/**"],
    )

    assert config.should_include_route("/api/users") is True
    assert config.should_include_route("/v1/posts") is True
    assert config.should_include_route("/internal/metrics") is False
    assert config.should_include_route("/debug/logs") is False
    assert config.should_include_route("/internal/health/check") is False


def test_should_include_route_exclude_takes_precedence():
    """Test that exclude patterns take precedence over include patterns."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        include_patterns=["**"],
        exclude_patterns=["/api/internal/**"],
    )

    assert config.should_include_route("/api/users") is True
    assert config.should_include_route("/api/posts") is True
    assert config.should_include_route("/api/internal/metrics") is False
    assert config.should_include_route("/api/internal/debug") is False


def test_should_include_route_no_matching_include_pattern():
    """Test route exclusion when no include patterns match."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        include_patterns=["/api/**"],
    )

    assert config.should_include_route("/api/users") is True
    assert config.should_include_route("/v1/users") is False
    assert config.should_include_route("/admin/dashboard") is False


def test_should_include_route_complex_patterns():
    """Test route inclusion with complex glob patterns."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        include_patterns=["/api/v*/users", "/api/*/posts/**"],
        exclude_patterns=["/api/v1/users/internal"],
    )

    assert config.should_include_route("/api/v1/users") is True
    assert config.should_include_route("/api/v2/users") is True
    assert config.should_include_route("/api/v1/posts/123") is True
    assert config.should_include_route("/api/v2/posts/456/comments") is True
    assert config.should_include_route("/api/v1/users/internal") is False
    assert config.should_include_route("/api/v1/comments") is False


def test_default_patterns(openapi_config):
    """Test that default patterns include everything."""
    assert openapi_config.should_include_route("/any/path") is True
    assert openapi_config.should_include_route("/api/users") is True
    assert openapi_config.should_include_route("/admin/dashboard") is True
    assert openapi_config.should_include_route("/") is True


def test_empty_include_patterns():
    """Test behavior with empty include patterns."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        include_patterns=[],
    )

    # Empty include patterns get converted to ["**"] by default, so everything is included
    assert config.should_include_route("/api/users") is True
    assert config.should_include_route("/any/path") is True
    assert config.include_patterns == ["**"]


def test_pattern_edge_cases():
    """Test edge cases in pattern matching."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        include_patterns=["/**", "/exact/path"],
        exclude_patterns=["/exact/path/excluded"],
    )

    assert config.should_include_route("/") is True
    assert config.should_include_route("/exact/path") is True
    assert config.should_include_route("/exact/path/excluded") is False
    assert config.should_include_route("/any/deep/nested/path") is True


def test_mutable_defaults_isolation():
    """Test that mutable default arguments are properly isolated between instances."""
    config1 = OpenAPIConfig(title="API 1", version="1.0.0")
    config2 = OpenAPIConfig(title="API 2", version="1.0.0")

    # Modify one config's patterns
    config1.include_patterns.append("/custom/**")
    config1.security_schemes["custom_auth"] = {"type": "apiKey"}

    # Check that the other config is not affected
    assert "/custom/**" not in config2.include_patterns
    assert "custom_auth" not in config2.security_schemes
    assert config2.include_patterns == ["**"]
    assert config2.security_schemes == {}


@pytest.mark.parametrize("docstring_style", ["auto", "google", "sphinx", "numpy"])
def test_valid_docstring_styles(docstring_style: str):
    """Test that valid docstring styles are accepted."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        docstring_style=docstring_style,
    )

    assert config.docstring_style == docstring_style


@pytest.mark.parametrize("inference_depth", ["basic", "medium", "deep"])
def test_valid_inference_depths(inference_depth: str):
    """Test that valid inference depths are accepted."""
    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        inference_depth=inference_depth,
    )

    assert config.inference_depth == inference_depth


def test_copy_behavior_of_provided_collections():
    """Test that provided collections are referenced, not copied."""
    original_patterns = ["/api/**"]
    original_security = {"auth": {"type": "bearer"}}
    original_servers = [{"url": "https://api.example.com"}]

    config = OpenAPIConfig(
        title="Test API",
        version="1.0.0",
        include_patterns=original_patterns,
        security_schemes=original_security,
        servers=original_servers,
    )

    # Modify original collections
    original_patterns.append("/v1/**")
    original_security["new_auth"] = {"type": "apiKey"}
    original_servers.append({"url": "https://test.example.com"})

    # Config is affected because collections are referenced, not copied
    assert len(config.include_patterns) == 2
    assert len(config.security_schemes) == 2
    assert len(config.servers) == 2

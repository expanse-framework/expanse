# Expanse OpenAPI Generator

A comprehensive OpenAPI 3.1 specification generator for the Expanse Python web framework. This module analyzes your router, route handlers, function signatures, docstrings, and even function code to generate detailed and accurate OpenAPI specifications.

## Features

- **Automatic Route Discovery**: Analyzes your Expanse router to discover all routes
- **Function Signature Analysis**: Extracts parameter types, return types, and default values
- **Intelligent Docstring Parsing**: Supports Google, Sphinx, NumPy, and auto-detection styles
- **Advanced Code Inference**: Analyzes function bodies to detect response patterns, status codes, and validation logic
- **Pydantic Integration**: Automatically converts Pydantic models to JSON Schema
- **Schema Generation**: Converts Python types to OpenAPI schemas with examples
- **Multiple Export Formats**: JSON and YAML output support
- **Highly Configurable**: Extensive configuration options for customization

## Quick Start

```python
from expanse.openapi import OpenAPIGenerator, OpenAPIConfig
from expanse.routing.router import Router

# Create your router with routes
router = Router()

# Configure the generator
config = OpenAPIConfig(
    title="My API",
    version="1.0.0",
    description="A sample API built with Expanse"
)

# Generate OpenAPI specification
generator = OpenAPIGenerator(router, config)
spec = generator.generate()

# Export to files
generator.export_json("api-spec.json")
generator.export_yaml("api-spec.yaml")
```

## Installation

The OpenAPI generator is included with Expanse. For YAML export support, install PyYAML:

```bash
pip install pyyaml
```

## Configuration

### Basic Configuration

```python
config = OpenAPIConfig(
    title="My API",           # Required: API title
    version="1.0.0",          # Required: API version
    description="API description",  # Optional: API description
)
```

### Advanced Configuration

```python
config = OpenAPIConfig(
    title="Advanced API",
    version="2.1.0",
    description="Comprehensive API documentation",

    # Route filtering
    include_patterns=["/api/**", "/v1/**"],
    exclude_patterns=["/internal/**", "/debug/**"],
    include_internal_routes=False,

    # Documentation parsing
    docstring_style="google",  # "google", "sphinx", "numpy", "auto"

    # Code analysis depth
    inference_depth="deep",    # "basic", "medium", "deep"

    # Schema generation
    generate_examples=True,

    # Security schemes
    security_schemes={
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    },

    # Server information
    servers=[
        {
            "url": "https://api.example.com/v1",
            "description": "Production server"
        }
    ],

    # API metadata
    contact={
        "name": "API Support",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)
```

## Writing Documentation-Friendly Code

### Route Handlers with Comprehensive Docstrings

```python
from pydantic import BaseModel
from expanse.http.request import Request
from expanse.http.response import Response

class UserCreateModel(BaseModel):
    name: str
    email: str
    age: int | None = None

class UserResponseModel(BaseModel):
    id: int
    name: str
    email: str
    age: int | None = None

async def create_user(request: Request, user_data: UserCreateModel) -> Response:
    """
    Create a new user account.

    This endpoint creates a new user with the provided information.
    Email addresses must be unique across the system.

    Args:
        request: The HTTP request object
        user_data: User creation data with name and email

    Returns:
        The created user object with generated ID

    Raises:
        HTTPException: 400 if validation fails
        HTTPException: 409 if email already exists

    Example:
        POST /users

        Request body:
        {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }

        Response (201):
        {
            "id": 123,
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
    """
    # Validation happens automatically with Pydantic
    if user_data.email == "taken@example.com":
        raise HTTPException(409, "Email already exists")

    # Create user logic here
    new_user = UserResponseModel(
        id=123,
        name=user_data.name,
        email=user_data.email,
        age=user_data.age
    )

    return Response(new_user.model_dump(), status_code=201)
```

### Path Parameters

```python
async def get_user(request: Request, user_id: int) -> Response:
    """
    Retrieve a user by ID.

    Args:
        request: The HTTP request object
        user_id: The unique identifier of the user

    Returns:
        User object if found

    Raises:
        HTTPException: 404 if user not found
    """
    if user_id <= 0:
        raise HTTPException(400, "Invalid user ID")

    # User lookup logic
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    return Response(user.model_dump())
```

### Query Parameters

```python
async def list_users(
    request: Request,
    page: int = 1,
    limit: int = 10,
    search: str | None = None
) -> Response:
    """
    List users with pagination and search.

    Args:
        request: The HTTP request object
        page: Page number (1-based)
        limit: Items per page (max 100)
        search: Optional search term for filtering

    Returns:
        Paginated list of users
    """
    # Implementation here
    pass
```

## Docstring Styles

### Google Style (Recommended)

```python
def example_function(param1: str, param2: int = 10) -> dict:
    """
    Brief description of the function.

    Longer description explaining what the function does,
    how it works, and any important details.

    Args:
        param1: Description of the first parameter
        param2: Description of the second parameter with default

    Returns:
        Description of what the function returns

    Raises:
        ValueError: When param1 is invalid
        HTTPException: 404 when resource not found

    Example:
        result = example_function("test", 20)
        print(result)
    """
```

### Sphinx Style

```python
def example_function(param1: str, param2: int = 10) -> dict:
    """
    Brief description of the function.

    Longer description explaining the function's purpose.

    :param param1: Description of first parameter
    :param param2: Description of second parameter
    :returns: Description of return value
    :raises ValueError: When param1 is invalid
    :raises HTTPException: 404 when not found
    """
```

### NumPy Style

```python
def example_function(param1: str, param2: int = 10) -> dict:
    """
    Brief description of the function.

    Longer description explaining the function.

    Parameters
    ----------
    param1 : str
        Description of first parameter
    param2 : int, optional
        Description of second parameter (default is 10)

    Returns
    -------
    dict
        Description of return value

    Raises
    ------
    ValueError
        When param1 is invalid
    HTTPException
        404 when resource not found
    """
```

## Code Inference Features

The generator can analyze your function code to automatically detect:

### Response Patterns

```python
async def get_data(request: Request) -> Response:
    """Get some data."""
    if condition:
        return Response({"data": "success"}, status_code=200)
    else:
        return Response({"error": "failed"}, status_code=400)
    # Generator automatically detects both 200 and 400 responses
```

### Exception Handling

```python
async def create_item(request: Request) -> Response:
    """Create an item."""
    if not valid_input:
        raise HTTPException(422, "Validation failed")

    if duplicate_exists:
        raise HTTPException(409, "Item already exists")

    return Response({"id": 123}, status_code=201)
    # Generator detects 201, 422, and 409 responses
```

### Model Validation

```python
async def update_user(request: Request, user_data: UserModel) -> Response:
    """Update user data."""
    user_data.validate()  # Detected as validation
    # Generator infers request body schema from UserModel
    return Response(user_data.model_dump())
```

## API Reference

### OpenAPIConfig

Configuration class for the OpenAPI generator.

**Parameters:**
- `title` (str): API title (required)
- `version` (str): API version (required)
- `openapi_version` (str): OpenAPI spec version (default: "3.1.0")
- `description` (str | None): API description
- `include_patterns` (list[str]): Route patterns to include (default: ["**"])
- `exclude_patterns` (list[str]): Route patterns to exclude (default: [])
- `docstring_style` (str): Docstring parsing style (default: "auto")
- `include_internal_routes` (bool): Include internal routes (default: False)
- `inference_depth` (str): Code analysis depth (default: "deep")
- `generate_examples` (bool): Generate example data (default: True)
- `security_schemes` (dict): Security scheme definitions
- `servers` (list[dict]): Server information
- `tags` (list[dict]): Tag definitions
- `contact` (dict): Contact information
- `license_info` (dict): License information
- `terms_of_service` (str): Terms of service URL

### OpenAPIGenerator

Main class for generating OpenAPI specifications.

**Methods:**

#### `__init__(router: Router, config: OpenAPIConfig)`
Initialize the generator with a router and configuration.

#### `generate() -> dict[str, Any]`
Generate the complete OpenAPI specification as a dictionary.

#### `export_json(file_path: str, indent: int | None = 2) -> None`
Export specification to a JSON file.

#### `export_yaml(file_path: str) -> None`
Export specification to a YAML file (requires PyYAML).

#### `to_json(indent: int | None = 2) -> str`
Get specification as JSON string.

#### `to_yaml() -> str`
Get specification as YAML string.

## Advanced Usage

### Custom Schema Processing

```python
from expanse.openapi.analyzers import SchemaGenerator

generator = OpenAPIGenerator(router, config)

# Access internal components for customization
schema_gen = generator.schema_generator

# Generate schema for custom type
custom_schema = schema_gen.generate_schema(MyCustomType)
```

### Route Filtering

```python
config = OpenAPIConfig(
    title="Filtered API",
    version="1.0.0",
    # Only include API routes
    include_patterns=["/api/**"],
    # Exclude admin and internal routes
    exclude_patterns=["/api/admin/**", "/internal/**"],
    # Don't include health checks and metrics
    include_internal_routes=False
)
```

### Analysis Depth Control

```python
config = OpenAPIConfig(
    title="My API",
    version="1.0.0",
    # Control how deep the code analysis goes
    inference_depth="medium"  # "basic", "medium", "deep"
)
```

- **basic**: Only function signatures and docstrings
- **medium**: Includes simple code pattern detection
- **deep**: Full AST analysis with advanced inference

## Best Practices

1. **Use Type Hints**: Always provide type annotations for parameters and return values
2. **Write Comprehensive Docstrings**: Include parameter descriptions and examples
3. **Use Pydantic Models**: For request/response bodies, use Pydantic models for automatic schema generation
4. **Handle Errors Explicitly**: Use HTTPException with specific status codes and messages
5. **Provide Examples**: Include example requests/responses in docstrings
6. **Tag Your Routes**: Use meaningful tags to group related operations
7. **Document Edge Cases**: Describe error conditions and special behaviors

## Troubleshooting

### Common Issues

**Schema generation fails for custom types:**
- Ensure your custom classes have proper type annotations
- Consider using Pydantic models for complex data structures

**Missing docstring information:**
- Check that your docstring style matches the configured style
- Use consistent formatting in your docstrings

**Routes not appearing in output:**
- Check include/exclude patterns in configuration
- Verify that routes are properly registered in the router

**Code inference not working:**
- Ensure function source code is available (not in compiled modules)
- Check that inference_depth is set appropriately

### Debug Mode

Enable debug information by examining the generated patterns:

```python
from expanse.openapi.analyzers import CodeInferenceEngine

engine = CodeInferenceEngine(config)
patterns = engine.analyze_function_code(your_function)

for pattern in patterns:
    print(f"Pattern: {pattern.pattern_type}, Confidence: {pattern.confidence}")
    print(f"Data: {pattern.data}")
```

## Contributing

The OpenAPI generator is designed to be extensible. You can:

1. Add custom analyzers for specific patterns
2. Extend schema generation for custom types
3. Add support for additional docstring formats
4. Improve code inference capabilities

See the analyzer classes in `expanse.openapi.analyzers` for extension points.

## License

This module is part of the Expanse framework and follows the same license terms.

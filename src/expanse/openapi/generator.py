import inspect
import json
import sys

from typing import Any
from typing import Union
from typing import get_args
from typing import get_origin
from typing import get_type_hints

from pydantic import BaseModel


# Handle UnionType for Python 3.10+
if sys.version_info >= (3, 10):
    import types

    UnionType = types.UnionType
else:
    UnionType = type(None)  # Fallback that will never match

from expanse.contracts.routing.router import Router
from expanse.openapi.analyzers.code_inference import CodeInferenceEngine
from expanse.openapi.analyzers.docstring_parser import DocstringParser
from expanse.openapi.analyzers.function_analyzer import FunctionAnalyzer
from expanse.openapi.analyzers.function_analyzer import FunctionSignature
from expanse.openapi.analyzers.route_analyzer import RouteAnalyzer
from expanse.openapi.analyzers.schema_generator import SchemaGenerator
from expanse.openapi.config import OpenAPIConfig
from expanse.openapi.document import OpenAPIDocument
from expanse.openapi.document import Operation
from expanse.routing.route import Route


class OpenAPIGenerator:
    """Main OpenAPI specification generator."""

    def __init__(self, router: Router, config: OpenAPIConfig) -> None:
        """
        Initialize OpenAPI generator.

        Args:
            router: The router instance to analyze
            config: Configuration for OpenAPI generation
        """
        self.router = router
        self.config = config

        # Initialize analyzers
        self.route_analyzer = RouteAnalyzer(config)
        self.schema_generator = SchemaGenerator(config)
        self.function_analyzer = FunctionAnalyzer(config, self.schema_generator)
        self.docstring_parser = DocstringParser(config)
        self.code_inference = CodeInferenceEngine(config)

        # Initialize document
        self.document = OpenAPIDocument(config)

    def generate(self) -> dict[str, Any]:
        """
        Generate OpenAPI specification from router.

        Returns:
            Complete OpenAPI specification as dictionary
        """
        # Step 1: Analyze all routes
        routes = [
            route for route in self.router.routes if route.path.startswith("/api")
        ]
        route_infos = self.route_analyzer.analyze_routes(routes)

        # Step 2: Process each route
        for route_info in route_infos:
            self._process_route(route_info)

        # Step 3: Add cached schemas to components
        # Step 2: Generate components (schemas from cached generator)
        schemas = self.schema_generator.get_cached_schemas()
        for schema_name, schema in schemas.items():
            self.document.add_schema(schema_name, schema)

        return self.document.to_dict()

    def _process_route(self, route_info) -> None:
        """Process a single route and add to document."""
        # Get the route handler function
        handler_func = self._get_route_handler(route_info.route)
        if not handler_func:
            return

        # Add tags to document
        for tag in route_info.tags:
            self.document.add_tag(tag)

        # Process each HTTP method for this route
        for method in route_info.methods:
            operation = self._create_operation(route_info, method, handler_func)
            if operation:
                self.document.add_path(
                    route_info.get_openapi_path(), method.lower(), operation.to_dict()
                )

    def _create_operation(
        self, route_info, method: str, handler_func
    ) -> Operation | None:
        """Create an OpenAPI operation from route and handler information."""
        operation = Operation(
            method=method,
            path=route_info.path,
            operation_id=route_info.get_operation_id(method),
        )

        # Set tags
        if route_info.tags:
            operation.tags = route_info.tags

        # Analyze function signature
        signature = self.function_analyzer.analyze_function(handler_func)

        # Discover and generate Pydantic model schemas from the function
        # Also store resolved return type for later use
        resolved_return_type = self._discover_and_generate_pydantic_schemas(
            handler_func, signature
        )

        # Parse docstring
        docstring_info = self.docstring_parser.parse_docstring(handler_func)

        # Perform code inference
        code_patterns = []
        if self.config.inference_depth != "basic":
            try:
                code_patterns = self.code_inference.analyze_function_code(handler_func)
            except Exception:
                # Code inference failed, continue without it
                pass

        # Set operation summary and description
        if docstring_info.summary:
            operation.summary = docstring_info.summary

        if docstring_info.description:
            operation.description = docstring_info.description

        # Set deprecated flag
        if docstring_info.deprecated:
            operation.deprecated = True

        # Process parameters
        self._add_parameters_to_operation(
            operation, route_info, signature, docstring_info
        )

        # Process request body
        self._add_request_body_to_operation(operation, signature, docstring_info)

        # Process responses
        self._add_responses_to_operation(
            operation, signature, docstring_info, code_patterns, resolved_return_type
        )

        return operation

    def _add_parameters_to_operation(
        self, operation: Operation, route_info, signature, docstring_info
    ) -> None:
        """Add parameters to operation."""
        param_descriptions = docstring_info.parameters

        # Add path parameters
        for path_param in route_info.path_parameters:
            # Try to find corresponding function parameter for type info
            func_param = self._find_function_parameter(signature, path_param["name"])

            if func_param:
                schema = self._get_parameter_schema(func_param)
            else:
                schema = path_param["schema"]

            description = param_descriptions.get(path_param["name"])

            operation.add_parameter(
                name=path_param["name"],
                param_in="path",
                schema=schema,
                required=True,
                description=description,
            )

        # Add query parameters from function signature
        query_params = signature.get_query_parameters()
        for param in query_params:
            schema = self._get_parameter_schema(param)
            description = param_descriptions.get(param.name)

            operation.add_parameter(
                name=param.name,
                param_in="query",
                schema=schema,
                required=param.is_required,
                description=description,
            )

    def _add_request_body_to_operation(
        self, operation: Operation, signature: FunctionSignature, docstring_info
    ) -> None:
        """Add request body to operation if applicable."""
        body_params = signature.get_body_parameters()

        if body_params:
            request_body_schema = self.schema_generator.generate_request_body_schema(
                body_params
            )

            if request_body_schema:
                description = "Request body"

                # Try to get description from docstring
                if len(body_params) == 1:
                    param_desc = docstring_info.parameters.get(body_params[0].name)
                    if param_desc:
                        description = param_desc

                operation.set_request_body(
                    content=request_body_schema["content"],
                    description=description,
                    required=request_body_schema.get("required", True),
                )

    def _add_responses_to_operation(
        self,
        operation: Operation,
        signature,
        docstring_info,
        code_patterns,
        resolved_return_type=None,
    ) -> None:
        """Add responses to operation."""
        # Start with responses from code inference
        inferred_responses = {}
        if code_patterns:
            inferred_responses = self.code_inference.infer_response_schemas(
                code_patterns
            )

        # Get status codes from docstring
        docstring_status_codes = self.docstring_parser.extract_http_status_codes(
            docstring_info
        )

        # Merge responses
        all_responses = {**inferred_responses, **docstring_status_codes}

        # If no responses found, add default success response
        if not all_responses:
            all_responses["200"] = "Success"

        # Process each response
        for status_code, response_info in all_responses.items():
            if isinstance(response_info, str):
                # Simple string description
                operation.add_response(status_code, response_info)
            else:
                # Complex response with content
                description = response_info.get("description", "Response")
                content = response_info.get("content")
                headers = response_info.get("headers")

                operation.add_response(
                    status_code=status_code,
                    description=description,
                    content=content,
                    headers=headers,
                )

        # Add success response based on return type if not already present
        if not any(code.startswith("2") for code in all_responses):
            # Use resolved return type if available, otherwise fall back to signature
            if resolved_return_type:
                return_schema = self.schema_generator.generate_schema(
                    resolved_return_type
                )
            else:
                return_schema = self._get_return_type_schema(signature)
            if return_schema:
                content = {"application/json": {"schema": return_schema}}

                # Add example if configured
                if self.config.generate_examples:
                    example = self.schema_generator.generate_example_data(return_schema)
                    if example is not None:
                        content["application/json"]["example"] = example

                operation.add_response(
                    status_code="200",
                    description=docstring_info.returns or "Success",
                    content=content,
                )
            else:
                operation.add_response("200", docstring_info.returns or "Success")

    def _get_route_handler(self, route: Route) -> Any:
        """Extract handler function from route."""
        if isinstance(route.endpoint, tuple):
            return getattr(route.endpoint[0], route.endpoint[1])

        return route.endpoint

    def _find_function_parameter(self, signature, param_name: str):
        """Find a function parameter by name."""
        for param in signature.parameters:
            if param.name == param_name:
                return param
        return None

    def _get_parameter_schema(self, param) -> dict[str, Any]:
        """
        Get OpenAPI schema for a parameter, ensuring Pydantic models are cached.

        Args:
            param: ParameterInfo object

        Returns:
            OpenAPI schema for the parameter
        """
        # For Pydantic models, ensure they're properly generated and cached
        annotation = param.annotation

        # Handle Pydantic models directly
        try:
            if hasattr(annotation, "__module__") and hasattr(annotation, "__name__"):
                # Check if it's a class that might be a Pydantic model
                if hasattr(annotation, "model_json_schema"):
                    # This is likely a Pydantic model
                    self.schema_generator.generate_pydantic_schema(annotation)
        except (TypeError, AttributeError):
            pass

        # Handle Union types containing Pydantic models
        from typing import Union
        from typing import get_args
        from typing import get_origin

        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            for arg in args:
                if arg is not type(None):  # Skip None in Optional types
                    try:
                        if hasattr(arg, "model_json_schema"):
                            self.schema_generator.generate_pydantic_schema(arg)
                    except (TypeError, AttributeError):
                        pass

        return param.get_openapi_type()

    def _discover_and_generate_pydantic_schemas(
        self, func, signature: FunctionSignature
    ) -> Any:
        """
        Discover Pydantic models in function signature and generate their schemas.

        Args:
            func: The function to analyze
            signature: Analyzed function signature

        Returns:
            Resolved return type if available, None otherwise
        """
        resolved_return_type = None
        # Use get_type_hints to resolve string annotations back to actual classes
        try:
            type_hints = get_type_hints(func)

            # Process parameters
            for param_name, param_type in type_hints.items():
                if param_name in ["self", "cls"]:
                    continue
                if param_name == "return":
                    # Handle return type
                    resolved_return_type = param_type
                    self._generate_schemas_for_annotation(param_type)
                else:
                    # Handle parameter type
                    self._generate_schemas_for_annotation(param_type)

        except Exception:
            # If we can't resolve type hints, fall back to string-based discovery
            self._discover_pydantic_from_string_annotations(signature)

        return resolved_return_type

    def _generate_schemas_for_annotation(self, annotation) -> None:
        """Generate schemas for a type annotation recursively."""
        if annotation is None or annotation is type(None):
            return

        # Handle Pydantic models directly
        try:
            if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
                self.schema_generator.generate_pydantic_schema(annotation)
                return
        except (TypeError, AttributeError):
            pass

        # Handle Union types - both typing.Union and types.UnionType
        origin = get_origin(annotation)
        if origin is Union or (
            sys.version_info >= (3, 10) and isinstance(annotation, UnionType)
        ):
            args = get_args(annotation)
            for arg in args:
                if arg is not type(None):  # Skip None in Optional types
                    self._generate_schemas_for_annotation(arg)
            return

        # Handle generic types
        if origin is not None:
            args = get_args(annotation)
            for arg in args:
                self._generate_schemas_for_annotation(arg)

    def _discover_pydantic_from_string_annotations(
        self, signature: FunctionSignature
    ) -> None:
        """Fallback method to discover Pydantic models from string annotations."""
        # This is a best-effort approach for string annotations
        for param in signature.parameters:
            annotation = param.annotation
            if isinstance(annotation, str):
                # Look for common Pydantic model naming patterns
                if (
                    annotation.endswith("Model")
                    or annotation.endswith("Request")
                    or annotation.endswith("Response")
                    or annotation.endswith("Schema")
                ):
                    # Create a placeholder schema entry to prevent missing references
                    # The actual schema will need to be provided by other means
                    pass

    def _get_return_type_schema(self, signature) -> dict[str, Any] | None:
        """Get OpenAPI schema for function return type."""
        if signature.return_info.annotation:
            return self.schema_generator.generate_schema(
                signature.return_info.annotation
            )
        return None

    def _get_return_type_schema_for_func(self, func) -> dict[str, Any] | None:
        """Get OpenAPI schema for function return type using resolved type hints."""
        try:
            type_hints = get_type_hints(func)
            if "return" in type_hints:
                return_type = type_hints["return"]
                return self.schema_generator.generate_schema(return_type)
        except Exception:
            pass
        return None

    def export_json(self, file_path: str, indent: int | None = 2) -> None:
        """
        Export OpenAPI specification to JSON file.

        Args:
            file_path: Path to save the JSON file
            indent: JSON indentation (None for compact)
        """
        spec = self.generate()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=indent, ensure_ascii=False)

    def export_yaml(self, file_path: str) -> None:
        """
        Export OpenAPI specification to YAML file.

        Args:
            file_path: Path to save the YAML file
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML export. Install with: pip install pyyaml"
            )

        spec = self.generate()
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False)

    def to_json(self, indent: int | None = 2) -> str:
        """
        Get OpenAPI specification as JSON string.

        Args:
            indent: JSON indentation (None for compact)

        Returns:
            JSON string representation
        """
        spec = self.generate()
        return json.dumps(spec, indent=indent, ensure_ascii=False)

    def to_yaml(self) -> str:
        """
        Get OpenAPI specification as YAML string.

        Returns:
            YAML string representation
        """
        return self.document.to_yaml()

    def add_custom_analyzer(self, analyzer) -> None:
        """
        Add a custom analyzer to the generation process.

        Args:
            analyzer: Custom analyzer instance
        """
        # This would allow extending the generator with custom analysis
        # Implementation depends on defining an analyzer interface

    def add_schema_processor(self, processor) -> None:
        """
        Add a custom schema processor.

        Args:
            processor: Custom schema processor
        """
        # This would allow custom schema transformations

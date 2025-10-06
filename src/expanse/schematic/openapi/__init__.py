"""
OpenAPI 3.1 Specification Classes

This module provides Python classes that represent the OpenAPI 3.1 specification objects.
All classes include proper typing and methods for serialization to dictionary format.
"""

from expanse.schematic.openapi.callback import Callback
from expanse.schematic.openapi.components import Components
from expanse.schematic.openapi.discriminator import Discriminator
from expanse.schematic.openapi.example import Example
from expanse.schematic.openapi.header import Header
from expanse.schematic.openapi.info import Contact
from expanse.schematic.openapi.info import Info
from expanse.schematic.openapi.info import License
from expanse.schematic.openapi.link import Link
from expanse.schematic.openapi.media_type import Encoding
from expanse.schematic.openapi.media_type import MediaType
from expanse.schematic.openapi.openapi import OpenAPI
from expanse.schematic.openapi.operation import Operation
from expanse.schematic.openapi.parameter import Parameter
from expanse.schematic.openapi.path_item import PathItem
from expanse.schematic.openapi.paths import Paths
from expanse.schematic.openapi.reference import Reference
from expanse.schematic.openapi.request_body import RequestBody
from expanse.schematic.openapi.response import Response
from expanse.schematic.openapi.responses import Responses
from expanse.schematic.openapi.schema import Schema
from expanse.schematic.openapi.security_requirement import SecurityRequirement
from expanse.schematic.openapi.security_scheme import OAuthFlow
from expanse.schematic.openapi.security_scheme import OAuthFlows
from expanse.schematic.openapi.security_scheme import SecurityScheme
from expanse.schematic.openapi.server import Server
from expanse.schematic.openapi.server import ServerVariable
from expanse.schematic.openapi.tag import ExternalDocumentation
from expanse.schematic.openapi.tag import Tag
from expanse.schematic.openapi.xml import XML


__all__ = [
    # Core OpenAPI Document
    "OpenAPI",
    "Info",
    "Contact",
    "License",
    "Server",
    "ServerVariable",
    "Paths",
    "PathItem",
    "Operation",
    "ExternalDocumentation",
    "Parameter",
    "RequestBody",
    "MediaType",
    "Encoding",
    "Responses",
    "Response",
    "Callback",
    "Example",
    "Link",
    "Header",
    "Tag",
    "Reference",
    "Schema",
    "Discriminator",
    "XML",
    "Components",
    "SecurityScheme",
    "OAuthFlows",
    "OAuthFlow",
    "SecurityRequirement",
]

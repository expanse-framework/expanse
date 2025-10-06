from __future__ import annotations

from typing import Any


class Discriminator:
    """
    When request bodies or response payloads may be one of a number of different schemas,
    a discriminator object can be used to aid in serialization, deserialization, and validation.
    The discriminator is a specific object in a schema which is used to inform the consumer
    of the document of an alternative schema based on the value associated with it.

    When using the discriminator, inline schemas will not be considered.
    """

    def __init__(self, property_name: str) -> None:
        """
        Initialize a Discriminator object.

        Args:
            property_name: The name of the property in the payload that will hold
                          the discriminator value.
        """
        self.property_name: str = property_name
        self.mapping: dict[str, str] = {}

    def add_mapping(self, value: str, schema_ref: str) -> "Discriminator":
        """
        Add a mapping between payload values and schema names or references.

        Args:
            value: The discriminator value from the payload
            schema_ref: The schema name or reference to map to

        Returns:
            Self for method chaining
        """
        self.mapping[value] = schema_ref
        return self

    def set_mapping(self, mapping: dict[str, str]) -> "Discriminator":
        """
        Set the mappings between payload values and schema names or references.

        Args:
            mapping: An object to hold mappings between payload values and schema names or references.

        Returns:
            Self for method chaining
        """
        self.mapping = mapping
        return self

    def remove_mapping(self, value: str) -> "Discriminator":
        """
        Remove a mapping.

        Args:
            value: The discriminator value to remove from mapping

        Returns:
            Self for method chaining
        """
        self.mapping.pop(value, None)
        return self

    def get_mapping(self, value: str) -> str | None:
        """
        Get the schema reference for a discriminator value.

        Args:
            value: The discriminator value

        Returns:
            The schema reference if found, None otherwise
        """
        return self.mapping.get(value)

    def clear_mapping(self) -> "Discriminator":
        """
        Clear all mappings.

        Returns:
            Self for method chaining
        """
        self.mapping.clear()
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Discriminator object to a dictionary representation."""
        result: dict[str, Any] = {"propertyName": self.property_name}

        if self.mapping:
            result["mapping"] = self.mapping

        return result

    def __repr__(self) -> str:
        return f"Discriminator(property_name='{self.property_name}', mappings={len(self.mapping)})"

    def __contains__(self, value: str) -> bool:
        """Check if a discriminator value has a mapping."""
        return value in self.mapping

    def __len__(self) -> int:
        """Get the number of mappings."""
        return len(self.mapping)

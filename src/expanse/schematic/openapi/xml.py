from __future__ import annotations

from typing import Any


class XML:
    """
    A metadata object that allows for more fine-tuned XML model definitions.

    When using arrays, XML element names are not inferred (for singular/plural forms)
    and the name property SHOULD be used to add that information.
    """

    def __init__(self) -> None:
        """Initialize an XML object."""
        self.name: str | None = None
        self.namespace: str | None = None
        self.prefix: str | None = None
        self.attribute: bool = False
        self.wrapped: bool = False

    def set_name(self, name: str) -> XML:
        """
        Set the name that replaces the element/attribute used for the described schema property.

        Args:
            name: Replaces the name of the element/attribute used for the described schema property.
                 When defined within items, it will affect the name of the individual XML elements
                 within the list. When defined alongside type being array (outside the items),
                 it will affect the wrapping element and only if wrapped is true.

        Returns:
            Self for method chaining
        """
        self.name = name
        return self

    def set_namespace(self, namespace: str) -> XML:
        """
        Set the URI of the namespace definition.

        Args:
            namespace: The URI of the namespace definition. This MUST be in the form of an absolute URI.

        Returns:
            Self for method chaining
        """
        self.namespace = namespace
        return self

    def set_prefix(self, prefix: str) -> XML:
        """
        Set the prefix to be used for the name.

        Args:
            prefix: The prefix to be used for the name.

        Returns:
            Self for method chaining
        """
        self.prefix = prefix
        return self

    def set_attribute(self, attribute: bool) -> XML:
        """
        Set whether the property definition translates to an attribute instead of an element.

        Args:
            attribute: Declares whether the property definition translates to an attribute
                      instead of an element. Default value is false.

        Returns:
            Self for method chaining
        """
        self.attribute = attribute
        return self

    def set_wrapped(self, wrapped: bool) -> XML:
        """
        Set whether the array is wrapped.

        Args:
            wrapped: MAY be used only for an array definition. Signifies whether the array
                    is wrapped (for example, <books><book/><book/></books>) or unwrapped
                    (<book/><book/>). Default value is false. The definition takes effect
                    only when defined alongside type being array (outside the items).

        Returns:
            Self for method chaining
        """
        self.wrapped = wrapped
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the XML object to a dictionary representation."""
        result: dict[str, Any] = {}

        if self.name is not None:
            result["name"] = self.name

        if self.namespace is not None:
            result["namespace"] = self.namespace

        if self.prefix is not None:
            result["prefix"] = self.prefix

        if self.attribute:
            result["attribute"] = self.attribute

        if self.wrapped:
            result["wrapped"] = self.wrapped

        return result

    def __repr__(self) -> str:
        parts = []
        if self.name:
            parts.append(f"name='{self.name}'")
        if self.namespace:
            parts.append(f"namespace='{self.namespace}'")
        if self.prefix:
            parts.append(f"prefix='{self.prefix}'")
        if self.attribute:
            parts.append("attribute=True")
        if self.wrapped:
            parts.append("wrapped=True")

        if parts:
            return f"XML({', '.join(parts)})"
        else:
            return "XML()"

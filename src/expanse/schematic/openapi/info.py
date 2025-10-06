from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.contact import Contact
    from expanse.schematic.openapi.license import License


class Contact:
    """
    Contact information for the exposed API.
    """

    def __init__(
        self,
        name: str | None = None,
        url: str | None = None,
        email: str | None = None,
    ) -> None:
        """
        Initialize a Contact object.

        Args:
            name: The identifying name of the contact person/organization.
            url: The URL pointing to the contact information. This MUST be in the form of a URL.
            email: The email address of the contact person/organization. This MUST be in the form of an email address.
        """
        self.name: str | None = name
        self.url: str | None = url
        self.email: str | None = email

    def to_dict(self) -> dict[str, Any]:
        """Convert the Contact object to a dictionary representation."""
        result: dict[str, Any] = {}

        if self.name is not None:
            result["name"] = self.name

        if self.url is not None:
            result["url"] = self.url

        if self.email is not None:
            result["email"] = self.email

        return result

    def __repr__(self) -> str:
        return f"Contact(name='{self.name}')"


class License:
    """
    License information for the exposed API.
    """

    def __init__(
        self,
        name: str,
        identifier: str | None = None,
        url: str | None = None,
    ) -> None:
        """
        Initialize a License object.

        Args:
            name: The license name used for the API.
            identifier: An SPDX-Licenses expression for the API. The identifier field is
                       mutually exclusive of the url field.
            url: A URL to the license used for the API. This MUST be in the form of a URL.
                The url field is mutually exclusive of the identifier field.
        """
        if identifier is not None and url is not None:
            raise ValueError("identifier and url fields are mutually exclusive")

        self.name: str = name
        self.identifier: str | None = identifier
        self.url: str | None = url

    def to_dict(self) -> dict[str, Any]:
        """Convert the License object to a dictionary representation."""
        result: dict[str, Any] = {"name": self.name}

        if self.identifier is not None:
            result["identifier"] = self.identifier

        if self.url is not None:
            result["url"] = self.url

        return result

    def __repr__(self) -> str:
        return f"License(name='{self.name}')"


class Info:
    """
    The object provides metadata about the API. The metadata MAY be used by the clients
    if needed, and MAY be presented in editing or documentation generation tools for convenience.
    """

    def __init__(self, title: str, version: str) -> None:
        """
        Initialize an Info object.

        Args:
            title: The title of the API.
            version: The version of the OpenAPI document (which is distinct from the OpenAPI
                    Specification version or the API implementation version).
        """
        self.title: str = title
        self.version: str = version
        self.summary: str | None = None
        self.description: str | None = None
        self.terms_of_service: str | None = None
        self.contact: Contact | None = None
        self.license: License | None = None

    def set_summary(self, summary: str) -> "Info":
        """
        Set a short summary of the API.

        Args:
            summary: A short summary of the API.

        Returns:
            Self for method chaining
        """
        self.summary = summary
        return self

    def set_description(self, description: str) -> "Info":
        """
        Set a description of the API.

        Args:
            description: A description of the API. CommonMark syntax MAY be used for rich text representation.

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def set_terms_of_service(self, terms_of_service: str) -> "Info":
        """
        Set a URL to the Terms of Service for the API.

        Args:
            terms_of_service: A URL to the Terms of Service for the API. This MUST be in the form of a URL.

        Returns:
            Self for method chaining
        """
        self.terms_of_service = terms_of_service
        return self

    def set_contact(self, contact: Contact) -> "Info":
        """
        Set the contact information for the exposed API.

        Args:
            contact: The contact information for the exposed API.

        Returns:
            Self for method chaining
        """
        self.contact = contact
        return self

    def set_license(self, license: License) -> "Info":
        """
        Set the license information for the exposed API.

        Args:
            license: The license information for the exposed API.

        Returns:
            Self for method chaining
        """
        self.license = license
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Info object to a dictionary representation."""
        result: dict[str, Any] = {
            "title": self.title,
            "version": self.version,
        }

        if self.summary is not None:
            result["summary"] = self.summary

        if self.description is not None:
            result["description"] = self.description

        if self.terms_of_service is not None:
            result["termsOfService"] = self.terms_of_service

        if self.contact is not None:
            result["contact"] = self.contact.to_dict()

        if self.license is not None:
            result["license"] = self.license.to_dict()

        return result

    def __repr__(self) -> str:
        return f"Info(title='{self.title}', version='{self.version}')"

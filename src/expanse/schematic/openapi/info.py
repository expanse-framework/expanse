from __future__ import annotations

from typing import Any


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
        self.name: str | None = name
        self.url: str | None = url
        self.email: str | None = email

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if self.name is not None:
            result["name"] = self.name

        if self.url is not None:
            result["url"] = self.url

        if self.email is not None:
            result["email"] = self.email

        return result


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
        if identifier is not None and url is not None:
            raise ValueError("identifier and url fields are mutually exclusive")

        self.name: str = name
        self.identifier: str | None = identifier
        self.url: str | None = url

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name}

        if self.identifier is not None:
            result["identifier"] = self.identifier

        if self.url is not None:
            result["url"] = self.url

        return result


class Info:
    def __init__(self, title: str, version: str) -> None:
        self.title: str = title
        self.version: str = version
        self.summary: str | None = None
        self.description: str | None = None
        self.terms_of_service: str | None = None
        self.contact: Contact | None = None
        self.license: License | None = None

    def set_summary(self, summary: str) -> Info:
        self.summary = summary
        return self

    def set_description(self, description: str) -> Info:
        self.description = description
        return self

    def set_terms_of_service(self, terms_of_service: str) -> Info:
        self.terms_of_service = terms_of_service
        return self

    def set_contact(self, contact: Contact) -> Info:
        self.contact = contact
        return self

    def set_license(self, license: License) -> Info:
        self.license = license
        return self

    def to_dict(self) -> dict[str, Any]:
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

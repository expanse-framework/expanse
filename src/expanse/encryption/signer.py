import hmac

from typing import TYPE_CHECKING
from typing import override

from expanse.contracts.encryption.signer import Signer as SignerContract
from expanse.encryption.key_generator import KeyGenerator
from expanse.support.secret import Secret


if TYPE_CHECKING:
    from expanse.encryption.key_chain import KeyChain


class Signer(SignerContract):
    def __init__(
        self,
        key_chain: "KeyChain",
        salt: Secret[bytes] | bytes | None = None,
        algorithm: str = "sha256",
    ) -> None:
        self._key_chain: KeyChain = key_chain
        self._salt: Secret[bytes] | None = Secret[bytes].wrap(salt) if salt else None
        self._algorithm: str = algorithm

    @override
    def sign(
        self,
        data: bytes | str,
        purpose: bytes | str | None = None,
    ) -> bytes:
        key = KeyGenerator.generate_key(
            self._key_chain.latest, salt=self._salt, purpose=purpose
        )

        if isinstance(data, str):
            data = data.encode()

        return hmac.digest(key.value.reveal(), data, self._algorithm)

    @override
    def verify(
        self, data: bytes, signature: bytes, purpose: bytes | str | None = None
    ) -> bool:
        # Try all keys in case of key rotation
        for raw_key in self._key_chain:
            key = KeyGenerator.generate_key(raw_key, salt=self._salt, purpose=purpose)
            expected_signature = hmac.digest(key.value.reveal(), data, self._algorithm)
            if hmac.compare_digest(expected_signature, signature):
                return True

        return False

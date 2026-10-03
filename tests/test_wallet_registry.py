import unittest
from uuid import UUID

from supabase_storage.wallets import PostgresWalletRegistry


class NoDatabaseCalls:
    def connection(self):
        raise AssertionError("Invalid wallet input must be rejected before database access.")


class WalletInputValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = PostgresWalletRegistry(
            NoDatabaseCalls(),
            UUID("2558d070-be78-4888-85e0-fb02975984ec"),
        )

    def test_wallet_registration_requires_public_wallet_metadata(self) -> None:
        for purpose, address in (
            ("investments", "A" * 32),
            ("profits", "short"),
        ):
            with self.subTest(purpose=purpose, address=address):
                with self.assertRaises(ValueError):
                    self.registry.register(
                        purpose=purpose,
                        label="Treasury",
                        network="ethereum-mainnet",
                        asset="USDC",
                        address=address,
                        created_by="080c2dc0-7332-4689-ade9-8a2229b2f4e3",
                    )

        with self.assertRaises(ValueError):
            self.registry.register(
                purpose=["profits"],
                label="Treasury",
                network="ethereum-mainnet",
                asset="USDC",
                address="A" * 32,
                created_by="080c2dc0-7332-4689-ade9-8a2229b2f4e3",
            )

    def test_withdrawal_amount_must_be_positive_plain_decimal(self) -> None:
        for amount in ("0", "-1", "1e3", "1.0000000000000000001", ""):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    self.registry.request_withdrawal(
                        wallet_id="080c2dc0-7332-4689-ade9-8a2229b2f4e3",
                        destination_address="D" * 32,
                        amount=amount,
                        memo=None,
                        requested_by="080c2dc0-7332-4689-ade9-8a2229b2f4e3",
                    )

    def test_withdrawal_rejects_malformed_destination_address(self) -> None:
        with self.assertRaisesRegex(ValueError, "public address"):
            self.registry.request_withdrawal(
                wallet_id="080c2dc0-7332-4689-ade9-8a2229b2f4e3",
                destination_address="not a chain address",
                amount="1.25",
                memo=None,
                requested_by="080c2dc0-7332-4689-ade9-8a2229b2f4e3",
            )


if __name__ == "__main__":
    unittest.main()

from virtual_index_card.security import (
    hash_password,
    hash_token,
    new_token,
    tokens_match,
    verify_password,
)


def test_password_hash_round_trip_uses_unique_salts() -> None:
    salt_a, hash_a = hash_password("a long password")
    salt_b, hash_b = hash_password("a long password")

    assert salt_a != salt_b
    assert hash_a != hash_b
    assert verify_password("a long password", salt_a, hash_a)
    assert not verify_password("wrong password", salt_a, hash_a)
    assert not verify_password("a long password", "not-hex", hash_a)


def test_tokens_are_hashed_and_compared_safely() -> None:
    token = new_token()
    assert hash_token(token) != token
    assert tokens_match(token, token)
    assert not tokens_match(token, new_token())
    assert not tokens_match(None, token)

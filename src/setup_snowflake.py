"""One-time Snowflake key-pair setup. Run from src/:  python setup_snowflake.py

Generates an RSA key pair, saves the private key into .streamlit/secrets.toml (gitignored),
and prints the ONE SQL command to run in a Snowsight worksheet.
"""
import re
import tomllib
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

SECRETS = Path(__file__).parent / ".streamlit" / "secrets.toml"


def main() -> None:
    current = tomllib.loads(SECRETS.read_text(encoding="utf-8")) if SECRETS.exists() else {}
    account = current.get("SNOWFLAKE_ACCOUNT") or input("Account identifier (e.g. ORG-ACCOUNT): ").strip()
    user = current.get("SNOWFLAKE_USER") or input("Snowflake user name: ").strip()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    public_body = "".join(l for l in public_pem.splitlines() if "-----" not in l)

    current.update(SNOWFLAKE_ACCOUNT=account, SNOWFLAKE_USER=user, SNOWFLAKE_PRIVATE_KEY=private_pem)
    current.setdefault("SNOWFLAKE_MODEL", "claude-sonnet-4-5")
    current.pop("SNOWFLAKE_TOKEN", None)  # key-pair auth replaces the access token
    lines = []
    for k, v in current.items():
        lines.append(f'{k} = """{v}"""' if "\n" in v else f'{k} = "{v}"')
    SECRETS.parent.mkdir(exist_ok=True)
    SECRETS.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved private key to {SECRETS}\n")
    print("Run this ONE command in a Snowsight worksheet (role ACCOUNTADMIN):\n")
    print(f"ALTER USER {user} SET RSA_PUBLIC_KEY='{public_body}';\n")
    print("Then test:  python -m eval_system.llm")


if __name__ == "__main__":
    main()

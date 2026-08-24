"""Generate self-signed SSL cert + key in PKCS#1 format for nginx."""
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())

subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IncentiveHouse ERP"),
    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
])
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.now(timezone.utc))
    .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1825))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
            x509.DNSName("erp.example.com"),
        ]),
        critical=False,
    )
    .sign(key, hashes.SHA256(), backend=default_backend())
)

with open("ssl/key_new.pem", "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))

with open("ssl/cert_new.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("Generated ssl/cert_new.pem and ssl/key_new.pem")

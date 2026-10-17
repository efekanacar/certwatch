#!/usr/bin/env python3
"""Standart kütüphane ile TLS sertifikalarını denetler."""

import argparse
import json
import math
import socket
import ssl
import sys
from datetime import datetime, timezone


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Pozitif, sonlu bir sayı girin.")
    return number


def port_number(value):
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("Port 1–65535 arasında olmalıdır.")
    return number


def nonnegative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("Sıfır veya pozitif bir tamsayı girin.")
    return number


def normalize_domain(domain):
    hostname = domain.rstrip(".").encode("idna").decode("ascii").lower()
    labels = hostname.split(".")
    if len(hostname) > 253 or any(
        not label or len(label) > 63 or label.startswith("-")
        or label.endswith("-") or any(
            char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in label
        ) for label in labels
    ):
        raise ValueError("Yalnızca domain adı girin; URL, yol veya port eklemeyin.")
    return hostname


def check_domain(domain, port, timeout, warn_days, context):
    result = {"domain": domain, "port": port, "status": "error",
              "expires_at": None, "days_remaining": None, "message": ""}
    try:
        hostname = normalize_domain(domain)
        with socket.create_connection((hostname, port), timeout=timeout) as connection:
            with context.wrap_socket(connection, server_hostname=hostname) as tls:
                certificate = tls.getpeercert()
        expiration = ssl.cert_time_to_seconds(certificate["notAfter"])
        seconds_remaining = expiration - datetime.now(timezone.utc).timestamp()
        result["expires_at"] = datetime.fromtimestamp(
            expiration, timezone.utc
        ).isoformat().replace("+00:00", "Z")
        result["days_remaining"] = math.floor(seconds_remaining / 86400)
        if seconds_remaining <= 0:
            result.update(status="expired", message="Sertifikanın süresi dolmuş.")
        elif seconds_remaining / 86400 <= warn_days:
            result.update(status="warning", message="Sertifikanın süresi yakında dolacak.")
        else:
            result.update(status="ok", message="Sertifika geçerli.")
    except ssl.SSLCertVerificationError as error:
        result["message"] = "Sertifika doğrulanamadı: " + error.verify_message
    except ssl.SSLError as error:
        result["message"] = "TLS bağlantısı kurulamadı: " + str(error)
    except socket.gaierror:
        result["message"] = "Domain adı çözümlenemedi (DNS hatası)."
    except (TimeoutError, socket.timeout):
        result["message"] = "Bağlantı veya TLS işlemi zaman aşımına uğradı."
    except ConnectionRefusedError:
        result["message"] = "Sunucu bağlantıyı reddetti."
    except OSError as error:
        result["message"] = "Ağ bağlantısı hatası: " + str(error)
    except (ValueError, UnicodeError) as error:
        result["message"] = "Geçersiz domain veya sertifika verisi: " + str(error)
    except KeyError:
        result["message"] = "Sertifikanın geçerlilik bitiş tarihi alınamadı."
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="CertWatch: domainlerin TLS sertifikalarını kontrol eder."
    )
    parser.add_argument("domains", nargs="+", help="Kontrol edilecek domainler")
    parser.add_argument("--port", type=port_number, default=443, help="TLS portu (443)")
    parser.add_argument("--timeout", type=positive_float, default=10,
                        help="Her ağ işlemi için zaman aşımı, saniye (10)")
    parser.add_argument("--warn-days", type=nonnegative_int, default=30,
                        help="Uyarı eşiği, gün (30)")
    parser.add_argument("--json", action="store_true", help="JSON çıktısı üret")
    args = parser.parse_args(argv)
    try:
        context = ssl.create_default_context()
    except (OSError, ssl.SSLError) as error:
        results = [{"domain": domain, "port": args.port, "status": "error",
                    "expires_at": None, "days_remaining": None,
                    "message": "TLS güven deposu yüklenemedi: " + str(error)}
                   for domain in args.domains]
    else:
        results = [check_domain(domain, args.port, args.timeout, args.warn_days, context)
                   for domain in args.domains]
    if args.json:
        print(json.dumps(results, ensure_ascii=True, indent=2))
    else:
        for result in results:
            print("{}:{} [{}]".format(result["domain"], result["port"], result["status"]))
            if result["expires_at"] is not None:
                print("  Bitiş (UTC): {} | Kalan tam gün: {}".format(
                    result["expires_at"], result["days_remaining"]))
            print("  " + result["message"])
    return 0 if all(result["status"] == "ok" for result in results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nİşlem kullanıcı tarafından durduruldu.", file=sys.stderr)
        sys.exit(130)

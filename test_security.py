import requests

def test_security_headers():
    url = "http://127.0.0.1:8000"

    try:
        response = requests.get(url)
        headers = response.headers

        print("\n Vérification des en-têtes de sécurité:")
        print("=" * 50)

        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        }

        for header, expected in security_headers.items():
            actual = headers.get(header)
            if actual == expected:
                print(f" {header}: {actual}")
            else:
                print(f" {header}: {actual} (attendu: {expected})")

        if 'Server' in headers:
            print(f"  Server: {headers['Server']}")
        else:
            print(" Server: masqué")

        if 'X-Powered-By' in headers:
            print(f"  X-Powered-By: {headers['X-Powered-By']}")
        else:
            print(" X-Powered-By: masqué")

    except Exception as e:
        print(f" Erreur: {e}")

def test_csrf_protection():
    print("\n  Vérification CSRF:")
    print("=" * 50)

    try:
        url = "http://127.0.0.1:8000/admin/login/"
        response = requests.get(url)

        if 'csrftoken' in response.cookies:
            print(" Cookie CSRF présent")
        else:
            print(" Cookie CSRF non trouvé")

    except Exception as e:
        print(f" Erreur: {e}")

if __name__ == "__main__":
    print(" TEST DE SÉCURITÉ")
    print("=" * 50)
    test_security_headers()
    test_csrf_protection()
    print("\n Tests terminés")

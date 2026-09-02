"""Envoi d'e-mails par API HTTPS (Brevo) : le SMTP sortant est bloqué sur le
serveur de prod, seul le 443 passe. Aucune dépendance externe (urllib)."""
import json
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

URL = "https://api.brevo.com/v3/smtp/email"


class BrevoAPIBackend(BaseEmailBackend):
    """Poste chaque message sur l'API transactionnelle de Brevo (port 443)."""

    def send_messages(self, email_messages):
        cle = getattr(settings, "BREVO_API_KEY", "")
        if not cle or not email_messages:
            return 0
        envoyes = 0
        for message in email_messages:
            if self._envoyer(message, cle):
                envoyes += 1
        return envoyes

    def _envoyer(self, message, cle):
        nom, adresse = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
        corps = {
            "sender": {"email": adresse, "name": nom or adresse},
            "to": [{"email": a} for a in message.to],
            "subject": message.subject,
            "textContent": message.body or " ",
        }
        for contenu, mime in getattr(message, "alternatives", None) or []:
            if mime == "text/html":
                corps["htmlContent"] = contenu
        if message.reply_to:
            corps["replyTo"] = {"email": parseaddr(message.reply_to[0])[1]}
        if getattr(message, "extra_headers", None):
            corps["headers"] = {k: str(v) for k, v in message.extra_headers.items()}

        requete = urllib.request.Request(
            URL, data=json.dumps(corps).encode("utf-8"), method="POST",
            headers={"api-key": cle, "content-type": "application/json",
                     "accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(requete, timeout=getattr(settings, "EMAIL_TIMEOUT", 15)) as reponse:
                return 200 <= reponse.status < 300
        except Exception:
            if not self.fail_silently:
                raise
            return False

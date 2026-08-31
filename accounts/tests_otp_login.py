"""Parcours de connexion : apprenant direct, personnel via code OTP e-mail."""

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts import otp
from accounts.models import Utilisateur


@override_settings(DEFAULT_FROM_EMAIL='test@bsb.local')
class ConnexionTests(TestCase):
    def setUp(self):
        self.eleve = Utilisateur.objects.create_user(
            username='eleve1', password='motdepasse123', user_type='eleve',
            nom='Traore', prenom='Ali', adresse='Ouaga', email='eleve1@example.com',
        )
        self.staff = Utilisateur.objects.create_user(
            username='daf1', password='motdepasse123', user_type='daf',
            nom='Kabore', prenom='Awa', adresse='Ouaga', email='awa@example.com',
        )

    def test_eleve_connexion_directe(self):
        resp = self.client.post(reverse('accounts:login'), {
            'identifiant': 'eleve1', 'password': 'motdepasse123',
        })
        self.assertRedirects(resp, reverse('courses:redirect_to_dashboard'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn('_auth_user_id', self.client.session)

    def test_email_inexistant_message_generique(self):
        resp = self.client.post(reverse('accounts:login'), {
            'identifiant': 'inconnu@example.com', 'password': 'x',
        })
        self.assertContains(resp, 'Email ou mot de passe incorrect')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_mauvais_mot_de_passe_message_generique(self):
        resp = self.client.post(reverse('accounts:login'), {
            'identifiant': 'awa@example.com', 'password': 'faux',
        })
        self.assertContains(resp, 'Email ou mot de passe incorrect')

    def test_staff_recoit_un_code_et_se_connecte(self):
        resp = self.client.post(reverse('accounts:login'), {
            'identifiant': 'awa@example.com', 'password': 'motdepasse123',
        })
        self.assertRedirects(resp, reverse('accounts:login_otp'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 1)

        code = ''.join(c for c in mail.outbox[0].body if c.isdigit())[:4]
        self.assertEqual(len(code), 4)

        resp = self.client.post(reverse('accounts:login_otp'), {'code': code})
        self.assertRedirects(resp, reverse('courses:redirect_to_dashboard'), fetch_redirect_response=False)
        self.assertEqual(str(self.client.session['_auth_user_id']), str(self.staff.pk))
        self.assertNotIn(otp.CLE_SESSION, self.client.session)

    def test_mauvais_code_refuse(self):
        self.client.post(reverse('accounts:login'), {
            'identifiant': 'awa@example.com', 'password': 'motdepasse123',
        })
        resp = self.client.post(reverse('accounts:login_otp'), {'code': '0000'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(resp, 'incorrect')

    def test_code_expire_refuse(self):
        self.client.post(reverse('accounts:login'), {
            'identifiant': 'awa@example.com', 'password': 'motdepasse123',
        })
        code = ''.join(c for c in mail.outbox[0].body if c.isdigit())[:4]
        session = self.client.session
        donnees = session[otp.CLE_SESSION]
        from django.utils import timezone
        donnees['expire_le'] = (timezone.now() - timezone.timedelta(seconds=1)).isoformat()
        session[otp.CLE_SESSION] = donnees
        session.save()

        resp = self.client.post(reverse('accounts:login_otp'), {'code': code})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(resp, 'expir')

    def test_otp_sans_session_redirige_login(self):
        resp = self.client.get(reverse('accounts:login_otp'))
        self.assertRedirects(resp, reverse('accounts:login'), fetch_redirect_response=False)

    def test_renvoi_respecte_le_delai(self):
        self.client.post(reverse('accounts:login'), {
            'identifiant': 'awa@example.com', 'password': 'motdepasse123',
        })
        resp = self.client.post(reverse('accounts:login_otp_resend'))
        self.assertRedirects(resp, reverse('accounts:login_otp'), fetch_redirect_response=False)
        # Envoi immédiat bloqué par le délai minimum (60 s).
        self.assertEqual(len(mail.outbox), 1)

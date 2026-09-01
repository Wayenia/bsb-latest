"""Séparation de la connexion des comptes d'administration technique.

Ces comptes se connectent par une page dédiée (chemin issu du .env) et sont
refusés sur la page publique ; le DG fait exception (il passe partout).
"""
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import TestCase, override_settings

from accounts import appareil, otp
from accounts.models import Utilisateur

CHEMIN = '/' + settings.ADMIN_LOGIN_PATH


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SeparationLoginAdmin(TestCase):
    def setUp(self):
        self.admin = Utilisateur.objects.create_user(
            username='chef', password='Passe#2026', nom='C', prenom='H',
            email='chef@example.invalid', user_type='admin')
        self.agent = Utilisateur.objects.create_user(
            username='caisse', password='Passe#2026', nom='A', prenom='G',
            email='caisse@example.invalid', user_type='caissier')
        self.dg = Utilisateur.objects.create_user(
            username='patron', password='Passe#2026', nom='D', prenom='G',
            email='dg@example.invalid', user_type='dg')

    # --- Page publique fermée aux admins ---
    def test_admin_refuse_sur_page_publique(self):
        r = self.client.post('/accounts/login',
                             {'identifiant': 'chef', 'password': 'Passe#2026'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 0)

    def test_agent_toujours_accepte_sur_page_publique(self):
        r = self.client.post('/accounts/login',
                             {'identifiant': 'caisse', 'password': 'Passe#2026'})
        self.assertRedirects(r, reverse_lazy_verification(), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)

    # --- Page dédiée réservée aux admins (+ DG) ---
    def test_admin_passe_par_la_page_dediee(self):
        r = self.client.post(CHEMIN, {'identifiant': 'chef', 'password': 'Passe#2026'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(self.client.session.get(otp.CLE_SESSION))

    def test_agent_refuse_sur_page_dediee(self):
        r = self.client.post(CHEMIN, {'identifiant': 'caisse', 'password': 'Passe#2026'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 0)

    def test_dg_passe_partout(self):
        pub = self.client.post('/accounts/login',
                               {'identifiant': 'patron', 'password': 'Passe#2026'})
        self.assertEqual(len(mail.outbox), 1)
        self.client = self.client_class()
        mail.outbox = []
        ded = self.client.post(CHEMIN, {'identifiant': 'patron', 'password': 'Passe#2026'})
        self.assertEqual(ded.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    # --- Délégation par permission ---
    def test_permission_deleguee_bascule_un_agent_en_admin(self):
        perm = Permission.objects.get(codename='acces_administration_technique')
        self.agent.user_permissions.add(perm)
        r = self.client.post('/accounts/login',
                             {'identifiant': 'caisse', 'password': 'Passe#2026'})
        self.assertNotIn('_auth_user_id', self.client.session)

    # --- 2FA admin : pas de dispense d'appareil ---
    def test_admin_ne_pose_pas_le_cookie_appareil(self):
        self.client.post(CHEMIN, {'identifiant': 'chef', 'password': 'Passe#2026'})
        # Forcer un code connu pour valider la 2e étape.
        from django.contrib.auth.hashers import make_password
        session = self.client.session
        donnees = session[otp.CLE_SESSION]
        donnees['code_hache'] = make_password('1234')
        session[otp.CLE_SESSION] = donnees
        session.save()
        self.client.post('/accounts/login/verification', {'code': '1234'})
        self.assertIn('_auth_user_id', self.client.session)
        self.assertNotIn(appareil.COOKIE, self.client.cookies)

    # --- Filtre IP optionnel ---
    @override_settings(ADMIN_LOGIN_IPS=['10.0.0.0/8'])
    def test_ip_hors_plage_donne_404(self):
        r = self.client.get(CHEMIN, REMOTE_ADDR='203.0.113.9')
        self.assertEqual(r.status_code, 404)

    @override_settings(ADMIN_LOGIN_IPS=['10.0.0.0/8'])
    def test_ip_dans_la_plage_donne_200(self):
        r = self.client.get(CHEMIN, REMOTE_ADDR='10.1.2.3')
        self.assertEqual(r.status_code, 200)


def reverse_lazy_verification():
    from django.urls import reverse
    return reverse('accounts:login_otp')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   SESSION_COOKIE_SECURE=False)
class DispenseOtpAdmin(TestCase):
    """Dispense d'OTP réglable de l'espace d'administration (5 h par défaut)."""

    def setUp(self):
        self.admin = Utilisateur.objects.create_user(
            username='chef', password='Passe#2026', nom='C', prenom='H',
            email='chef@example.invalid', user_type='admin')

    def _valider_otp(self):
        from django.contrib.auth.hashers import make_password
        session = self.client.session
        donnees = session[otp.CLE_SESSION]
        donnees['code_hache'] = make_password('1234')
        session[otp.CLE_SESSION] = donnees
        session.save()
        return self.client.post('/accounts/login/verification', {'code': '1234'})

    def test_defaut_cinq_heures(self):
        from accounts import dispense_admin
        self.assertEqual(dispense_admin.minutes_reglees(self.admin),
                         dispense_admin.DEFAUT_MINUTES)

    def test_reglage_du_jour_puis_reset_le_lendemain(self):
        from django.utils import timezone
        from datetime import timedelta
        from accounts import dispense_admin
        self.admin.admin_otp_grace_minutes = 720
        self.admin.admin_otp_grace_jour = timezone.localdate()
        self.assertEqual(dispense_admin.minutes_reglees(self.admin), 720)
        self.admin.admin_otp_grace_jour = timezone.localdate() - timedelta(days=1)
        self.assertEqual(dispense_admin.minutes_reglees(self.admin),
                         dispense_admin.DEFAUT_MINUTES)

    def test_reglage_plafonne_a_24h(self):
        self.client.force_login(self.admin)
        self.client.post('/accounts/mon-compte/dispense', {'minutes': '5000'})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.admin_otp_grace_minutes, 1440)

    def test_dispense_evite_l_otp_a_la_connexion_suivante(self):
        from accounts import dispense_admin
        chemin = CHEMIN
        # 1re connexion : OTP puis dispense posée.
        self.client.post(chemin, {'identifiant': 'chef', 'password': 'Passe#2026'})
        self._valider_otp()
        self.assertIn(dispense_admin.COOKIE, self.client.cookies)
        jeton = self.client.cookies[dispense_admin.COOKIE].value
        # 2e connexion avec la dispense : aucun code envoyé.
        c2 = self.client_class()
        c2.cookies[dispense_admin.COOKIE] = jeton
        mail.outbox = []
        c2.post(chemin, {'identifiant': 'chef', 'password': 'Passe#2026'})
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn('_auth_user_id', c2.session)

    def test_agent_n_a_pas_le_reglage(self):
        agent = Utilisateur.objects.create_user(
            username='caisse', password='Passe#2026', nom='A', prenom='G',
            email='caisse@example.invalid', user_type='caissier')
        self.client.force_login(agent)
        page = self.client.get('/accounts/mon-compte')
        self.assertNotContains(page, "Connexion à l'administration")

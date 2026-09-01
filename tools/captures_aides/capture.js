const puppeteer = require('puppeteer-core');
const fs = require('fs');
const S = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const OUT = process.argv[3];
const BASE = 'http://localhost';
const CHROME = '/usr/bin/google-chrome';

// (fichier, url, cookie(caissier|otp|null), action-clic optionnelle)
const PLAN = [
  ['01-accueil.png',            '/',                                         null],
  ['02-bouton-connexion.png',   '/accounts/login',                           null],
  ['03-identifiants.png',       '/accounts/login',                           null],
  ['04-code-verification.png',  '/accounts/login/verification',              'otp'],
  ['05-mon-espace.png',         '/redirect-dashboard',                       'caissier'],
  ['06-encaissements.png',      '/membre/centre/paiement/list-paiement',     'caissier'],
  ['07-recherche.png',          '/statistiques/paiement/recherche',          'caissier'],
  ['08-tranche.png',            '/statistiques/paiement/dette/' + S.dette_id + '/', 'caissier'],
  ['09-enregistrer.png',        '/membre/centre/paiement/list-paiement',     'caissier', 'modale'],
  ['10-quittance.png',          '/statistiques/paiement/eleve/' + S.eleve_id + '/?inscription=' + S.inscription_id, 'caissier'],
  ['11-quitter.png',            '/membre/dashboard',                         'caissier'],
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox','--disable-gpu','--hide-scrollbars','--force-device-scale-factor=1'],
    defaultViewport: { width: 1366, height: 900 },
  });
  for (const [fichier, url, cook, action] of PLAN) {
    const page = await browser.newPage();
    if (cook) {
      await page.setCookie({ name: 'sessionid', value: S[cook], domain: 'localhost', path: '/', httpOnly: true });
    }
    try {
      await page.goto(BASE + url, { waitUntil: 'networkidle2', timeout: 30000 });
      await new Promise(r => setTimeout(r, 700));
      if (action === 'modale') {
        // ouvrir la premiere modale d'encaissement si un bouton existe
        const btn = await page.$('button[data-paiement-dette], [data-modal-ouvrir]');
        if (btn) { await btn.click(); await new Promise(r => setTimeout(r, 600)); }
      }
      await page.screenshot({ path: OUT + '/' + fichier });
      console.log('OK   ' + fichier);
    } catch (e) {
      console.log('FAIL ' + fichier + ' : ' + e.message.split('\n')[0]);
    }
    await page.close();
  }
  await browser.close();
})();

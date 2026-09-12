// Délégation d'évènements compatible CSP stricte (sans gestionnaire inline).
// Remplace les onclick="fn(args)" par data-action="fn" data-args="[...]".
// Aucun eval : on résout la fonction sur window et on l'appelle avec les args JSON.
(function () {
  function run(el, evt) {
    var fn = el.getAttribute('data-action');
    if (fn === 'dismiss') { el.parentElement && el.parentElement.remove(); return; }
    if (typeof window[fn] !== 'function') return;
    var args = [];
    var raw = el.getAttribute('data-args');
    if (raw) { try { args = JSON.parse(raw); } catch (e) { args = [raw]; } }
    return window[fn].apply(null, args);
  }

  document.addEventListener('click', function (evt) {
    var el = evt.target.closest('[data-action]');
    if (el && el.getAttribute('data-on') !== 'change') {
      if (el.getAttribute('data-prevent') === '1') evt.preventDefault();
      run(el, evt);
    }
  });

  document.addEventListener('change', function (evt) {
    var el = evt.target.closest('[data-action][data-on="change"]');
    if (el) run(el, evt);
  });

  // Soumission automatique d'un champ : <select data-auto-submit>
  document.addEventListener('change', function (evt) {
    var el = evt.target.closest('[data-auto-submit]');
    if (el && el.form) el.form.submit();
  });

  // Soumission avec confirmation : <form data-confirm="Message ?">
  document.addEventListener('submit', function (evt) {
    var f = evt.target.closest('form[data-confirm]');
    if (f && !window.confirm(f.getAttribute('data-confirm'))) evt.preventDefault();
  });

  // Champs « montant » (paiements, frais, prestations...) : nombre entier
  // positif uniquement -- aucun signe, symbole ni lettre, saisi ou collé.
  // Portée par nom/id (montant, prix) plutôt qu'un data-attribute : couvre
  // aussi les champs générés dynamiquement (lignes de frais ajoutées en JS)
  // sans qu'il faille penser à les marquer un par un.
  function estChampMontant(el) {
    return !!el && el.tagName === 'INPUT' && /montant|prix/i.test((el.name || '') + (el.id || ''));
  }

  document.addEventListener('keydown', function (evt) {
    if (!estChampMontant(evt.target)) return;
    // Navigation (flèches, Tab, Retour arrière...) et raccourcis (Ctrl/Cmd+X/C/V/A)
    // ont un nom de touche de plusieurs caractères ou une touche de contrôle enfoncée.
    if (evt.ctrlKey || evt.metaKey || evt.key.length > 1) return;
    if (!/[0-9]/.test(evt.key)) evt.preventDefault();
  });

  document.addEventListener('input', function (evt) {
    if (!estChampMontant(evt.target)) return;
    var propre = evt.target.value.replace(/[^0-9]/g, '');
    if (propre !== evt.target.value) evt.target.value = propre;
  });

  document.addEventListener('paste', function (evt) {
    if (!estChampMontant(evt.target)) return;
    var presse_papier = evt.clipboardData || window.clipboardData;
    var texte = presse_papier ? presse_papier.getData('text') : '';
    if (/[^0-9]/.test(texte)) {
      evt.preventDefault();
      var champ = evt.target;
      champ.value = texte.replace(/[^0-9]/g, '');
      champ.dispatchEvent(new Event('input', { bubbles: true }));
    }
  });
})();

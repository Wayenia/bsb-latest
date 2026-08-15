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
})();

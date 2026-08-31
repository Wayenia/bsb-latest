/* Reduction de colonnes des tableaux du back-office.
 *
 * Au-dela de trois colonnes, la lecture se degrade et la ligne devient une
 * bande a parcourir. On garde donc les trois premieres colonnes et celle des
 * actions ; les autres passent derriere un bouton qui deplie une fiche de
 * detail sous la ligne.
 *
 * Tout est fait a l'execution : le gabarit n'a qu'une classe a porter, et les
 * intitules sont lus dans le <thead> du tableau. Sans JavaScript, le tableau
 * reste complet — degradation acceptable, rien n'est perdu.
 *
 * En dessous de 640px, le tableau est deja replie en fiches par la feuille de
 * style : on ne masque alors aucune colonne, tout est deja lisible.
 */
(function () {
    'use strict';

    var VISIBLES = 3;                       // colonnes conservees
    var LARGE = window.matchMedia('(min-width: 640px)');

    function estActions(intitule, cellule) {
        return /action/i.test(intitule || '') || (cellule && cellule.classList.contains('bo-actions-cell'));
    }

    function preparer(table) {
        var thead = table.tHead;
        if (!thead || !thead.rows.length) return null;
        var entetes = Array.prototype.map.call(thead.rows[0].cells, function (th) {
            return (th.textContent || '').trim();
        });

        var secondaires = [];
        entetes.forEach(function (intitule, i) {
            if (i < VISIBLES) return;
            if (estActions(intitule)) return;
            secondaires.push(i);
        });
        return secondaires.length ? { entetes: entetes, secondaires: secondaires } : null;
    }

    function cellulesDe(ligne) {
        return Array.prototype.slice.call(ligne.cells);
    }

    function appliquer(table, plan, actif) {
        var thead = table.tHead;
        plan.secondaires.forEach(function (i) {
            var th = thead.rows[0].cells[i];
            if (th) th.hidden = actif;
        });
        Array.prototype.forEach.call(table.tBodies, function (corps) {
            Array.prototype.forEach.call(corps.rows, function (ligne) {
                if (ligne.dataset.detail === 'true') { ligne.hidden = true; return; }
                var cellules = cellulesDe(ligne);
                if (cellules.length < plan.entetes.length) return;   // ligne de groupe
                plan.secondaires.forEach(function (i) {
                    if (cellules[i]) cellules[i].hidden = actif;
                });
                var bouton = ligne.querySelector('.bo-oeil');
                if (bouton) bouton.hidden = !actif;
            });
        });
    }

    function ajouterBoutons(table, plan) {
        Array.prototype.forEach.call(table.tBodies, function (corps) {
            Array.prototype.forEach.call(corps.rows, function (ligne) {
                if (ligne.dataset.detail === 'true' || ligne.querySelector('.bo-oeil')) return;
                var cellules = cellulesDe(ligne);
                if (cellules.length < plan.entetes.length) return;
                var hote = ligne.querySelector('.bo-actions-cell') || cellules[cellules.length - 1];
                if (!hote) return;
                var bouton = document.createElement('button');
                bouton.type = 'button';
                bouton.className = 'bo-oeil';
                bouton.setAttribute('aria-expanded', 'false');
                bouton.setAttribute('aria-label', 'Voir le détail de la ligne');
                bouton.title = 'Voir le détail';
                bouton.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
                    'stroke-width="1.8" aria-hidden="true"><path stroke-linecap="round" ' +
                    'stroke-linejoin="round" d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 ' +
                    '18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.6"/></svg>';
                hote.insertBefore(bouton, hote.firstChild);
            });
        });
    }

    function basculerDetail(ligne, plan) {
        var suivante = ligne.nextElementSibling;
        if (suivante && suivante.dataset.detail === 'true') {
            suivante.remove();
            ligne.querySelector('.bo-oeil').setAttribute('aria-expanded', 'false');
            return;
        }
        var cellules = cellulesDe(ligne);
        // Insertion par reference et non par index calcule : un tableau a
        // plusieurs <tbody> ou a lignes de groupe fausserait le calcul.
        var detail = document.createElement('tr');
        detail.dataset.detail = 'true';
        detail.className = 'bo-detail-ligne';
        ligne.parentNode.insertBefore(detail, ligne.nextSibling);
        var cel = document.createElement('td');
        detail.appendChild(cel);
        cel.colSpan = plan.entetes.length + 1;
        var liste = document.createElement('dl');
        liste.className = 'bo-detail';
        plan.secondaires.forEach(function (i) {
            if (!cellules[i]) return;
            var dt = document.createElement('dt');
            dt.textContent = plan.entetes[i];
            var dd = document.createElement('dd');
            dd.innerHTML = cellules[i].innerHTML;
            liste.appendChild(dt);
            liste.appendChild(dd);
        });
        cel.appendChild(liste);
        ligne.querySelector('.bo-oeil').setAttribute('aria-expanded', 'true');
    }

    document.querySelectorAll('.bo-table-compacte').forEach(function (table) {
        var plan = preparer(table);
        if (!plan) return;
        ajouterBoutons(table, plan);

        function synchroniser() {
            // Sous 640px la feuille de style replie deja la ligne en fiche :
            // masquer des colonnes y ferait perdre de l'information.
            appliquer(table, plan, LARGE.matches);
        }
        synchroniser();
        LARGE.addEventListener('change', synchroniser);

        table.addEventListener('click', function (e) {
            var bouton = e.target.closest('.bo-oeil');
            if (!bouton || !LARGE.matches) return;
            basculerDetail(bouton.closest('tr'), plan);
        });
    });
})();

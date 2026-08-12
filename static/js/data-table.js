/*
 * Ameliore les tables ".data-table" : tri par colonne (clic sur l'en-tete) +
 * export (copier / CSV / Excel / imprimer-PDF). Remplace DataTables/jQuery -
 * zero dependance externe, donc rien a fingerprinter et rien a maintenir a
 * jour cote securite. Le tri/export porte sur les lignes visibles dans le
 * DOM (recherche et pagination restent gerees cote serveur par Django).
 */
(function () {
  function csvEscape(value) {
    var v = String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
    if (/[",\n]/.test(v)) {
      v = '"' + v.replace(/"/g, '""') + '"';
    }
    return v;
  }

  function getRows(table) {
    var tbody = table.querySelector('tbody');
    if (!tbody) return [];
    return Array.prototype.filter.call(tbody.querySelectorAll('tr'), function (tr) {
      return !tr.querySelector('[colspan]');
    });
  }

  function getHeaders(table) {
    var thead = table.querySelector('thead');
    if (!thead) return [];
    return Array.prototype.map.call(thead.querySelectorAll('th'), function (th) {
      return th.innerText.trim();
    });
  }

  function tableToMatrix(table) {
    var headers = getHeaders(table);
    var rows = getRows(table).map(function (tr) {
      return Array.prototype.map.call(tr.children, function (td) {
        return td.innerText.trim();
      });
    });
    return { headers: headers, rows: rows };
  }

  function downloadBlob(content, filename, mime) {
    var blob = new Blob([content], { type: mime });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function exportCsv(table) {
    var data = tableToMatrix(table);
    var lines = [data.headers.map(csvEscape).join(',')];
    data.rows.forEach(function (row) { lines.push(row.map(csvEscape).join(',')); });
    downloadBlob('﻿' + lines.join('\r\n'), 'export.csv', 'text/csv;charset=utf-8');
  }

  function exportExcel(table) {
    var data = tableToMatrix(table);
    var html = '<table><thead><tr>' +
      data.headers.map(function (h) { return '<th>' + h + '</th>'; }).join('') +
      '</tr></thead><tbody>' +
      data.rows.map(function (row) {
        return '<tr>' + row.map(function (c) { return '<td>' + c + '</td>'; }).join('') + '</tr>';
      }).join('') +
      '</tbody></table>';
    downloadBlob(
      '﻿' + html,
      'export.xls',
      'application/vnd.ms-excel;charset=utf-8'
    );
  }

  function copyTable(table) {
    var data = tableToMatrix(table);
    var lines = [data.headers.join('\t')];
    data.rows.forEach(function (row) { lines.push(row.join('\t')); });
    var text = lines.join('\n');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
    }
  }

  function makeSortable(table) {
    var thead = table.querySelector('thead');
    var tbody = table.querySelector('tbody');
    if (!thead || !tbody) return;

    Array.prototype.forEach.call(thead.querySelectorAll('th'), function (th, colIndex) {
      th.style.cursor = 'pointer';
      th.title = 'Trier';
      th.addEventListener('click', function () {
        var dir = th.dataset.sortDir === 'asc' ? 'desc' : 'asc';
        Array.prototype.forEach.call(thead.querySelectorAll('th'), function (h) { delete h.dataset.sortDir; });
        th.dataset.sortDir = dir;

        var rows = getRows(table);
        rows.sort(function (a, b) {
          var av = (a.children[colIndex] && a.children[colIndex].innerText || '').trim();
          var bv = (b.children[colIndex] && b.children[colIndex].innerText || '').trim();
          var an = parseFloat(av.replace(/\s/g, '').replace(',', '.'));
          var bn = parseFloat(bv.replace(/\s/g, '').replace(',', '.'));
          var cmp = (!isNaN(an) && !isNaN(bn)) ? (an - bn) : av.localeCompare(bv, 'fr');
          return dir === 'asc' ? cmp : -cmp;
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
  }

  function addToolbar(table) {
    var toolbar = document.createElement('div');
    toolbar.className = 'flex flex-wrap gap-2 mb-3';
    toolbar.innerHTML =
      '<button type="button" data-action="copy" class="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50">Copier</button>' +
      '<button type="button" data-action="csv" class="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50">CSV</button>' +
      '<button type="button" data-action="excel" class="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50">Excel</button>' +
      '<button type="button" data-action="print" class="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50">Imprimer / PDF</button>';

    var anchor = table.closest('.overflow-x-auto') || table;
    anchor.parentNode.insertBefore(toolbar, anchor);

    toolbar.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-action]');
      if (!btn) return;
      var action = btn.dataset.action;
      if (action === 'copy') copyTable(table);
      else if (action === 'csv') exportCsv(table);
      else if (action === 'excel') exportExcel(table);
      else if (action === 'print') window.print();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('table.data-table').forEach(function (table) {
      addToolbar(table);
      makeSortable(table);
    });
  });
})();

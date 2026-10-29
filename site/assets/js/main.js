// 基督教世界故事 · 轻量客户端筛选（分类页 / 全部页）
document.addEventListener('DOMContentLoaded', function () {
  var input = document.getElementById('filter-input');
  var select = document.getElementById('source-filter');
  if (!input && !select) return;

  function filter() {
    var q = (input ? input.value : '').toLowerCase().trim();
    var src = select ? select.value : '';
    var cards = document.querySelectorAll('.story-card');
    cards.forEach(function (card) {
      var titleEl = card.querySelector('h3');
      var textEl = card.querySelector('.story-text');
      var title = titleEl ? titleEl.textContent.toLowerCase() : '';
      var text = textEl ? textEl.textContent.toLowerCase() : '';
      var source = card.getAttribute('data-source') || '';
      var ok = true;
      if (q && title.indexOf(q) === -1 && text.indexOf(q) === -1) ok = false;
      if (src && source !== src) ok = false;
      card.style.display = ok ? '' : 'none';
    });
  }

  if (input) input.addEventListener('input', filter);
  if (select) select.addEventListener('change', filter);
});

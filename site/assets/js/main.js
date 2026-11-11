// 基督教故事 · 前端交互（无依赖）
// 1) 移动端汉堡菜单  2) 书架实时搜索 / 主题标签  3) 七套配色切换

(function () {
  var navToggle = document.getElementById("navToggle");
  var mainNav = document.getElementById("mainNav");
  if (navToggle && mainNav) {
    navToggle.addEventListener("click", function () {
      var open = mainNav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    mainNav.addEventListener("click", function (e) {
      if (e.target && e.target.tagName === "A") {
        mainNav.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }
})();

document.addEventListener('DOMContentLoaded', function () {
  var input = document.getElementById('filter-input');
  var clear = document.getElementById('filter-clear');
  var bar = document.querySelector('.searchbar');
  var cards = Array.prototype.slice.call(document.querySelectorAll('.book-card'));
  if (!input || !cards.length) return;

  var empty = document.getElementById('empty-state');
  var chips = Array.prototype.slice.call(document.querySelectorAll('.tag-chip, .region-chip'));
  var sections = Array.prototype.slice.call(
    document.querySelectorAll('.featured, .shelf, .more-stories')
  );

  function apply(raw) {
    var q = (raw || '').toLowerCase().trim();
    input.value = raw || '';
    if (bar) bar.classList.toggle('has-value', q.length > 0);

    var visible = 0;
    cards.forEach(function (card) {
      var hay = card.getAttribute('data-search') || '';
      var ok = !q || hay.indexOf(q) !== -1;
      card.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });

    sections.forEach(function (sec) {
      var inner = sec.querySelectorAll('.book-card');
      if (!inner.length) return;
      var any = false;
      Array.prototype.forEach.call(inner, function (c) {
        if (c.style.display !== 'none') any = true;
      });
      sec.style.display = (q && !any) ? 'none' : '';
    });

    var catCards = document.querySelector('.cat-cards');
    if (catCards) catCards.style.display = q ? 'none' : '';

    if (empty) empty.hidden = !(q && visible === 0);
    chips.forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-tag').toLowerCase() === q);
    });
  }

  input.addEventListener('input', function () { apply(input.value); });
  if (clear) clear.addEventListener('click', function () {
    apply('');
    input.focus();
  });
  chips.forEach(function (b) {
    b.addEventListener('click', function () {
      var tag = b.getAttribute('data-tag');
      apply(input.value.trim().toLowerCase() === tag.toLowerCase() ? '' : tag);
      if (bar) window.scrollTo({ top: bar.getBoundingClientRect().top + window.pageYOffset - 90, behavior: 'smooth' });
    });
  });

  try {
    var q0 = new URLSearchParams(window.location.search).get('q');
    if (q0) apply(q0);
  } catch (e) { /* 忽略旧浏览器 */ }
});

(function () {
  var KEY = 'story-palette';
  var P = ["monet", "matisse", "morandi", "macaron", "rococo", "vangogh", "hokusai"];
  function apply(n) {
    if (P.indexOf(n) === -1) return false;
    document.documentElement.setAttribute('data-palette', n);
    try { localStorage.setItem(KEY, n); } catch (e) {}
    sync();
    return true;
  }
  function sync() {
    var c = document.documentElement.getAttribute('data-palette');
    var d = document.querySelectorAll('.palette-dot');
    for (var i = 0; i < d.length; i++) {
      d[i].setAttribute('aria-pressed', d[i].getAttribute('data-palette') === c ? 'true' : 'false');
    }
  }
  function init() {
    var cur = document.documentElement.getAttribute('data-palette');
    var d = document.querySelectorAll('.palette-dot');
    for (var i = 0; i < d.length; i++) {
      (function (b) {
        b.addEventListener('click', function () { apply(b.getAttribute('data-palette')); });
      })(d[i]);
      if (d[i].getAttribute('data-palette') === cur) d[i].setAttribute('aria-pressed', 'true');
    }
    try {
      var s = localStorage.getItem(KEY);
      if (s && s !== cur) apply(s);
    } catch (e) {}
  }
  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();

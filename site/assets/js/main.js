// 移动端汉堡菜单
(function () {
  var navToggle = document.getElementById("navToggle");
  var mainNav = document.getElementById("mainNav");
  if (!navToggle || !mainNav) return;
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
})();

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

(function(){
  var KEY='story-palette';
  var P=["monet","matisse","morandi","macaron","rococo","vangogh","hokusai"];
  function apply(n){if(P.indexOf(n)===-1)return false;document.documentElement.setAttribute('data-palette',n);try{localStorage.setItem(KEY,n);}catch(e){}sync();return true;}
  function sync(){var c=document.documentElement.getAttribute('data-palette');var d=document.querySelectorAll('.palette-dot');for(var i=0;i<d.length;i++){d[i].setAttribute('aria-pressed',d[i].getAttribute('data-palette')===c?'true':'false');}}
  function init(){var cur=document.documentElement.getAttribute('data-palette');var d=document.querySelectorAll('.palette-dot');for(var i=0;i<d.length;i++){(function(b){b.addEventListener('click',function(){apply(b.getAttribute('data-palette'));});})(d[i]);if(d[i].getAttribute('data-palette')===cur)d[i].setAttribute('aria-pressed','true');}try{var s=localStorage.getItem(KEY);if(s&&s!==cur)apply(s);}catch(e){}}
  if(document.readyState!=='loading')init();else document.addEventListener('DOMContentLoaded',init);
})();

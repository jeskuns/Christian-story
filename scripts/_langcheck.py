import json, subprocess, collections
raw = subprocess.run(["git", "show", "68bb5eb:data/db/articles.json"], capture_output=True,
                     cwd=r"c:\Users\Administrator\Documents\lifeOS\personal\Christian-story")
data = json.loads(raw.stdout.decode("utf-8"))
arts = data.get("articles", [])
print("TOTAL:", len(arts))
langs = collections.Counter((a.get("language") or "?") for a in arts)
print("LANGS:", dict(sorted(langs.items(), key=lambda x: -x[1])))
kws = ("doxa.app", "sabda", "christiantoday.co.kr", "christiantoday.co.jp", "cma-mission",
       "aleteia", "godreports", "fundacioncarf", "russianpentecostal")
for kw in kws:
    hits = [a for a in arts if kw in (a.get("url") or "")]
    print(f"{kw:24s} -> {len(hits)}")
    for a in hits[:2]:
        body = len(a.get("content") or "")
        t = a.get("title_zh") or a.get("title") or ""
        print(f"    * [{a.get('language')}] {t[:45]} | 正文{body}字")

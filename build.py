# -*- coding: utf-8 -*-
"""
臥龍会 Journal builder.
Reads content/journal/*.md (YAML front-matter) and regenerates:
  journal/<slug>/index.html, en/journal/<slug>/index.html
  journal/index.html, en/journal/index.html (hubs)
  about/higano-taku/index.html, en/about/higano-taku/index.html (author)
  sitemap.xml
  and injects the featured cards into index.html / en/index.html (between markers)
Design, fonts (incl. NameJP 点あり 琢), and structured data are reproduced 1:1.
No third-party deps (pure stdlib + PyYAML).
Run:  python3 build.py
"""
import os, re, html, json, base64, glob, datetime
try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML required: pip install pyyaml")

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://studio.garyukai.jp"
LOGO = f"{BASE}/assets/img_f6c0f2ddaf33.png"
OGP  = f"{BASE}/ogp.jpg"
AUTHOR_PHOTO = "img_904b72b379bc.jpg"

def esc(s): return html.escape(s or "", quote=True)
def eurl(fn): return fn if str(fn).startswith("http") else f"{BASE}{fn if str(fn).startswith('/') else '/assets/'+fn}"
def disp_date(d):
    return str(d or "")[:10].replace("-", ".")

# ---------- fonts / css ----------
_b64 = base64.b64encode(open(os.path.join(ROOT,"assets/fonts/NameJP.woff2"),"rb").read()).decode()
FONT_FACE = ('@font-face{font-family:"NameJP";src:url("/assets/fonts/NameJP.woff2") format("woff2");font-display:swap}'
             '.name-jp{font-family:"NameJP",var(--mincho)}')

CSS_BODY = r'''
:root{--paper:#f4f2ec;--paper2:#eae6db;--surface:#fffdf8;--surface2:#f8f5ee;--ink:#14110b;--ink2:#574f42;--faint:#8f8676;--line:#d8cfbf;--line2:#ebe4d6;--shu:#b83521;--shu-deep:#8f2716;--shu-tint:#f4e7e2;--mincho:__MIN__;--gothic:__GO__;--sans:"Helvetica Neue",Arial,__GO__;--shadow:0 1px 2px rgba(20,17,11,.03),0 18px 40px -26px rgba(20,17,11,.18);--shadow-h:0 3px 8px rgba(20,17,11,.05),0 30px 60px -28px rgba(20,17,11,.28)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#100e0a;--paper2:#15110c;--surface:#191510;--surface2:#201b15;--ink:#efe8db;--ink2:#b7ae9d;--faint:#8a8172;--line:#2b261f;--line2:#231e18;--shu:#e0715a;--shu-deep:#c1543f;--shu-tint:#291c17;--shadow:0 20px 44px -26px rgba(0,0,0,.72);--shadow-h:0 30px 60px -28px rgba(0,0,0,.88)}}
:root[data-theme="dark"]{--paper:#100e0a;--paper2:#15110c;--surface:#191510;--surface2:#201b15;--ink:#efe8db;--ink2:#b7ae9d;--faint:#8a8172;--line:#2b261f;--line2:#231e18;--shu:#e0715a;--shu-deep:#c1543f;--shu-tint:#291c17;--shadow:0 20px 44px -26px rgba(0,0,0,.72);--shadow-h:0 30px 60px -28px rgba(0,0,0,.88)}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--gothic);line-height:1.95;font-feature-settings:"palt" 1;-webkit-font-smoothing:antialiased;line-break:strict;word-break:auto-phrase}
img{max-width:100%;display:block}a{color:inherit}
.nb{display:inline-block}
.wrap{max-width:760px;margin:0 auto;padding:0 24px}
.nav{border-bottom:1px solid var(--line)}
.nav .wrap{max-width:1100px;display:flex;align-items:center;justify-content:space-between;height:62px}
.brand{display:flex;align-items:center;text-decoration:none}
.logo{height:26px;width:auto;display:block}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .logo{filter:invert(1) brightness(1.7)}}
:root[data-theme="dark"] .logo{filter:invert(1) brightness(1.7)}
.navr{display:flex;gap:22px;font-family:var(--sans);font-size:12px;letter-spacing:.1em}
.navr a{color:var(--ink2);text-decoration:none}.navr a:hover{color:var(--shu)}
main{padding:clamp(26px,4vw,44px) 0 clamp(48px,7vw,80px)}
.eyecatch{width:100%;aspect-ratio:16/8;object-fit:cover;margin:0 0 24px;display:block}
.eyebrow{font-family:var(--mincho);font-weight:700;font-size:14px;letter-spacing:.08em;color:var(--shu);display:block}
h1{font-family:var(--mincho);font-weight:800;font-size:clamp(28px,4.6vw,44px);line-height:1.3;letter-spacing:.01em;margin:10px 0 0;text-wrap:pretty}
.byline{margin:18px 0 0;font-size:13.5px;color:var(--faint)}
.byline a{color:var(--ink2);text-decoration:underline;text-decoration-color:var(--line);text-decoration-thickness:1px;text-underline-offset:.35em}
.pubdate{margin:10px 0 0;font-family:var(--sans);font-size:12px;letter-spacing:.06em;color:var(--faint)}
.card .cdate{display:block;margin-top:10px;font-family:var(--sans);font-size:11.5px;letter-spacing:.06em;color:var(--faint)}
.lead{margin:24px 0 0;font-size:clamp(16px,1.7vw,18.5px);line-height:1.95;color:var(--ink2)}
.qa{margin-top:clamp(26px,4vw,40px)}
.qa h2{font-family:var(--mincho);font-weight:800;font-size:clamp(19px,2.4vw,25px);line-height:1.5;letter-spacing:.01em;margin:0 0 12px;text-wrap:pretty}
.qa h2::before{content:"Q. ";color:var(--shu)}
.qa p{margin:0 0 1.1em;font-size:clamp(15px,1.6vw,17px);line-height:2.05;color:var(--ink)}
.article{margin-top:clamp(26px,4vw,40px)}
.article h2{font-family:var(--mincho);font-weight:800;font-size:clamp(20px,2.5vw,26px);line-height:1.5;letter-spacing:.01em;margin:clamp(28px,4vw,40px) 0 12px;text-wrap:pretty}
.article h3{font-family:var(--mincho);font-weight:800;font-size:clamp(18px,2vw,21px);line-height:1.5;margin:24px 0 10px}
.article p{margin:0 0 1.1em;font-size:clamp(15px,1.6vw,17px);line-height:2.05;color:var(--ink)}
.article ul,.article ol{margin:0 0 1.2em;padding-left:1.4em;color:var(--ink);line-height:2}
.article li{margin:.3em 0}
.article blockquote{margin:1.4em 0;padding:6px 0 6px 18px;border-left:2px solid var(--shu);color:var(--ink2)}
.article a{color:var(--shu);text-decoration:underline;text-underline-offset:.2em}
.article img{width:100%;margin:1.4em 0}
.article strong{font-weight:800}.article em{font-style:italic}
.divider{height:0;border:none;margin:clamp(26px,4vw,40px) 0}
.cta{margin-top:clamp(36px,5vw,56px);background:var(--paper2);padding:clamp(28px,4vw,40px);text-align:center}
.cta h3{font-family:var(--mincho);font-weight:800;font-size:clamp(20px,2.6vw,27px);margin:0;color:var(--ink);line-height:1.5}
.cta p{margin:14px auto 0;max-width:48ch;color:var(--ink2);font-size:15px;line-height:1.95}
.cta .btn{display:inline-block;margin-top:22px;background:var(--shu);color:#fff;text-decoration:none;font-family:var(--mincho);font-weight:800;letter-spacing:.06em;padding:15px 34px;transition:background .2s}
.cta .btn:hover{background:var(--shu-deep)}
.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:clamp(18px,2.4vw,26px);margin-top:clamp(20px,3vw,30px)}
@media(max-width:620px){.cards{grid-template-columns:1fr;gap:16px}}
.card{display:flex;flex-direction:column;text-decoration:none;background:var(--surface);border:1px solid var(--line2);border-radius:3px;box-shadow:var(--shadow);overflow:hidden;transition:transform .25s cubic-bezier(.2,.7,.2,1),box-shadow .25s}
.card:hover{transform:translateY(-3px);box-shadow:var(--shadow-h)}
.card .thumb{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.card .body{padding:clamp(18px,2vw,22px)}
.card .k{font-family:var(--mincho);font-weight:700;font-size:12px;letter-spacing:.06em;color:var(--shu)}
.card h3{font-family:var(--mincho);font-weight:800;font-size:19px;margin:7px 0 0;color:var(--ink);line-height:1.4}
.card p{margin:8px 0 0;font-size:14px;color:var(--ink2);line-height:1.8}
.lineage{margin-top:clamp(16px,2.2vw,24px)}
.lineage .gen{padding:clamp(18px,2.2vw,24px) 0;border-top:1px solid var(--line)}
.lineage .gen:last-child{border-bottom:1px solid var(--line)}
.lineage .gno{font-family:var(--mincho);font-weight:700;font-size:12.5px;letter-spacing:.12em;color:var(--shu)}
.lineage .gen h3{font-family:var(--mincho);font-weight:800;font-size:clamp(19px,2.2vw,23px);margin:6px 0 0;color:var(--ink);line-height:1.4}
.lineage .gen p{margin:9px 0 0;font-size:15px;line-height:1.95;color:var(--ink2)}
.lineage-more{margin:26px 0 0}
.lineage-more a{display:block;background:var(--surface2);border:1px solid var(--line2);border-radius:3px;box-shadow:var(--shadow);padding:clamp(18px,2.2vw,24px);font-family:var(--mincho);font-weight:800;font-size:clamp(16px,1.9vw,18px);letter-spacing:.03em;color:var(--shu);text-decoration:none;transition:transform .25s cubic-bezier(.2,.7,.2,1),box-shadow .25s}
.lineage-more a:hover{transform:translateY(-3px);box-shadow:var(--shadow-h);color:var(--shu-deep)}
.prof{display:flex;gap:28px;flex-wrap:wrap;align-items:flex-start}
.prof .photo{width:210px;aspect-ratio:4/5;background-size:cover;background-position:center top;flex:none}
.prof .meta{flex:1;min-width:240px}
.tags{display:flex;flex-wrap:wrap;gap:10px 26px;margin-top:20px}
.tag{font-family:var(--mincho);font-size:14px;color:var(--ink2);position:relative}
.tag:not(:last-child)::after{content:"\FF0F";position:absolute;right:-18px;color:var(--line)}
.backlink{display:inline-block;margin-top:32px;font-family:var(--mincho);font-weight:700;font-size:14px;color:var(--shu);text-decoration:none}
footer{border-top:1px solid var(--line);padding:28px 0 48px;text-align:center;margin-top:clamp(40px,6vw,72px)}
footer p{font-family:var(--mincho);font-size:12px;letter-spacing:.06em;color:var(--faint);margin:0}
'''
def css(lang):
    if lang=="ja":
        fonts='<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@600;700;800&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap">'
        mincho='"Shippori Mincho","Hiragino Mincho ProN","Yu Mincho",serif'
        gothic='"Zen Kaku Gothic New","Hiragino Kaku Gothic ProN","Yu Gothic","Noto Sans JP",sans-serif'
    else:
        fonts='<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap">'
        mincho='"Cormorant Garamond","EB Garamond",Georgia,serif'
        gothic='"EB Garamond","Cormorant Garamond",Georgia,serif'
    body=CSS_BODY.replace("__MIN__",mincho).replace("__GO__",gothic)
    return fonts+"\n<style>"+FONT_FACE+body+"</style>"

# ---------- nav / head / footer ----------
def nav(lang):
    if lang=="ja":
        links=(f'<a href="{BASE}/">臥龍会について</a><a href="{BASE}/journal/">読み物</a>'
               f'<a href="{BASE}/about/higano-taku/">日賀野 琢</a><a href="{BASE}/#contact">お問い合わせ</a>'
               f'<a href="{BASE}/en/journal/">EN</a>')
        home=f"{BASE}/"
    else:
        links=(f'<a href="{BASE}/en/">About</a><a href="{BASE}/en/journal/">Journal</a>'
               f'<a href="{BASE}/en/about/higano-taku/">Taku Higano</a><a href="{BASE}/en/#contact">Contact</a>'
               f'<a href="{BASE}/journal/">日本語</a>')
        home=f"{BASE}/en/"
    return (f'<nav class="nav"><div class="wrap"><a class="brand" href="{home}">'
            f'<img class="logo" src="{LOGO}" alt="臥龍会"></a><div class="navr">{links}</div></div></nav>')

def head(lang,title,desc,canonical,alt_ja,alt_en,ld_list,og_type="article",image=None,extra=""):
    ld="\n".join('<script type="application/ld+json">'+json.dumps(x,ensure_ascii=False)+'</script>' for x in ld_list)
    img=image or OGP
    feed_title="臥龍会 読み物" if lang=="ja" else "Garyukai Journal"
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{esc(title)}</title>\n<meta name="description" content="{esc(desc)}">\n'
            f'<link rel="canonical" href="{canonical}">\n'
            f'<link rel="alternate" hreflang="ja" href="{alt_ja}"><link rel="alternate" hreflang="en" href="{alt_en}">'
            f'<link rel="alternate" hreflang="x-default" href="{alt_ja}">\n'
            f'<link rel="alternate" type="application/rss+xml" title="{feed_title}" href="{BASE}/feed.xml">\n'
            f'<meta property="og:type" content="{og_type}"><meta property="og:title" content="{esc(title)}">'
            f'<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canonical}">'
            f'<meta property="og:image" content="{img}"><meta name="twitter:card" content="summary_large_image">'
            f'<meta property="og:locale" content="{"ja_JP" if lang=="ja" else "en_US"}">'
            f'<meta property="og:site_name" content="{"書道研究 臥龍会" if lang=="ja" else "Garyukai"}">\n'
            f'<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">\n'
            f'{extra}'
            f'<link rel="icon" href="{BASE}/favicon.ico" sizes="any">'
            f'<link rel="icon" type="image/png" sizes="32x32" href="{BASE}/favicon-32.png">'
            f'<link rel="apple-touch-icon" href="{BASE}/apple-touch-icon.png"><meta name="theme-color" content="#f3f1ea">\n'
            f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'{css(lang)}\n{ld}\n</head><body>{nav(lang)}<main><div class="wrap">')
FOOT='</div></main><footer><div class="wrap"><p>書道研究 臥龍会 · GARYUKAI · studio.garyukai.jp</p></div></footer></body></html>'

# ---------- structured data ----------
ORG={"@context":"https://schema.org","@type":["Organization","LocalBusiness"],"name":"書道研究 臥龍会",
     "alternateName":"Garyukai","url":BASE+"/","logo":OGP,
     "sameAs":["https://instagram.com/garyu_shodo","https://instagram.com/garyu_shodo_en","https://garyukai.jp/"]}
def person_ld(lang):
    return {"@context":"https://schema.org","@type":"Person",
            "name":"日賀野 琢" if lang=="ja" else "Taku Higano",
            "alternateName":"Taku Higano" if lang=="ja" else "日賀野 琢",
            "jobTitle":"書道家 / 臥龍会 三代目・代表取締役" if lang=="ja" else "Calligrapher / Third-generation head of Garyukai",
            "url":(BASE+"/about/higano-taku/") if lang=="ja" else (BASE+"/en/about/higano-taku/"),
            "image":eurl(AUTHOR_PHOTO),
            "knowsAbout":["書道","篆書","隷書","古代文字","日本の伝統文化"] if lang=="ja" else ["Japanese calligraphy","seal script","clerical script","ancient Chinese characters","Japanese traditional culture"],
            "worksFor":{"@type":"Organization","name":"書道研究 臥龍会","url":BASE+"/"},
            "sameAs":["https://instagram.com/garyu_shodo","https://instagram.com/garyu_shodo_en"]}
def article_ld(lang,title,desc,url,img,date):
    return {"@context":"https://schema.org","@type":"Article","headline":title,"description":desc,
            "inLanguage":lang,"datePublished":date,"dateModified":date,
            "author":{"@type":"Person","name":"日賀野 琢" if lang=="ja" else "Taku Higano",
                      "url":(BASE+"/about/higano-taku/") if lang=="ja" else (BASE+"/en/about/higano-taku/")},
            "publisher":ORG,"mainEntityOfPage":url,"image":img,"articleSection":"Journal"}

# ---------- mini markdown ----------
def _inline(t):
    t=esc(t)
    t=re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda m:f'<img src="{m.group(2)}" alt="{m.group(1)}">', t)
    t=re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t=re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', t)
    return t
def md2html(md):
    md=(md or "").replace("\r\n","\n").strip()
    blocks=re.split(r'\n\s*\n', md)
    out=[]
    for b in blocks:
        b=b.rstrip()
        if not b: continue
        if re.match(r'^#{1,3}\s', b):
            lvl=len(re.match(r'^(#+)',b).group(1)); lvl=min(lvl,3)
            out.append(f'<h{lvl+0 if lvl>1 else 2}>'+_inline(re.sub(r'^#+\s+','',b))+f'</h{lvl+0 if lvl>1 else 2}>')
        elif b=='---':
            out.append('<hr class="divider">')
        elif all(l.lstrip().startswith(('- ','* ')) for l in b.split("\n")):
            items="".join('<li>'+_inline(l.lstrip()[2:])+'</li>' for l in b.split("\n"))
            out.append(f'<ul>{items}</ul>')
        elif all(re.match(r'^\d+\.\s', l.lstrip()) for l in b.split("\n")):
            items="".join('<li>'+_inline(re.sub(r'^\d+\.\s+','',l.lstrip()))+'</li>' for l in b.split("\n"))
            out.append(f'<ol>{items}</ol>')
        elif all(l.lstrip().startswith('>') for l in b.split("\n")):
            inner=" ".join(re.sub(r'^>\s?','',l.lstrip()) for l in b.split("\n"))
            out.append('<blockquote>'+_inline(inner)+'</blockquote>')
        elif re.match(r'^!\[[^\]]*\]\([^)]+\)$', b):
            out.append(_inline(b))
        else:
            out.append('<p>'+_inline(b.replace("\n","<br>"))+'</p>')
    return "\n".join(out)

def qa_html(md, lang):
    """style==qa: render '## Q\n\nA...' blocks as <section class="qa">."""
    parts=re.split(r'(?m)^##\s+', (md or "").strip())
    secs=[]
    for chunk in parts:
        chunk=chunk.strip()
        if not chunk: continue
        lines=chunk.split("\n\n",1)
        q=lines[0].strip().replace("\n"," ")
        ans=lines[1] if len(lines)>1 else ""
        ps="".join('<p>'+_inline(p.strip())+'</p>' for p in re.split(r'\n\s*\n',ans) if p.strip())
        secs.append(f'<section class="qa"><h2>{_inline(q)}</h2>{ps}</section>')
    return "\n".join(secs)

# ---------- 琢 wrap (body text nodes only) ----------
def wrap_taku(htmls):
    i=htmls.lower().find("<body")
    if i<0: return htmls
    j=htmls.find(">",i)+1
    head_,body=htmls[:j],htmls[j:]
    body=body.replace('<span class="name-jp">琢</span>','琢')
    toks=re.split(r'(<[^>]*>)',body); skip=False
    for k in range(len(toks)):
        t=toks[k]
        if k%2==1:
            tl=t.lower()
            if tl.startswith('<script') or tl.startswith('<style'): skip=True
            elif tl.startswith('</script') or tl.startswith('</style'): skip=False
            continue
        if not skip and '琢' in t:
            toks[k]=t.replace('琢','<span class="name-jp">琢</span>')
    return head_+"".join(toks)

def write(path,content):
    full=os.path.join(ROOT,path); os.makedirs(os.path.dirname(full),exist_ok=True)
    open(full,"w",encoding="utf-8").write(wrap_taku(content))

# ---------- CTA / author data ----------
def cta(lang):
    if lang=="ja":
        return ('<div class="cta"><h3>書のご相談・ご依頼はこちら</h3>'
                '<p>作品制作（企業ロゴ・記念品・空間装飾）、企業研修・講演会、訪日の方向けの書道体験まで。'
                'どんな些細なことからでも、まずはお気軽にご相談ください。</p>'
                f'<a class="btn" href="{BASE}/#contact">お問い合わせはこちら</a></div>')
    return ('<div class="cta"><h3>Commission a work, or get in touch</h3>'
            '<p>From custom calligraphy artwork and corporate workshops to calligraphy experiences for visitors to Japan — '
            'every commission can begin from the smallest inquiry. We would be glad to hear from you.</p>'
            f'<a class="btn" href="{BASE}/en/#contact">Get in touch</a></div>')

AUTHOR={
 "ja":dict(title="日賀野 琢　書家 / 臥龍会 三代目",
   desc="書道家 日賀野琢（ひがの たく）。書道研究 臥龍会 三代目・代表取締役。篆書・隷書を専門とし、日展会員、読売書法会 常任理事などを務める。初代 日賀野東華、二代 日賀野溥と続く臥龍会の系譜を継ぐ。",
   eyebrow="書家",
   bio="1964年、栃木県宇都宮市生まれ。墨の匂いに包まれた環境で育ち、幼少期から筆を握る。臥龍会 三代目として有限会社臥龍会の代表取締役を務めながら、一書家として創作にも没頭する。専門は古代文字（篆書・隷書）。甲骨文字から現代までつらなる文字の成り立ちを踏まえ、一点一点に文字学的・造形的な意図を込めて揮毫する。日展会員、読売書法会 常任理事、全日本書道連盟 監事、謙慎書道会 副事務局長を務め、埼玉学園大学でも教鞭を執る。作家活動にとどまらず、講演や企業向けの作品制作・揮毫を通じて、八十余年続く臥龍会の書を次代へ、そして社会へと広げている。",
   quote="書は、生きる業（ぎょう）。生きていくためのすべての根源であり、それを取ったら何も残らない。",
   tags=["日展 会員","読売書法会 常任理事","全日本書道連盟 監事","謙慎書道会 副事務局長","埼玉学園大学 講師"],
   lineage_head="臥龍会の系譜",
   lineage=[
     dict(gen="初代", name="日賀野 東華（とうか）",
          text="1940年（昭和15年）2月11日、書道教育の普及と研究を目的に臥龍会を創立し、月刊競書誌『臥龍』を興した初代会長。1947年、臥龍会本部で発起人会が開かれた栃木県書道連盟の結成に携わり、初代副会長を務めるなど、栃木の書道文化の礎を築いた。"),
     dict(gen="二代", name="日賀野 溥（ひろし）",
          text="臥龍会 会長。『臥龍』を全国でも最古参となる競書誌（通巻1,850号超）へと継承・発展させ、創立80周年・85周年を牽引。全国約130支部・約2,000名を擁する県内最大の書道団体へと育てた。"),
     dict(gen="三代", name="日賀野 琢（たく）",
          text="有限会社臥龍会 代表取締役／臥龍会 三代目。古代文字（篆書・隷書）を専門とし、日展会員・読売書法会 常任理事ほかを務める。作家活動に加え、企業の作品制作・揮毫・講演を通じて臥龍会の書を社会へ広げている。"),
   ],
   lineage_more="系譜の物語をさらに詳しく　臥龍会 八十五年の歩み →",
   readmore="読み物で、日賀野琢の言葉を読む", back="読み物一覧へ戻る"),
 "en":dict(title="Taku Higano: Calligrapher, Third Generation of Garyukai",
   desc="Taku Higano is a Japanese calligrapher and the third-generation head of the Garyukai calligraphy institute. A specialist in seal and clerical script; member of Nitten and standing director of the Yomiuri Shohokai. He continues the Garyukai lineage of Tōka Higano (founder) and Hiroshi Higano.",
   eyebrow="The Master",
   bio="Born in 1964 in Utsunomiya, Tochigi, Taku Higano grew up surrounded by the scent of sumi ink and took up the brush in early childhood. As the third-generation head of Garyukai and representative director of Garyukai Co., Ltd., he leads the institute while pursuing his own practice as an artist. He specialises in the ancient scripts, seal (tensho) and clerical (reisho), grounding each work in the etymology of characters from oracle-bone forms to the present, with deliberate philological and formal intent. A member of Nitten and standing director of the Yomiuri Shohokai, he has also served as auditor of the All-Japan Calligraphers Federation and deputy secretary-general of the Kenshin Shodokai, and teaches at Saitama Gakuen University. Beyond his own work, through lectures and commissioned pieces and performances for companies, he carries the calligraphy of Garyukai, now in its ninth decade, to the next generation and into wider society.",
   quote="Calligraphy is my life's work — the very root of living. Take it away, and nothing would remain.",
   tags=["Member, Nitten","Standing Director, Yomiuri Shohokai","Auditor, All-Japan Calligraphers Federation","Deputy Secretary-General, Kenshin Shodokai","Lecturer, Saitama Gakuen University"],
   lineage_head="The Garyukai Lineage",
   lineage=[
     dict(gen="First generation", name="Higano Tōka",
          text="Founded Garyukai on 11 February 1940 to advance the study and teaching of calligraphy, and launched the monthly journal Garyu. In 1947 he took part in forming the Tochigi Prefectural Calligraphy Federation — its founding meeting was held at the Garyukai headquarters — and served as its first vice-president, laying the foundations of calligraphic culture in Tochigi."),
     dict(gen="Second generation", name="Higano Hiroshi",
          text="President of Garyukai. He carried the Garyu journal to become one of Japan's longest-running competitive calligraphy monthlies (past its 1,850th issue) and led the 80th and 85th anniversaries, growing Garyukai into the prefecture's largest calligraphy society, with some 130 chapters and around 2,000 members."),
     dict(gen="Third generation", name="Taku Higano",
          text="Representative director of Garyukai Co., Ltd. and third-generation head. A specialist in the ancient seal and clerical scripts; member of Nitten and standing director of the Yomiuri Shohokai. Beyond his own art, he brings Garyukai's calligraphy to society through commissions, performances and talks."),
   ],
   lineage_more="The fuller story — Eighty-Five Years of Garyukai →",
   readmore="Read Taku Higano's words in the Journal", back="Back to Journal"),
}

# ---------- load content ----------
def load_articles():
    arts=[]
    for f in glob.glob(os.path.join(ROOT,"content/journal/*.md")):
        raw=open(f,encoding="utf-8").read()
        m=re.match(r'^---\n(.*?)\n---\n?(.*)$', raw, re.S)
        fm=yaml.safe_load(m.group(1)) if m else yaml.safe_load(raw)
        fm=fm or {}
        fm["slug"]=os.path.splitext(os.path.basename(f))[0]
        # body fields may be in front-matter; fall back to trailing body as JA
        if not fm.get("body_ja") and m and m.group(2).strip(): fm["body_ja"]=m.group(2).strip()
        arts.append(fm)
    arts.sort(key=lambda a:(a.get("order",999), str(a.get("date",""))))
    return arts

def article_url(slug,lang): return f"{BASE}/{'en/' if lang=='en' else ''}journal/{slug}/"

# ---------- builders ----------
def breadcrumb_ld(items):
    return {"@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[{"@type":"ListItem","position":i+1,"name":n,"item":u} for i,(n,u) in enumerate(items)]}

def build_article(a,lang):
    slug=a["slug"]
    title=a["title_"+lang] or a.get("title_ja","")
    desc=(a.get("desc_"+lang) or a.get("excerpt_"+lang) or "")[:300]
    lead=a.get("excerpt_"+lang,"")
    img=eurl(a.get("eyecatch",""))
    date=str(a.get("date","")); section=a.get("category_"+lang,"") or "Journal"
    url=article_url(slug,lang); alt_ja=article_url(slug,"ja"); alt_en=article_url(slug,"en")
    home=(BASE+"/") if lang=="ja" else (BASE+"/en/")
    hub_url=(BASE+"/journal/") if lang=="ja" else (BASE+"/en/journal/")
    ld=[article_ld(lang,title,desc,url,img,date),
        breadcrumb_ld([("臥龍会" if lang=="ja" else "Garyukai",home),
                       ("読み物" if lang=="ja" else "Journal",hub_url),(title,url)])]
    extra=(f'<meta property="article:published_time" content="{date}">'
           f'<meta property="article:modified_time" content="{date}">'
           f'<meta property="article:author" content="{"日賀野 琢" if lang=="ja" else "Taku Higano"}">'
           f'<meta property="article:section" content="{esc(section)}">')
    body_md=a.get("body_"+lang,"") or ""
    if a.get("style")=="qa":
        body=qa_html(body_md,lang)
    else:
        body='<div class="article">'+md2html(body_md)+'</div>'
    eyebrow=("JOURNAL · 書家に聞く" if lang=="ja" else "JOURNAL · IN THE MASTER'S WORDS")
    if lang=="ja":
        by=f'語り手：<a href="{BASE}/about/higano-taku/">日賀野 琢（臥龍会 三代目）</a>'
        back="読み物一覧へ戻る"
    else:
        by=f'By <a href="{BASE}/en/about/higano-taku/">Taku Higano — third-generation head of Garyukai</a>'
        back="Back to Journal"
    h=head(lang,title,desc,url,alt_ja,alt_en,ld,image=img,extra=extra)
    page=(h+f'<img class="eyecatch" src="{img}" alt="{esc(title)}" width="1200" height="600" decoding="async" fetchpriority="high">'
          f'<p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(title)}</h1>'
          f'<p class="byline">{by}</p>'
          + f'<p class="pubdate"><time datetime="{date}">{("公開 " if lang=="ja" else "Published ")}{disp_date(date)}</time></p>'
          + (f'<p class="lead">{esc(lead)}</p>' if lead else '')
          + body + cta(lang)
          + f'<a class="backlink" href="{BASE}/{"en/" if lang=="en" else ""}journal/">← {back}</a>'
          + FOOT)
    write(f'{"en/" if lang=="en" else ""}journal/{slug}/index.html', page)

def card(a,lang,klass="card"):
    slug=a["slug"]; url=article_url(slug,lang)
    title=a["title_"+lang] or a.get("title_ja","")
    cat=a.get("category_"+lang,"") ; ex=a.get("excerpt_"+lang,"")
    img=eurl(a.get("eyecatch",""))
    iso=str(a.get('date',''))[:10]
    return (f'<a class="{klass}" href="{url}"><img class="thumb" src="{img}" alt="{esc(title)}" loading="lazy" decoding="async" width="640" height="360">'
            f'<div class="body"><span class="k">{esc(cat)}</span><h3>{esc(title)}</h3>'
            f'<p>{esc(ex)}</p><time class="cdate" datetime="{iso}">{disp_date(iso)}</time></div></a>')

def build_hub(arts,lang):
    url=(BASE+"/journal/") if lang=="ja" else (BASE+"/en/journal/")
    alt_ja=BASE+"/journal/"; alt_en=BASE+"/en/journal/"
    if lang=="ja":
        title="読み物　書家 日賀野琢に聞く | 臥龍会"
        desc="書道研究 臥龍会・三代目 日賀野琢へのインタビュー。書道とは何か、篆書・隷書の魅力、書道家として生きること。書の一次情報をお届けします。"
        eyebrow="読み物"; h1="読み物　書家に聞く"; lead="臥龍会 三代目・日賀野琢の言葉で、書道の奥深さをお伝えします。"
    else:
        title="Journal — In the Words of Taku Higano | Garyukai"
        desc="Interviews with Taku Higano, third-generation head of the Garyukai calligraphy institute: what shodo is, the allure of seal and clerical script, and a life lived by the brush."
        eyebrow="Journal"; h1="In the Master's Words"; lead="The depth of Japanese calligraphy, in the words of Taku Higano, third-generation head of Garyukai."
    home=(BASE+"/") if lang=="ja" else (BASE+"/en/")
    ld=[{"@context":"https://schema.org","@type":"CollectionPage","name":title,"description":desc,"inLanguage":lang,"url":url,"isPartOf":ORG},
        breadcrumb_ld([("臥龍会" if lang=="ja" else "Garyukai",home),("読み物" if lang=="ja" else "Journal",url)]),
        ORG]
    cards="".join(card(a,lang) for a in arts)
    h=head(lang,title,desc,url,alt_ja,alt_en,ld,og_type="website")
    page=(h+f'<p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(h1)}</h1><p class="lead">{esc(lead)}</p>'
          f'<div class="cards">{cards}</div>{cta(lang)}'+FOOT)
    write(("journal/index.html") if lang=="ja" else ("en/journal/index.html"), page)

def build_author(arts,lang):
    d=AUTHOR[lang]
    url=(BASE+"/about/higano-taku/") if lang=="ja" else (BASE+"/en/about/higano-taku/")
    alt_ja=BASE+"/about/higano-taku/"; alt_en=BASE+"/en/about/higano-taku/"
    ld=[person_ld(lang)]
    h=head(lang,d["title"],d["desc"],url,alt_ja,alt_en,ld,og_type="profile",image=eurl(AUTHOR_PHOTO))
    tg="".join(f'<span class="tag">{esc(t)}</span>' for t in d["tags"])
    cards="".join(card(a,lang) for a in arts)
    page=(h+f'<p class="eyebrow">{esc(d["eyebrow"])}</p><h1>{esc(d["title"])}</h1>'
          f'<div class="prof" style="margin-top:28px"><div class="photo" style="background-image:url(\'{eurl(AUTHOR_PHOTO)}\')"></div>'
          f'<div class="meta"><p style="margin:0;font-size:16px;line-height:2;color:var(--ink2)">{esc(d["bio"])}</p><div class="tags">{tg}</div></div></div>'
          f'<hr class="divider"><p class="lead" style="font-family:var(--mincho);font-size:clamp(19px,2.6vw,26px);line-height:1.7;border:none;padding:0;color:var(--ink)">「{esc(d["quote"])}」</p>'
          f'<hr class="divider"><p class="eyebrow">{esc(d["lineage_head"])}</p>'
          f'<div class="lineage">'+''.join(f'<div class="gen"><span class="gno">{esc(g["gen"])}</span><h3>{esc(g["name"])}</h3><p>{esc(g["text"])}</p></div>' for g in d["lineage"])+'</div>'
          f'<p class="lineage-more"><a href="{article_url("garyukai-85-years",lang)}">{esc(d["lineage_more"])}</a></p>'
          f'<hr class="divider"><p class="eyebrow">{esc(d["readmore"])}</p><div class="cards">{cards}</div>{cta(lang)}'+FOOT)
    write(("about/higano-taku/index.html") if lang=="ja" else ("en/about/higano-taku/index.html"), page)

# ---------- LP featured cards injection ----------
def lp_cards(arts,lang):
    # newest first (date desc, then order asc within same date)
    items=sorted(arts,key=lambda a:(str(a.get("date","")), -a.get("order",999)), reverse=True)
    if not items: return ""
    big=items[0]; rest=items[1:6]; overflow=len(items)>6
    hub=f"{BASE}/{'en/' if lang=='en' else ''}journal/"
    def u(a): return f"{BASE}/{'en/' if lang=='en' else ''}journal/{a['slug']}/"
    more_lbl="続きを読む →" if lang=="ja" else "Read →"
    t=big["title_"+lang] or big.get("title_ja",""); cat=big.get("category_"+lang,""); ex=big.get("excerpt_"+lang,"")
    iso=str(big.get("date",""))[:10]
    hero=(f'<a class="jhero" href="{u(big)}"><div class="jthumb"><img loading="lazy" decoding="async" src="{eurl(big.get("eyecatch",""))}" alt="{esc(t)}"></div>'
          f'<div class="jbody"><span class="jcat">{esc(cat)}</span><h3>{esc(t)}</h3><p>{esc(ex)}</p>'
          f'<time class="jdate" datetime="{iso}">{disp_date(iso)}</time><span class="jmore">{more_lbl}</span></div></a>')
    rows=[]
    for a in rest:
        rt=a["title_"+lang] or a.get("title_ja",""); riso=str(a.get("date",""))[:10]
        rows.append(f'<a class="jrow" href="{u(a)}"><span class="jrow-t">{esc(rt)}</span>'
                    f'<time class="jdate" datetime="{riso}">{disp_date(riso)}</time></a>')
    lst=f'<div class="jlist">{"".join(rows)}</div>' if rows else ""
    more=(f'<a class="jmore-all" href="{hub}">'
          f'{"そのほかの記事はこちら →" if lang=="ja" else "See all articles →"}</a>') if overflow else ""
    return hero+lst+more

def inject_lp(arts):
    for lang,path in (("ja","index.html"),("en","en/index.html")):
        full=os.path.join(ROOT,path)
        s=open(full,encoding="utf-8").read()
        if "<!--JCARDS-->" not in s:
            print("  [skip LP inject: no marker in",path,"]"); continue
        cards=lp_cards(arts,lang)
        s=re.sub(r'<!--JCARDS-->.*?<!--/JCARDS-->', '<!--JCARDS-->'+cards+'<!--/JCARDS-->', s, flags=re.S)
        # 琢 wrap safe (whole file already has proper wrapping; re-wrap only injected region is complex -> wrap file body safely)
        open(full,"w",encoding="utf-8").write(wrap_taku(s))
        print("  injected LP featured ->",path)

# ---------- sitemap ----------
def build_sitemap(arts):
    today=datetime.date.today().isoformat()
    # (ja_url, en_url, lastmod) pairs — each pair emits both URLs with reciprocal hreflang alternates
    pairs=[(BASE+"/",BASE+"/en/",today),
           (BASE+"/journal/",BASE+"/en/journal/",today),
           (BASE+"/about/higano-taku/",BASE+"/en/about/higano-taku/",today)]
    for a in arts:
        d=str(a.get("date",""))[:10] or today
        pairs.append((article_url(a["slug"],"ja"),article_url(a["slug"],"en"),d))
    def alts(ja,en):
        return (f'<xhtml:link rel="alternate" hreflang="ja" href="{ja}"/>'
                f'<xhtml:link rel="alternate" hreflang="en" href="{en}"/>'
                f'<xhtml:link rel="alternate" hreflang="x-default" href="{ja}"/>')
    rows=[]
    for ja,en,d in pairs:
        a=alts(ja,en)
        rows.append(f'<url><loc>{ja}</loc><lastmod>{d}</lastmod>{a}</url>')
        rows.append(f'<url><loc>{en}</loc><lastmod>{d}</lastmod>{a}</url>')
    xml=('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
         'xmlns:xhtml="http://www.w3.org/1999/xhtml">'+"".join(rows)+'</urlset>')
    open(os.path.join(ROOT,"sitemap.xml"),"w",encoding="utf-8").write(xml)

def _rfc822(d):
    try: dt=datetime.datetime.strptime(str(d),"%Y-%m-%d")
    except Exception: dt=datetime.datetime.today()
    return dt.strftime("%a, %d %b %Y 09:00:00 +0900")

def build_feed(arts):
    # RSS 2.0 (Japanese primary) — aids discovery / AIO / subscriptions
    recent=sorted(arts,key=lambda a:str(a.get("date","")),reverse=True)
    items=[]
    for a in recent:
        u=article_url(a["slug"],"ja")
        items.append(
            "<item>"
            f"<title>{esc(a.get('title_ja',''))}</title>"
            f"<link>{u}</link><guid isPermaLink=\"true\">{u}</guid>"
            f"<pubDate>{_rfc822(a.get('date',''))}</pubDate>"
            f"<category>{esc(a.get('category_ja',''))}</category>"
            f"<description>{esc(a.get('excerpt_ja',''))}</description>"
            "</item>")
    xml=('<?xml version="1.0" encoding="UTF-8"?>\n'
         '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
         '<title>臥龍会 読み物 — 書家 日賀野琢に聞く</title>'
         f'<link>{BASE}/journal/</link>'
         '<description>書道研究 臥龍会の読み物。書道とは何か、篆書・隷書の魅力、書家として生きること。</description>'
         '<language>ja</language>'
         f'<atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>'
         +"".join(items)+'</channel></rss>')
    open(os.path.join(ROOT,"feed.xml"),"w",encoding="utf-8").write(xml)

def main():
    arts=load_articles()
    print(f"Loaded {len(arts)} articles:", ", ".join(a["slug"] for a in arts))
    for a in arts:
        build_article(a,"ja"); build_article(a,"en")
    build_hub(arts,"ja"); build_hub(arts,"en")
    build_author(arts,"ja"); build_author(arts,"en")
    build_sitemap(arts)
    build_feed(arts)
    inject_lp(arts)
    print("Build complete.")

if __name__=="__main__":
    main()

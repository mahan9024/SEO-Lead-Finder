import re
import time
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

APP_TITLE = "SEO Lead Finder"
USER_AGENT = "SEO-Lead-Finder/1.0"

st.set_page_config(page_title=APP_TITLE, page_icon="🔎", layout="wide")

def normalize_url(url):
    url = url.strip()
    if not url:
        return ""
    return url if re.match(r"^https?://", url, re.I) else "https://" + url

def fetch(url, timeout=12):
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "fa,en;q=0.8"}
    started = time.perf_counter()
    try:
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return r, round(time.perf_counter() - started, 2), None
    except requests.RequestException as e:
        return None, round(time.perf_counter() - started, 2), str(e)

def word_count(text):
    return len(re.findall(r"\b[\w\u0600-\u06ff]+\b", text or ""))

def audit(url):
    url = normalize_url(url)
    result = {"url": url, "final_url": url, "seo_score": 0, "lead_score": 0,
              "issues": [], "passed": [], "metrics": {}, "title": "", "description": "",
              "response_time": 0, "status": None}
    r, elapsed, error = fetch(url)
    result["response_time"] = elapsed
    if error:
        result["issues"].append(("critical", "سایت قابل دسترسی نیست", error))
        result["lead_score"] = 95
        return result

    result["status"] = r.status_code
    result["final_url"] = r.url
    if "html" not in r.headers.get("content-type", "").lower():
        result["issues"].append(("critical", "محتوا HTML نیست", r.headers.get("content-type", "")))
        result["lead_score"] = 90
        return result

    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    desc = meta.get("content", "").strip() if meta else ""
    h1 = soup.find_all("h1")
    h2 = soup.find_all("h2")
    images = soup.find_all("img")
    missing_alt = [x for x in images if not x.get("alt", "").strip()]
    canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
    viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    schemas = soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)})
    text = soup.get_text(" ", strip=True)
    words = word_count(text)
    parsed = urlparse(r.url)

    robots, _, _ = fetch(urljoin(r.url, "/robots.txt"), timeout=8)
    sitemap, _, _ = fetch(urljoin(r.url, "/sitemap.xml"), timeout=8)

    score = 100
    def issue(sev, name, detail, penalty):
        nonlocal score
        score -= penalty
        result["issues"].append((sev, name, detail))
    def passed(name, detail):
        result["passed"].append((name, detail))

    if parsed.scheme != "https":
        issue("high", "HTTPS فعال نیست", "نسخه HTTPS صفحه بررسی شده نیست.", 12)
    else:
        passed("HTTPS", "HTTPS فعال است.")

    if not title:
        issue("high", "Title وجود ندارد", "تگ title پیدا نشد.", 10)
    elif len(title) < 30:
        issue("medium", "Title کوتاه است", f"{len(title)} کاراکتر.", 5)
    elif len(title) > 60:
        issue("medium", "Title طولانی است", f"{len(title)} کاراکتر.", 4)
    else:
        passed("Title", f"{len(title)} کاراکتر.")

    if not desc:
        issue("medium", "Meta Description وجود ندارد", "توضیحات متا پیدا نشد.", 7)
    elif len(desc) < 70 or len(desc) > 170:
        issue("low", "طول Meta Description نامناسب است", f"{len(desc)} کاراکتر.", 3)
    else:
        passed("Meta Description", f"{len(desc)} کاراکتر.")

    if len(h1) == 0:
        issue("high", "H1 وجود ندارد", "هیچ H1 پیدا نشد.", 8)
    elif len(h1) > 1:
        issue("medium", "چند H1 وجود دارد", f"{len(h1)} عدد.", 4)
    else:
        passed("H1", "یک H1 وجود دارد.")

    if not h2:
        issue("low", "H2 وجود ندارد", "ساختار هدینگ ضعیف یا نامشخص است.", 2)
    else:
        passed("H2", f"{len(h2)} عدد.")

    if not viewport:
        issue("high", "Viewport موبایل وجود ندارد", "تگ viewport پیدا نشد.", 8)
    else:
        passed("Mobile Viewport", "وجود دارد.")

    if not canonical:
        issue("medium", "Canonical وجود ندارد", "تگ canonical پیدا نشد.", 5)
    else:
        passed("Canonical", "وجود دارد.")

    if not robots or robots.status_code >= 400:
        issue("medium", "robots.txt پیدا نشد", "فایل robots.txt در دسترس نیست.", 4)
    else:
        passed("robots.txt", "در دسترس است.")

    if not sitemap or sitemap.status_code >= 400:
        issue("medium", "sitemap.xml پیدا نشد", "فایل sitemap.xml در دسترس نیست.", 4)
    else:
        passed("Sitemap", "در دسترس است.")

    if images and missing_alt:
        issue("medium", "تصاویر بدون ALT", f"{len(missing_alt)} از {len(images)} تصویر.", min(8, 2 + len(missing_alt)))
    elif images:
        passed("Image ALT", "همه تصاویر ALT دارند.")

    if words < 300:
        issue("medium", "محتوای متنی کم است", f"حدود {words} کلمه.", 7)
    elif words >= 700:
        passed("Content Volume", f"حدود {words} کلمه.")
    else:
        issue("low", "حجم محتوا متوسط است", f"حدود {words} کلمه.", 2)

    if not schemas:
        issue("low", "Schema پیدا نشد", "JSON-LD پیدا نشد.", 3)
    else:
        passed("Schema", f"{len(schemas)} بلوک JSON-LD.")

    if elapsed > 3:
        issue("high", "پاسخ اولیه کند است", f"{elapsed} ثانیه. این جایگزین Core Web Vitals نیست.", 7)
    elif elapsed > 1.5:
        issue("low", "پاسخ اولیه متوسط است", f"{elapsed} ثانیه.", 2)
    else:
        passed("Response Time", f"{elapsed} ثانیه.")

    score = max(0, min(100, score))
    commercial_terms = ["خرید", "فروش", "قیمت", "سفارش", "خدمات", "فروشگاه", "shop", "store", "buy", "price"]
    combined = (title + " " + desc + " " + text[:5000]).lower()
    commercial_signal = sum(1 for x in commercial_terms if x in combined)
    lead = min(100, max(0, 100 - score + min(20, commercial_signal * 3)))
    result.update({
        "seo_score": score, "lead_score": lead, "title": title, "description": desc,
        "metrics": {
            "word_count": words, "h1": len(h1), "h2": len(h2), "images": len(images),
            "missing_alt": len(missing_alt), "schema": len(schemas), "https": parsed.scheme == "https",
            "canonical": bool(canonical), "viewport": bool(viewport),
            "robots": bool(robots and robots.status_code < 400),
            "sitemap": bool(sitemap and sitemap.status_code < 400),
        }
    })
    return result

def discover(keyword, limit=8):
    q = requests.utils.quote(keyword.strip())
    r, _, err = fetch(f"https://html.duckduckgo.com/html/?q={q}", timeout=15)
    if err or not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    urls = []
    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        if href.startswith("http") and "duckduckgo.com" not in urlparse(href).netloc:
            if href not in urls:
                urls.append(href)
        if len(urls) >= limit:
            break
    return urls

st.title("🔎 SEO Lead Finder")
st.caption("کشف سایت های دارای فرصت سئو، Audit و اولویت بندی سرنخ های فروش")

with st.sidebar:
    st.header("تنظیمات")
    limit = st.slider("تعداد نتایج کشف", 3, 15, 8)
    st.info("Lead Score یک امتیاز داخلی برای اولویت بندی فروش است و رتبه گوگل را پیش بینی نمی کند.")

tab1, tab2 = st.tabs(["🚀 کشف مشتری بالقوه", "🧪 Audit مستقیم سایت"])

with tab1:
    keyword = st.text_input("کلمه کلیدی / حوزه هدف", placeholder="مثلا: فروش لباس ورزشی تهران")
    if st.button("🔍 پیدا کردن سایت های هدف", type="primary", use_container_width=True):
        if not keyword.strip():
            st.warning("کلمه کلیدی را وارد کن.")
        else:
            with st.spinner("در حال کشف نتایج عمومی وب و Audit..."):
                urls = discover(keyword, limit)
                results = [audit(u) for u in urls]
            st.session_state.results = results

    results = st.session_state.get("results", [])
    if results:
        c1, c2, c3 = st.columns(3)
        c1.metric("سایت های بررسی شده", len(results))
        c2.metric("🔥 سرنخ داغ", sum(x["lead_score"] >= 70 for x in results))
        c3.metric("🟡 سرنخ متوسط", sum(40 <= x["lead_score"] < 70 for x in results))
        df = pd.DataFrame([{
            "دامنه": urlparse(x["final_url"]).netloc,
            "SEO Score": x["seo_score"],
            "Lead Score": x["lead_score"],
            "مشکلات": len(x["issues"]),
            "Title": x["title"] or "ندارد"
        } for x in results]).sort_values("Lead Score", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ خروجی CSV", df.to_csv(index=False).encode("utf-8-sig"),
                           "seo-leads.csv", "text/csv", use_container_width=True)
        for x in sorted(results, key=lambda z: z["lead_score"], reverse=True):
            with st.expander(f"{x['lead_score']}/100 — {x['final_url']}"):
                st.write(f"**SEO Score:** {x['seo_score']}/100")
                st.write(f"**Title:** {x['title'] or 'ندارد'}")
                for sev, name, detail in x["issues"]:
                    st.write(f"**{sev.upper()} — {name}:** {detail}")

with tab2:
    url = st.text_input("آدرس سایت", placeholder="https://example.com")
    if st.button("🧪 اجرای SEO Audit", type="primary", use_container_width=True):
        if url.strip():
            with st.spinner("در حال بررسی سایت..."):
                st.session_state.audit = audit(url)
        else:
            st.warning("آدرس سایت را وارد کن.")

    x = st.session_state.get("audit")
    if x:
        a, b, c, d = st.columns(4)
        a.metric("SEO Score", f"{x['seo_score']}/100")
        b.metric("Lead Score", f"{x['lead_score']}/100")
        c.metric("Issues", len(x["issues"]))
        d.metric("Response", f"{x['response_time']}s")
        st.write("**URL:**", x["final_url"])
        st.write("**Title:**", x["title"] or "ندارد")
        st.write("**Meta Description:**", x["description"] or "ندارد")
        m = x["metrics"]
        cols = st.columns(5)
        for col, label, val in zip(cols, ["کلمات","H1","H2","تصاویر بدون ALT","Schema"],
                                   [m["word_count"],m["h1"],m["h2"],m["missing_alt"],m["schema"]]):
            col.metric(label, val)
        st.subheader("🚨 مشکلات قابل فروش")
        if not x["issues"]:
            st.success("مشکل مهمی در این بررسی اولیه پیدا نشد.")
        for sev, name, detail in x["issues"]:
            st.error(f"**{sev.upper()} — {name}**: {detail}")
        st.subheader("✅ موارد سالم")
        for name, detail in x["passed"]:
            st.write(f"✓ **{name}** — {detail}")
        report = pd.DataFrame([{"URL": x["final_url"], "SEO Score": x["seo_score"],
                                "Lead Score": x["lead_score"], **x["metrics"]}])
        st.download_button("⬇️ دانلود گزارش CSV", report.to_csv(index=False).encode("utf-8-sig"),
                           "seo-audit.csv", "text/csv")

st.divider()
st.caption("MVP واقعی. برای نسخه حرفه ای می توان PageSpeed Insights، SERP API، Playwright، PostgreSQL، PDF و CRM را اضافه کرد.")

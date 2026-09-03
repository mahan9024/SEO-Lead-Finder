import re
import time
import urllib.parse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


st.set_page_config(
    page_title="SEO Lead Finder",
    page_icon="🔎",
    layout="wide"
)

USER_AGENT = "Mozilla/5.0 (SEO Lead Finder)"


def normalize_url(url):
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def fetch(url, timeout=15):
    headers = {"User-Agent": USER_AGENT}
    return requests.get(
        url,
        headers=headers,
        timeout=timeout,
        allow_redirects=True
    )


def word_count(text):
    return len(re.findall(r"\b\w+\b", text or ""))


def audit(url):
    url = normalize_url(url)

    result = {
        "URL": url,
        "Status": "❌",
        "HTTP": "",
        "HTTPS": "❌",
        "Title": "❌",
        "Meta Description": "❌",
        "H1": "❌",
        "H2": "❌",
        "Viewport": "❌",
        "Canonical": "❌",
        "Robots.txt": "❌",
        "Sitemap": "❌",
        "Images ALT": "❌",
        "Word Count": 0,
        "Schema": "❌",
        "Response Time": 0,
        "SEO Score": 0,
        "Lead Score": 0,
    }

    start = time.time()

    try:
        response = fetch(url)
        elapsed = round(time.time() - start, 2)

        result["Response Time"] = elapsed
        result["HTTP"] = response.status_code

        if response.status_code >= 400:
            result["Status"] = "❌"
            return result

        result["Status"] = "✅"

        if url.startswith("https://"):
            result["HTTPS"] = "✅"

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.find("title")
        if title and title.get_text(strip=True):
            result["Title"] = "✅"

        meta = soup.find(
            "meta",
            attrs={"name": re.compile("^description$", re.I)}
        )
        if meta and meta.get("content"):
            result["Meta Description"] = "✅"

        if soup.find("h1"):
            result["H1"] = "✅"

        if soup.find("h2"):
            result["H2"] = "✅"

        viewport = soup.find(
            "meta",
            attrs={"name": re.compile("^viewport$", re.I)}
        )
        if viewport:
            result["Viewport"] = "✅"

        canonical = soup.find(
            "link",
            attrs={"rel": lambda x: x and "canonical" in x}
        )
        if canonical:
            result["Canonical"] = "✅"

        text = soup.get_text(" ", strip=True)
        result["Word Count"] = word_count(text)

        images = soup.find_all("img")

        if images:
            without_alt = [
                img for img in images
                if not img.get("alt", "").strip()
            ]

            if len(without_alt) == 0:
                result["Images ALT"] = "✅"
            elif len(without_alt) < len(images):
                result["Images ALT"] = "⚠️"
        else:
            result["Images ALT"] = "✅"

        robots_url = urllib.parse.urljoin(url + "/", "robots.txt")
        sitemap_url = urllib.parse.urljoin(url + "/", "sitemap.xml")

        try:
            robots = fetch(robots_url, timeout=8)
            if robots.status_code == 200:
                result["Robots.txt"] = "✅"
        except Exception:
            pass

        try:
            sitemap = fetch(sitemap_url, timeout=8)
            if sitemap.status_code == 200:
                result["Sitemap"] = "✅"
        except Exception:
            pass

        schema = soup.find_all(
            "script",
            attrs={"type": "application/ld+json"}
        )

        if schema:
            result["Schema"] = "✅"

        score_items = [
            result["HTTPS"] == "✅",
            result["Title"] == "✅",
            result["Meta Description"] == "✅",
            result["H1"] == "✅",
            result["H2"] == "✅",
            result["Viewport"] == "✅",
            result["Canonical"] == "✅",
            result["Robots.txt"] == "✅",
            result["Sitemap"] == "✅",
            result["Images ALT"] == "✅",
            result["Schema"] == "✅",
        ]

        result["SEO Score"] = round(
            sum(score_items) / len(score_items) * 100
        )

        lead_score = 100 - result["SEO Score"]

        if result["Word Count"] < 300:
            lead_score += 10

        if result["Response Time"] > 3:
            lead_score += 5

        result["Lead Score"] = min(100, max(0, round(lead_score)))

        return result

    except requests.exceptions.Timeout:
        result["Status"] = "⏱️ Timeout"
        return result

    except requests.exceptions.RequestException:
        result["Status"] = "🌐 خطا در اتصال"
        return result

    except Exception:
        result["Status"] = "⚠️ خطای ناشناخته"
        return result


def discover(keyword):
    keyword = keyword.strip()

    if not keyword:
        return [], "⚠️ لطفا یک کلمه کلیدی وارد کنید."

    query = urllib.parse.quote_plus(keyword)

    search_url = (
        "https://html.duckduckgo.com/html/?q="
        + query
    )

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(
            search_url,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            return [], (
                f"❌ موتور جستجو پاسخ مناسب نداد. "
                f"کد وضعیت: {response.status_code}"
            )

        soup = BeautifulSoup(response.text, "html.parser")

        urls = []

        for link in soup.select("a.result__a"):
            href = link.get("href")

            if not href:
                continue

            if href.startswith("http"):
                clean_url = href.split("?")[0]

                if clean_url not in urls:
                    urls.append(clean_url)

        if not urls:
            return [], (
                "⚠️ نتیجه‌ای پیدا نشد. "
                "کلمه کلیدی دیگری امتحان کنید."
            )

        return urls[:10], f"✅ تعداد {len(urls[:10])} سایت پیدا شد."

    except requests.exceptions.Timeout:
        return [], "⏱️ زمان اتصال به موتور جستجو تمام شد."

    except requests.exceptions.RequestException as e:
        return [], f"🌐 خطا در اتصال به موتور جستجو: {e}"

    except Exception as e:
        return [], f"⚠️ خطا: {e}"


st.title("🔎 SEO Lead Finder")
st.write(
    "پیدا کردن سایت‌های هدف و بررسی وضعیت سئوی آنها"
)

if "results" not in st.session_state:
    st.session_state.results = None

if "audit" not in st.session_state:
    st.session_state.audit = None


tab1, tab2 = st.tabs([
    "🚀 کشف مشتری بالقوه",
    "🧪 Audit مستقیم سایت"
])


with tab1:

    st.subheader("🚀 پیدا کردن سایت‌های هدف")

    keyword = st.text_input(
        "کلمه کلیدی یا حوزه کاری",
        placeholder="مثلا: طراحی سایت، فروشگاه موبایل، آموزشگاه زبان",
        key="keyword_input"
    )

    search_button = st.button(
        "🔍 پیدا کردن سایت‌های هدف",
        type="primary",
        key="discover_button"
    )

    if search_button:

        if not keyword.strip():
            st.warning("⚠️ ابتدا یک کلمه کلیدی وارد کنید.")

        else:

            with st.spinner("🔎 در حال جستجو..."):
                urls, message = discover(keyword)

            st.info(message)

            if urls:

                data = []

                progress = st.progress(0)

                for i, url in enumerate(urls):

                    audit_result = audit(url)

                    data.append({
                        "سایت": url,
                        "وضعیت": audit_result["Status"],
                        "SEO Score": audit_result["SEO Score"],
                        "Lead Score": audit_result["Lead Score"],
                        "HTTPS": audit_result["HTTPS"],
                        "Title": audit_result["Title"],
                        "Meta": audit_result["Meta Description"],
                        "H1": audit_result["H1"],
                        "سرعت": audit_result["Response Time"],
                    })

                    progress.progress((i + 1) / len(urls))

                progress.empty()

                st.session_state.results = pd.DataFrame(data)

                st.success(
                    f"✅ بررسی {len(data)} سایت انجام شد."
                )


    if st.session_state.results is not None:

        st.subheader("📊 نتایج")

        st.dataframe(
            st.session_state.results,
            use_container_width=True,
            hide_index=True
        )

        csv = st.session_state.results.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "⬇️ دانلود نتایج CSV",
            data=csv,
            file_name="seo_leads.csv",
            mime="text/csv",
            key="download_leads"
        )


with tab2:

    st.subheader("🧪 بررسی مستقیم سایت")

    audit_url = st.text_input(
        "آدرس سایت",
        placeholder="example.com",
        key="audit_url_input"
    )

    audit_button = st.button(
        "🧪 اجرای SEO Audit",
        type="primary",
        key="audit_button"
    )

    if audit_button:

        if not audit_url.strip():
            st.warning("⚠️ ابتدا آدرس سایت را وارد کنید.")

        else:

            with st.spinner("🧪 در حال بررسی سایت..."):

                result = audit(audit_url)

            st.session_state.audit = result

            if result["Status"] == "✅":
                st.success("✅ بررسی سایت با موفقیت انجام شد.")
            else:
                st.error(
                    f"❌ بررسی سایت کامل نشد. وضعیت: "
                    f"{result['Status']}"
                )


    if st.session_state.audit is not None:

        result = st.session_state.audit

        st.subheader("📋 نتیجه SEO Audit")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "SEO Score",
            f"{result['SEO Score']}/100"
        )

        col2.metric(
            "Lead Score",
            f"{result['Lead Score']}/100"
        )

        col3.metric(
            "سرعت پاسخ",
            f"{result['Response Time']} ثانیه"
        )

        st.divider()

        audit_df = pd.DataFrame([
            {
                "شاخص": key,
                "نتیجه": value
            }
            for key, value in result.items()
            if key not in [
                "URL",
                "SEO Score",
                "Lead Score",
                "Response Time"
            ]
        ])

        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True
        )

        audit_csv = audit_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "⬇️ دانلود گزارش Audit",
            data=audit_csv,
            file_name="seo_audit.csv",
            mime="text/csv",
            key="download_audit"
        )


st.divider()

st.caption(
    "SEO Lead Finder | ابزار بررسی اولیه سئو و کشف مشتری بالقوه"
)

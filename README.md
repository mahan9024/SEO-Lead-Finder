# SEO Lead Finder

ابزار MVP برای کارشناس سئو جهت کشف سایت های هدف، اجرای SEO Audit اولیه و اولویت بندی Leadها.

## امکانات فعلی
- کشف سایت بر اساس کلمه کلیدی با نتایج عمومی وب
- Audit مستقیم URL
- SEO Score از 100
- Lead Score برای اولویت بندی فروش
- بررسی Title، Meta Description، H1/H2، HTTPS، Viewport، Canonical، robots.txt، sitemap.xml، ALT، حجم محتوا، Schema و زمان پاسخ
- خروجی CSV
- رابط کاربری Streamlit و مناسب موبایل/دسکتاپ

## اجرا
```bash
pip install -r requirements.txt
streamlit run app.py
```

> Lead Score پیش بینی رتبه گوگل نیست. برای نسخه تولیدی، اتصال به SERP API و PageSpeed Insights و یک crawler کنترل شده توصیه می شود.

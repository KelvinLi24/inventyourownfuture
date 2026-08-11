#!/usr/bin/env python3
"""Migrate Chrome-saved Squarespace pages into a deployable static site."""

from __future__ import annotations

import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "IYOF Website"
PAGES_DIR = ROOT / "pages"
ASSETS_DIR = ROOT / "assets"
REPORTS_DIR = ROOT / "reports"

SITE_DOMAIN = "www.inventyourownfuture.com"
INTERNAL_HOSTS = {SITE_DOMAIN, "inventyourownfuture.com", "chrysalis-plantain-z2mp.squarespace.com"}

TEXT_EXTS = {".html", ".css", ".js", ".json", ".txt", ".svg", ".xml"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
FONT_EXTS = {".woff", ".woff2", ".ttf", ".otf", ".eot"}
ICON_EXTS = {".ico", ".svg"}
MEDIA_EXTS = {".mp4", ".webm", ".mov", ".mp3", ".wav", ".m4a", ".pdf"}

DROP_FILE_PATTERNS = (
    "visitor-site-error-reporter",
    "user-account-core",
    "recaptcha",
    "enterprise.js",
    "anchor.html",
    "saved_resource",
    "styles__ltr.css",
    ".ds_store",
)

DROP_SCRIPT_SRC_PATTERNS = (
    "visitor-site-error-reporter",
    "user-account-core",
    "recaptcha",
    "enterprise.js",
    "legacy.js",
    "modern.js",
    "site-bundle",
    "common-vendors",
    "common-75ed",
    "cldr-resource-pack",
    "extract-css-runtime",
    "extract-css-moment",
    "performance-",
    "squarespace.com",
    "squarespace-cdn.com",
)

DROP_INLINE_SCRIPT_PATTERNS = (
    "Static.SQUARESPACE_CONTEXT",
    "YUI",
    "SQUARESPACE_CONTEXT",
    "google-analytics",
    "googletagmanager",
    "gtag(",
    "facebookAppId",
)

DROP_LINK_PATTERNS = (
    "user-account-core",
    "preconnect",
    "squarespace.com",
    "squarespace-cdn.com",
)

DROP_TAG_PATTERNS = (
    "grecaptcha-badge",
    "chrome-extension://",
    "<shark-icon-container",
    "</shark-icon-container>",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(value: str, fallback: str = "asset") -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = unquote(value)
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"['`]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or fallback


def clean_asset_stem(path: Path) -> str:
    stem = unquote(path.stem)
    stem = re.sub(r"\+\(\d+\)$", "", stem)
    stem = re.sub(r"\(\d+\)$", "", stem)
    stem = stem.replace("+", " ")
    stem = stem.replace("_", " ")
    return slugify(stem, "asset")


def asset_category(path: Path) -> str:
    ext = path.suffix.lower()
    name = path.name.lower()
    if ext in FONT_EXTS:
        return "fonts"
    if ext in IMAGE_EXTS:
        return "images"
    if ext in ICON_EXTS or "favicon" in name:
        return "icons"
    if ext in MEDIA_EXTS:
        return "media"
    if ext == ".css":
        return "css/vendor"
    if ext == ".js":
        return "js/vendor"
    return "misc"


def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    i = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{i}{suffix}"
        i += 1
    return candidate


def is_dropped_asset(path: Path) -> bool:
    lower = path.name.lower()
    return any(pattern in lower for pattern in DROP_FILE_PATTERNS)


def discover_pages() -> list[Path]:
    return sorted(SOURCE.glob("*.html"))


def page_slug(path: Path) -> str:
    title = path.stem.replace(" — Invent Your Own Future", "")
    if title == "Invent Your Own Future":
        return "index"
    known = {
        "About Us": "about-us",
        "Contact Us": "contact",
        "Career Blog": "career-blog",
        "Upcoming Events": "upcoming",
        "Events and Camps": "events-and-camps",
        "Internship Opportunities": "internship-opportunities",
        "Student Ambassador": "student-ambassador",
        "Alumni Network": "alumni-network",
    }
    return known.get(title, slugify(title, "page"))


def output_page_path(path: Path) -> Path:
    slug = page_slug(path)
    if slug == "index":
        return ROOT / "index.html"
    return PAGES_DIR / f"{slug}.html"


def build_route_map(pages: list[Path]) -> dict[str, Path]:
    routes: dict[str, Path] = {}
    for page in pages:
        slug = page_slug(page)
        out = output_page_path(page)
        title_slug = slugify(page.stem.replace(" — Invent Your Own Future", ""), "page")
        text = page.read_text(encoding="utf-8", errors="ignore")
        canonical_routes = set()
        for match in re.finditer(r"<link\b[^>]*rel=[\"']canonical[\"'][^>]*href=[\"']https?://www\.inventyourownfuture\.com([^\"']*)[\"']", text[:20000], flags=re.I):
            canonical_routes.add(match.group(1).rstrip("/") or "/")
        saved = re.search(r"saved from url=\(\d+\)https?://www\.inventyourownfuture\.com([^ ]*)", text[:500], flags=re.I)
        if saved:
            canonical_routes.add(saved.group(1).rstrip("/") or "/")
        for route in {slug, title_slug, f"{slug}.html", f"{title_slug}.html", f"career-blog/{slug}", f"career-blog/{title_slug}"}:
            routes[f"/{route}".rstrip("/")] = out
            routes[f"https://{SITE_DOMAIN}/{route}".rstrip("/")] = out
            routes[f"http://{SITE_DOMAIN}/{route}".rstrip("/")] = out
        for route in canonical_routes:
            routes[route] = out
            routes[f"https://{SITE_DOMAIN}{route}".rstrip("/")] = out
            routes[f"http://{SITE_DOMAIN}{route}".rstrip("/")] = out
        if slug == "index":
            routes["/"] = ROOT / "index.html"
            routes[f"https://{SITE_DOMAIN}"] = ROOT / "index.html"
            routes[f"https://{SITE_DOMAIN}/"] = ROOT / "index.html"
            routes[f"http://{SITE_DOMAIN}"] = ROOT / "index.html"
            routes[f"http://{SITE_DOMAIN}/"] = ROOT / "index.html"
    # Legacy footer typo from the downloaded site.
    if "/about-us" in routes:
        routes["/about"] = routes["/about-us"]
        routes[f"https://{SITE_DOMAIN}/about"] = routes["/about-us"]
    if "/student-ambassador" in routes:
        routes["/initiatives"] = routes["/student-ambassador"]
        routes[f"https://{SITE_DOMAIN}/initiatives"] = routes["/student-ambassador"]
    return routes


def rel_link(from_page: Path, to_path: Path) -> str:
    base = from_page.parent
    return Path(os.path.relpath(to_path, base)).as_posix()


def collect_assets() -> tuple[dict[str, str], dict[str, int], dict[str, list[str]]]:
    ASSETS_DIR.mkdir(exist_ok=True)
    local_ref_map: dict[str, str] = {}
    by_hash: dict[str, Path] = {}
    by_basename: dict[str, Path] = {}
    category_counts: Counter[str] = Counter()
    hash_sources: defaultdict[str, list[str]] = defaultdict(list)

    for path in sorted(SOURCE.rglob("*")):
        if not path.is_file() or path.suffix.lower() == ".html":
            continue
        if path.suffix.lower() == ".js" or path.name == ".DS_Store" or is_dropped_asset(path):
            continue

        digest = sha256(path)
        category = asset_category(path)
        target_dir = ASSETS_DIR / category
        target_dir.mkdir(parents=True, exist_ok=True)

        if digest in by_hash:
            target = by_hash[digest]
        else:
            suffix = path.suffix.lower()
            stem = clean_asset_stem(path)
            target = unique_path(target_dir, stem, suffix)
            shutil.copy2(path, target)
            by_hash[digest] = target
            category_counts[category] += 1

        hash_sources[digest].append(str(path.relative_to(ROOT)))
        rel_from_root = target.relative_to(ROOT).as_posix()
        relative_key = path.relative_to(ROOT).as_posix()
        local_ref_map[relative_key] = rel_from_root
        local_ref_map[unquote(relative_key)] = rel_from_root
        local_ref_map[path.as_posix()] = rel_from_root
        local_ref_map[path.name] = rel_from_root
        local_ref_map[unquote(path.name)] = rel_from_root
        by_basename[path.name.lower()] = target

    # Add basename-only aliases after all assets are known. Prefer first copied canonical asset.
    for lower_name, target in by_basename.items():
        local_ref_map[lower_name] = target.relative_to(ROOT).as_posix()

    duplicate_groups = {
        digest: sources for digest, sources in hash_sources.items() if len(sources) > 1
    }
    return local_ref_map, dict(category_counts), duplicate_groups


def normalize_url_token(raw: str) -> str:
    return html.unescape(raw.strip().strip('"').strip("'"))


def external_to_local(raw: str, asset_map: dict[str, str]) -> str | None:
    value = normalize_url_token(raw)
    if not value or value.startswith(("data:", "mailto:", "tel:", "#")):
        return None
    parsed = urlparse(value if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value) else f"https:{value}" if value.startswith("//") else value)
    candidate_names = []
    if parsed.path:
        basename = unquote(Path(parsed.path).name)
        candidate_names.extend([basename, basename.replace(" ", "+")])
        candidate_names.append(basename.replace("%2B", "+"))
    for name in candidate_names:
        if name in asset_map:
            return asset_map[name]
        if name.lower() in asset_map:
            return asset_map[name.lower()]
    return None


def local_to_asset(raw: str, current_source: Path, asset_map: dict[str, str]) -> str | None:
    value = normalize_url_token(raw)
    if not value or value.startswith(("data:", "mailto:", "tel:", "#", "javascript:")):
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} or value.startswith("//"):
        return external_to_local(value, asset_map)
    if parsed.scheme:
        return None
    path_part = unquote(parsed.path)
    if not path_part:
        return None
    full = (current_source.parent / path_part).resolve()
    try:
        key = full.relative_to(ROOT).as_posix()
    except ValueError:
        key = path_part
    return asset_map.get(key) or asset_map.get(Path(path_part).name) or asset_map.get(Path(path_part).name.lower())


def rebase_asset(raw: str, current_source: Path, output_page: Path, asset_map: dict[str, str]) -> str:
    local = local_to_asset(raw, current_source, asset_map)
    if not local:
        return raw
    return rel_link(output_page, ROOT / local)


def rebase_srcset(raw: str, current_source: Path, output_page: Path, asset_map: dict[str, str]) -> str:
    candidates = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        bits = item.split()
        url = bits[0]
        descriptor = " ".join(bits[1:])
        local = rebase_asset(url, current_source, output_page, asset_map)
        if local == url and re.match(r"^https?://|^//", url):
            continue
        candidates.append(f"{local} {descriptor}".strip())
    return ", ".join(dict.fromkeys(candidates))


def rebase_css_urls(text: str, current_source: Path, output_page: Path, asset_map: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        quote = match.group(1) or ""
        value = match.group(2)
        local = rebase_asset(value, current_source, output_page, asset_map)
        return f"url({quote}{local}{quote})"

    return re.sub(r"url\((['\"]?)([^)'\"\s]+)\1\)", repl, text)


def map_internal_href(raw: str, output_page: Path, route_map: dict[str, Path]) -> str | None:
    value = html.unescape(raw.strip())
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlparse(value)
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc not in INTERNAL_HOSTS:
            return None
        key = parsed.path.rstrip("/") or "/"
    elif value.startswith("/"):
        key = parsed.path.rstrip("/") or "/"
    else:
        key = "/" + parsed.path.rstrip("/")
    if key in route_map:
        return rel_link(output_page, route_map[key]) + fragment
    if parsed.scheme in {"http", "https"} and parsed.netloc in INTERNAL_HOSTS:
        return "#"
    if value.startswith("/"):
        return "#"
    return None


def clean_head_markup(markup: str, output_page: Path) -> str:
    markup = re.sub(r"<!-- saved from url=.*?-->\s*", "", markup, flags=re.S)
    markup = re.sub(r"<base\b[^>]*>\s*", "", markup, flags=re.I)
    markup = re.sub(r"<meta\s+http-equiv=[\"']Accept-CH[\"'][^>]*>\s*", "", markup, flags=re.I)
    markup = re.sub(r"<meta\s+http-equiv=[\"']origin-trial[\"'][^>]*>\s*", "", markup, flags=re.I)
    markup = re.sub(r"<link\b[^>]+rel=[\"']preconnect[\"'][^>]*>\s*", "", markup, flags=re.I)
    markup = re.sub(r"<!-- This is Squarespace\. -->.*?\n", "", markup, flags=re.I | re.S)
    markup = re.sub(r"<style\b[^>]*data-sqsp-font-ids=[\"'][^\"']*[\"'][\s\S]*?</style>", "", markup, flags=re.I)
    return markup


def drop_unwanted_tags(markup: str) -> str:
    markup = re.sub(r"<script\b(?:(?!</script>).)*?</script>", "", markup, flags=re.I | re.S)
    markup = re.sub(r"<link\b[^>]*>", drop_link_tag, markup, flags=re.I | re.S)
    markup = re.sub(r"<div\b[^>]*class=[\"'][^\"']*grecaptcha-badge[^\"']*[\"'][\s\S]*?</div>\s*</div>", "", markup, flags=re.I)
    markup = re.sub(r"<div><div\b[^>]*class=[\"'][^\"']*grecaptcha-badge[^\"']*[\"'][\s\S]*?</div></div>", "", markup, flags=re.I)
    markup = re.sub(r"<iframe\b[^>]*saved_resource[^>]*>\s*</iframe>", "", markup, flags=re.I)
    markup = re.sub(r"<iframe\b[^>]*(?:anchor\.html|recaptcha|google\.com/recaptcha)[^>]*>\s*</iframe>", "", markup, flags=re.I)
    markup = re.sub(r"<shark-icon-container\b[\s\S]*?</shark-icon-container>", "", markup, flags=re.I)
    markup = re.sub(r"<template\b[^>]*shadowrootmode=[\"']open[\"'][\s\S]*?</template>", "", markup, flags=re.I)
    markup = markup.replace('<div id="yui3-css-stamp" style="position: absolute !important; visibility: hidden !important"></div>', "")
    return markup


def drop_script_tag(match: re.Match[str]) -> str:
    return ""


def drop_inline_script_tag(match: re.Match[str]) -> str:
    return ""


def drop_link_tag(match: re.Match[str]) -> str:
    tag = match.group(0)
    lower = tag.lower()
    if any(pattern in lower for pattern in DROP_LINK_PATTERNS):
        return ""
    return tag


def rewrite_attrs(markup: str, source_page: Path, output_page: Path, asset_map: dict[str, str], route_map: dict[str, Path]) -> str:
    asset_attrs = {
        "src",
        "data-src",
        "data-image",
        "href",
        "content",
        "poster",
        "data-url",
    }

    def attr_repl(match: re.Match[str]) -> str:
        name = match.group(1)
        quote = match.group(2)
        value = match.group(3)
        lower_value = html.unescape(value).lower()
        if name.lower() == "href":
            mapped = map_internal_href(value, output_page, route_map)
            if mapped:
                return f'{name}={quote}{html.escape(mapped, quote=True)}{quote}'
        if name.lower() == "srcset":
            mapped_srcset = rebase_srcset(value, source_page, output_page, asset_map)
            return f'{name}={quote}{html.escape(mapped_srcset, quote=True)}{quote}'
        if name.lower() in asset_attrs:
            mapped = rebase_asset(value, source_page, output_page, asset_map)
            if mapped != value:
                return f'{name}={quote}{html.escape(mapped, quote=True)}{quote}'
            if "squarespace-cdn.com" in lower_value or "static1.squarespace.com" in lower_value:
                fallback = rel_link(output_page, ROOT / "assets/images/invent.png")
                return f'{name}={quote}{html.escape(fallback, quote=True)}{quote}'
        return match.group(0)

    markup = re.sub(r"\sdata-block-(?:css|scripts)=([\"']).*?\1", "", markup, flags=re.I | re.S)
    markup = re.sub(r"\b(srcset)=([\"'])(.*?)\2", attr_repl, markup, flags=re.I | re.S)
    markup = re.sub(r"\b(src|data-src|data-image|href|content|poster|data-url)=([\"'])(.*?)\2", attr_repl, markup, flags=re.I | re.S)
    markup = re.sub(r"(/universal/svg/social-accounts\.svg#)", "#", markup)
    markup = rebase_css_urls(markup, source_page, output_page, asset_map)
    fallback = rel_link(output_page, ROOT / "assets/images/invent.png")
    markup = re.sub(r"https?://images\.squarespace-cdn\.com[^\"'<>\s,)]+", fallback, markup)
    markup = re.sub(r"https?://static1\.squarespace\.com[^\"'<>\s,)]+", fallback, markup)
    markup = re.sub(r"https?://(?:www\.)?inventyourownfuture\.com/(?:cart|config)[^\"'<>\s)]*", "#", markup)
    return markup


def add_static_assets(markup: str, output_page: Path) -> str:
    css_href = rel_link(output_page, ROOT / "assets/css/static-site.css")
    js_src = rel_link(output_page, ROOT / "assets/js/main.js")
    favicon = rel_link(output_page, ROOT / "assets/images/invent.png")
    head_inserts = (
        f'<link rel="icon" type="image/png" href="{favicon}">\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700&family=Poppins:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">\n'
        f'<link rel="stylesheet" href="{css_href}">\n'
    )
    markup = re.sub(r"</head>", head_inserts + "</head>", markup, count=1, flags=re.I)
    markup = re.sub(r"</body>", f'<script src="{js_src}" defer></script>\n</body>', markup, count=1, flags=re.I)
    return markup


def ensure_html_basics(markup: str) -> str:
    if not markup.lstrip().lower().startswith("<!doctype html>"):
        markup = "<!DOCTYPE html>\n" + markup
    markup = re.sub(r"<html\b[^>]*>", '<html lang="en-CA">', markup, count=1, flags=re.I)
    if '<meta charset="utf-8">' not in markup.lower():
        markup = re.sub(r"<head>", '<head>\n<meta charset="utf-8">', markup, count=1, flags=re.I)
    markup = re.sub(r"<meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\">\s*", "", markup, flags=re.I)
    return markup


def rewrite_page(source_page: Path, output_page: Path, asset_map: dict[str, str], route_map: dict[str, Path]) -> dict[str, int]:
    text = source_page.read_text(encoding="utf-8", errors="ignore")
    text = clean_head_markup(text, output_page)
    text = drop_unwanted_tags(text)
    text = rewrite_attrs(text, source_page, output_page, asset_map, route_map)
    text = ensure_html_basics(text)
    text = add_static_assets(text, output_page)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    output_page.parent.mkdir(parents=True, exist_ok=True)
    output_page.write_text(text, encoding="utf-8")
    return {
        "scripts": len(re.findall(r"<script\b", text, flags=re.I)),
        "stylesheets": len(re.findall(r"<link\b[^>]+stylesheet", text, flags=re.I)),
        "images": len(re.findall(r"<img\b", text, flags=re.I)),
    }


def write_static_css() -> None:
    path = ASSETS_DIR / "css" / "static-site.css"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """/* Static-site compatibility layer for the migrated Squarespace export. */
html {
  scroll-behavior: smooth;
}

body.static-site-ready .preFade,
body.static-site-ready .preScale,
body.static-site-ready .preSlide,
body.static-site-ready .preClip {
  opacity: 1 !important;
  transform: none !important;
  clip-path: none !important;
}

img {
  max-width: 100%;
}

.header-menu {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  transition: opacity 180ms ease;
}

body.header-menu-open .header-menu,
.header-menu.menu-open {
  visibility: visible;
  opacity: 1;
  pointer-events: auto;
}

body.header-menu-open {
  overflow: hidden;
}

.header-menu-controls,
.header-menu-nav-folder {
  transition: opacity 180ms ease, transform 180ms ease;
}

.static-form-message {
  margin-top: 1rem;
  font-size: 0.95rem;
}
""",
        encoding="utf-8",
    )


def sanitize_copied_css() -> None:
    css_dir = ASSETS_DIR / "css"
    if not css_dir.exists():
        return
    for path in css_dir.rglob("*.css"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"url\((['\"]?)/universal/[^)'\"\s]+\1\)", "url('data:,')", text)
        text = re.sub(r"url\((['\"]?)https?://(?:[^)'\"\s]*squarespace[^)'\"\s]*)\1\)", "url('data:,')", text)
        text = re.sub(r"url\((['\"]?)//(?:[^)'\"\s]*squarespace[^)'\"\s]*)\1\)", "url('data:,')", text)
        text = re.sub(r"@font-face\s*\{[^{}]*squarespace[^{}]*\}", "", text, flags=re.I)
        path.write_text(text, encoding="utf-8")


def write_static_js() -> None:
    path = ASSETS_DIR / "js" / "main.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """(() => {
  document.documentElement.classList.add('js');

  const ready = () => {
    document.body.classList.add('static-site-ready');
    wireMobileMenu();
    wireFolders();
    wireForms();
    wireLazyImages();
  };

  const wireMobileMenu = () => {
    const toggles = document.querySelectorAll('.header-burger-btn, .burger, [data-test="header-burger"]');
    const menu = document.querySelector('.header-menu');
    if (!toggles.length || !menu) return;

    const setOpen = (open) => {
      document.body.classList.toggle('header-menu-open', open);
      menu.classList.toggle('menu-open', open);
      toggles.forEach((toggle) => {
        toggle.setAttribute('aria-expanded', String(open));
      });
    };

    toggles.forEach((toggle) => {
      toggle.setAttribute('aria-controls', menu.id || 'header-menu');
      toggle.addEventListener('click', (event) => {
        event.preventDefault();
        setOpen(!document.body.classList.contains('header-menu-open'));
      });
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') setOpen(false);
    });

    menu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => setOpen(false));
    });
  };

  const wireFolders = () => {
    document.querySelectorAll('.header-nav-folder-title, [data-folder-id], [data-action="back"]').forEach((control) => {
      control.addEventListener('click', (event) => {
        const targetId = control.getAttribute('aria-controls') || control.getAttribute('data-folder-id');
        if (!targetId) return;
        const folder = document.getElementById(targetId.replace(/^\\//, '')) || document.querySelector(`[data-folder="${targetId}"]`);
        if (!folder) return;
        event.preventDefault();
        const expanded = control.getAttribute('aria-expanded') === 'true';
        control.setAttribute('aria-expanded', String(!expanded));
        folder.hidden = expanded;
      });
    });
  };

  const wireForms = () => {
    document.querySelectorAll('form.react-form-contents, form').forEach((form) => {
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        let message = form.querySelector('.static-form-message');
        if (!message) {
          message = document.createElement('p');
          message.className = 'static-form-message';
          form.appendChild(message);
        }
        message.textContent = 'This static copy preserves the form layout. Connect this form to a static form provider before publishing submissions.';
      });
    });
  };

  const wireLazyImages = () => {
    document.querySelectorAll('img[data-src]:not([src])').forEach((img) => {
      img.src = img.getAttribute('data-src');
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ready);
  } else {
    ready();
  }
})();
""",
        encoding="utf-8",
    )


def generate_dependency_report(pages: list[Path], duplicate_groups: dict[str, list[str]], asset_counts: dict[str, int]) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    report = {
        "source_directory": str(SOURCE.relative_to(ROOT)),
        "page_count": len(pages),
        "pages": [],
        "asset_counts": asset_counts,
        "duplicate_asset_groups": len(duplicate_groups),
        "duplicate_source_files": sum(len(v) - 1 for v in duplicate_groups.values()),
    }
    url_pattern = re.compile(r"""(?:(?:https?:)?//|mailto:|tel:)[^'"<>\s)]+""")
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="ignore")
        files_dir = SOURCE / f"{page.stem}_files"
        local_assets = sorted(p.name for p in files_dir.glob("*") if p.is_file()) if files_dir.exists() else []
        urls = sorted(set(url_pattern.findall(text)))
        report["pages"].append(
            {
                "source": str(page.relative_to(ROOT)),
                "output": str(output_page_path(page).relative_to(ROOT)),
                "local_asset_count": len(local_assets),
                "local_assets": local_assets,
                "external_domains": sorted(
                    {
                        urlparse(("https:" + u) if u.startswith("//") else u).netloc
                        for u in urls
                        if urlparse(("https:" + u) if u.startswith("//") else u).netloc
                    }
                ),
            }
        )
    (REPORTS_DIR / "dependency-map.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def remove_legacy_source() -> None:
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    ds_store = ROOT / ".DS_Store"
    if ds_store.exists():
        ds_store.unlink()


def remove_source_asset_dirs() -> None:
    for path in SOURCE.glob("*_files"):
        if path.is_dir():
            shutil.rmtree(path)
    for path in SOURCE.glob(".DS_Store"):
        path.unlink()


def main() -> None:
    pages = discover_pages()
    if not pages:
        raise SystemExit("No source HTML pages found.")

    for directory in [PAGES_DIR, ASSETS_DIR, REPORTS_DIR]:
        if directory.exists():
            shutil.rmtree(directory)
    for path in [ROOT / "index.html", ROOT / "README.md"]:
        if path.exists():
            path.unlink()

    asset_map, asset_counts, duplicate_groups = collect_assets()
    remove_source_asset_dirs()
    route_map = build_route_map(pages)
    page_stats = {}
    for page in pages:
        out = output_page_path(page)
        page_stats[str(out.relative_to(ROOT))] = rewrite_page(page, out, asset_map, route_map)

    sanitize_copied_css()
    write_static_css()
    write_static_js()
    generate_dependency_report(pages, duplicate_groups, asset_counts)
    (REPORTS_DIR / "migration-summary.json").write_text(
        json.dumps(
            {
                "pages_migrated": len(pages),
                "page_stats": page_stats,
                "asset_counts": asset_counts,
                "duplicate_asset_groups": len(duplicate_groups),
                "duplicate_source_files": sum(len(v) - 1 for v in duplicate_groups.values()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    remove_legacy_source()


if __name__ == "__main__":
    main()

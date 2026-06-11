import streamlit as st
import pandas as pd
import json
import re
from collections import Counter

st.set_page_config(
    page_title="Archives Jeune Afrique 1980-1989",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Palette ────────────────────────────────────────────────────────────────────
CAT_COLORS = {
    "Politique": "#1E3A5F",
    "Economie":  "#1B5E20",
    "Societe":   "#E65100",
    "Autre":     "#616161",
}
PAYS_COLOR  = "#B71C1C"
PERSO_COLOR = "#4A148C"
ORG_COLOR   = "#006064"

# ── CSS global ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #ffffff; }
    [data-testid="stSidebar"] { display: none; }
    h1, h2, h3 { color: #1E3A5F; font-family: Georgia, serif; }
    .stTextInput > div > input { border-radius: 6px; }
    div[data-testid="stVerticalBlock"] > div > div > div > button {
        background: #1E3A5F !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-size: 12px !important;
    }
    div[data-testid="stVerticalBlock"] > div > div > div > button:hover {
        background: #2a5080 !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Chargement des données ─────────────────────────────────────────────────────
@st.cache_resource
def load_data():
    try:
        df = pd.read_csv("articles_final_v.csv", encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv("articles_final_v.csv", encoding="latin-1")

    def parse_list(val):
        if pd.isna(val) or str(val).strip() in ("", "[]", "null"):
            return []
        try:
            r = json.loads(val)
            return r if isinstance(r, list) else []
        except Exception:
            return []

    df["pays"]          = df["pays"].apply(parse_list)
    df["personnalites"] = df["personnalites"].apply(parse_list)
    df["entreprises"]   = df["entreprises"].apply(parse_list)

    df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")

    df["categorie"] = df["categorie"].fillna("Autre")
    df["categorie"] = df["categorie"].replace({"Société": "Societe"})
    df["categorie"] = df["categorie"].where(df["categorie"].isin(CAT_COLORS), "Autre")

    df["auteur"] = df["auteur"].fillna("").astype(str).str.strip()

    return df


# ── Helpers ─────────────────────────────────────────────────────────────────────
def top_items(series, n=3):
    c = Counter()
    for lst in series:
        c.update(lst)
    return [item for item, _ in c.most_common(n)]


def pill(text, color):
    return (
        f'<span style="background:{color};color:#fff;padding:2px 9px;'
        f'border-radius:12px;font-size:11px;margin:2px;'
        f'display:inline-block;white-space:nowrap;">{text}</span>'
    )


def pill_sm(text, color):
    return (
        f'<span style="background:{color};color:#fff;padding:1px 6px;'
        f'border-radius:10px;font-size:10px;margin:1px;'
        f'display:inline-block;white-space:nowrap;">{text}</span>'
    )


def tag_section(items, color, height_px=90):
    if not items:
        return f'<div style="height:{height_px}px;"><span style="color:#aaa;font-size:10px;">—</span></div>'
    pills = "".join(pill_sm(p, color) for p in items)
    return (
        f'<div style="max-height:{height_px}px;overflow-y:auto;'
        f'padding:2px 0;line-height:1.8;">{pills}</div>'
    )


def mini_bars(cat_counts, total):
    rows = []
    labels = [("Politique", "Pol."), ("Economie", "Éco."), ("Societe", "Soc."), ("Autre", "Aut.")]
    for cat, label in labels:
        n   = cat_counts.get(cat, 0)
        pct = round(n / total * 100) if total else 0
        clr = CAT_COLORS[cat]
        rows.append(
            f'<div style="display:flex;align-items:center;margin-bottom:3px;font-size:10px;">'
            f'<span style="width:28px;color:#666;">{label}</span>'
            f'<div style="flex:1;background:#e9ecef;border-radius:3px;height:7px;margin:0 5px;">'
            f'<div style="width:{pct}%;background:{clr};height:7px;border-radius:3px;"></div>'
            f'</div>'
            f'<span style="width:22px;color:#666;text-align:right;">{n}</span>'
            f'</div>'
        )
    return "".join(rows)


def format_content(text):
    """Normalise le texte OCR en paragraphes HTML propres.

    Stratégie : les doubles sauts de ligne marquent les vrais paragraphes ;
    les sauts simples (coupures OCR en milieu de phrase) sont fusionnés
    en espaces.
    """
    if not text or not str(text).strip():
        return ""
    text = str(text)
    text = re.sub(r'[ \t]+', ' ', text)          # espaces multiples → un seul
    text = re.sub(r'\n{2,}', '\x00', text)        # double NL → marqueur para
    text = re.sub(r'\n', ' ', text)               # NL simple (OCR) → espace
    paragraphs = [p.strip() for p in text.split('\x00') if p.strip()]
    if not paragraphs:
        return ""
    return "".join(
        f'<p style="margin:0 0 1.2em 0;text-align:justify;'
        f'text-indent:1.8em;line-height:1.85;">{p}</p>'
        for p in paragraphs
    )


def article_card(row, key_prefix="art"):
    """Rendu d'une carte article (Vue 2 et Vue auteur)."""
    cat = row["categorie"]
    clr = CAT_COLORS.get(cat, CAT_COLORS["Autre"])

    tags  = pill(cat, clr)
    tags += "".join(pill(p, PAYS_COLOR)  for p in row["pays"][:3])
    tags += "".join(pill(p, PERSO_COLOR) for p in row["personnalites"][:2])
    tags += "".join(pill(p, ORG_COLOR)   for p in row["entreprises"][:1])

    meta_parts = []
    if row.get("auteur") and row["auteur"] not in ("", "nan"):
        meta_parts.append(row["auteur"])
    if pd.notna(row.get("publish_date")) and str(row.get("publish_date")).strip() not in ("", "nan"):
        meta_parts.append(str(row["publish_date"]))
    meta_html = (
        f'<div style="color:#888;font-size:12px;margin:5px 0 10px;">'
        f'{" · ".join(meta_parts)}</div>'
    ) if meta_parts else "<div style='margin-bottom:10px;'></div>"

    chapeau = str(row.get("chapeau", "") or "").strip()
    if chapeau and chapeau != "nan":
        excerpt_src = chapeau
    else:
        contenu = str(row.get("contenu", "") or "").strip()
        excerpt_src = re.sub(r'\s+', ' ', contenu)
    excerpt = (excerpt_src[:230] + "…") if len(excerpt_src) > 230 else excerpt_src
    excerpt_html = (
        f'<div style="color:#4a4a4a;font-size:13px;font-style:italic;'
        f'line-height:1.6;margin-top:2px;">{excerpt}</div>'
    ) if excerpt else ""

    with st.container():
        st.markdown(f"""
        <div style="background:#fff;
                    border:1px solid #e0e0e0;
                    border-left:4px solid {clr};
                    border-radius:0 8px 8px 0;
                    padding:18px 22px 16px;">
          <div style="margin-bottom:10px;">{tags}</div>
          <div style="font-size:17px;font-weight:700;color:#1E3A5F;
                      line-height:1.35;margin-bottom:2px;">{row['titre']}</div>
          {meta_html}
          {excerpt_html}
        </div>
        """, unsafe_allow_html=True)

        _, btn_col = st.columns([9, 3])
        with btn_col:
            if st.button("Lire l'article →", key=f"{key_prefix}_{row['article_id']}", use_container_width=True):
                st.session_state.article_selectionne = row["article_id"]
                st.rerun()

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)


# ── Vue 1 : Dashboard ──────────────────────────────────────────────────────────
def render_dashboard(df):
    # Barre de navigation principale
    nav_col1, nav_col2, _ = st.columns([2, 2, 8])
    with nav_col1:
        if st.button("📅  Par année", key="nav_annee", use_container_width=True):
            st.session_state.vue = "dashboard"
            st.rerun()
    with nav_col2:
        if st.button("✍️  Par auteur", key="nav_auteur", use_container_width=True):
            st.session_state.vue = "auteurs"
            st.rerun()

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    st.markdown("# Archives Jeune Afrique — Décennie 1980")
    st.markdown(
        '<p style="color:#666;font-size:14px;margin-top:-12px;margin-bottom:24px;">'
        'Sélectionnez une année pour explorer les articles.</p>',
        unsafe_allow_html=True,
    )

    for row_start in (1980, 1985):
        cols = st.columns(5, gap="small")
        for i, year in enumerate(range(row_start, row_start + 5)):
            ydf = df[df["annee"] == year]
            n   = len(ydf)

            t_pays  = top_items(ydf["pays"],          n=10)
            t_perso = top_items(ydf["personnalites"], n=10)
            t_orgs  = top_items(ydf["entreprises"],  n=5)

            cat_counts = {c: int((ydf["categorie"] == c).sum()) for c in CAT_COLORS}

            sec_pays  = tag_section(t_pays,  PAYS_COLOR,  height_px=88)
            sec_perso = tag_section(t_perso, PERSO_COLOR, height_px=88)
            sec_orgs  = tag_section(t_orgs,  ORG_COLOR,   height_px=52)

            with cols[i]:
                st.markdown(f"""
                <div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:10px;
                            padding:18px 14px 12px;margin-bottom:6px;">
                  <div style="font-size:40px;font-weight:800;color:#1E3A5F;
                              text-align:center;line-height:1.1;">{year}</div>
                  <div style="text-align:center;color:#888;font-size:12px;
                              margin-bottom:12px;">{n} articles</div>
                  <div style="font-size:10px;color:#999;text-transform:uppercase;
                              letter-spacing:.5px;margin-bottom:3px;">Pays <span style="color:#ccc;font-size:9px;">top 10</span></div>
                  <div style="margin-bottom:8px;">{sec_pays}</div>
                  <div style="font-size:10px;color:#999;text-transform:uppercase;
                              letter-spacing:.5px;margin-bottom:3px;">Personnalités <span style="color:#ccc;font-size:9px;">top 10</span></div>
                  <div style="margin-bottom:8px;">{sec_perso}</div>
                  <div style="font-size:10px;color:#999;text-transform:uppercase;
                              letter-spacing:.5px;margin-bottom:3px;">Organisations <span style="color:#ccc;font-size:9px;">top 5</span></div>
                  <div style="margin-bottom:10px;">{sec_orgs}</div>
                  <div style="border-top:1px solid #dee2e6;padding-top:8px;">
                    {mini_bars(cat_counts, n)}
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"Voir {year}", key=f"btn_{year}", use_container_width=True):
                    st.session_state.annee_selectionnee = year
                    st.session_state.article_selectionne = None
                    st.rerun()

        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)


# ── Vue 2 : Liste des articles d'une année ────────────────────────────────────
def render_year(df, year):
    col_back, col_title = st.columns([1, 9])

    with col_back:
        st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
        if st.button("← Retour", key="back_dash"):
            st.session_state.annee_selectionnee = None
            st.session_state.article_selectionne = None
            st.rerun()

    ydf = df[df["annee"] == year].copy()

    with col_title:
        st.markdown(f"## Année {year} — {len(ydf)} articles")

    search = st.text_input(
        "Recherche",
        placeholder="Rechercher par titre ou auteur…",
        label_visibility="collapsed",
    )

    if search.strip():
        mask = (
            ydf["titre"].str.contains(search, case=False, na=False) |
            ydf["auteur"].str.contains(search, case=False, na=False)
        )
        ydf = ydf[mask]
        st.caption(f"{len(ydf)} résultat(s) pour « {search} »")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    for _, row in ydf.iterrows():
        article_card(row, key_prefix=f"y{year}")


# ── Vue auteurs : liste de tous les auteurs ────────────────────────────────────
def render_authors_list(df):
    col_back, col_title = st.columns([1, 9])

    with col_back:
        st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
        if st.button("← Retour", key="back_dash_aut"):
            st.session_state.vue = "dashboard"
            st.rerun()

    with col_title:
        st.markdown("## Articles par auteur")

    # Exclure les articles sans auteur identifié
    adf = df[df["auteur"].str.len() > 0].copy()

    search = st.text_input(
        "Recherche auteur",
        placeholder="Filtrer par nom d'auteur…",
        label_visibility="collapsed",
    )

    # Calcul des stats par auteur
    stats = []
    for auteur, grp in adf.groupby("auteur"):
        annees = sorted(grp["annee"].dropna().unique().tolist())
        cat_counts = {c: int((grp["categorie"] == c).sum()) for c in CAT_COLORS}
        dominant_cat = max(cat_counts, key=cat_counts.get)
        stats.append({
            "auteur":       auteur,
            "n":            len(grp),
            "annee_min":    annees[0]  if annees else "",
            "annee_max":    annees[-1] if annees else "",
            "cat_counts":   cat_counts,
            "dominant_cat": dominant_cat,
        })

    stats.sort(key=lambda x: x["n"], reverse=True)

    if search.strip():
        stats = [s for s in stats if search.lower() in s["auteur"].lower()]

    st.caption(f"{len(stats)} auteur(s) trouvé(s)")
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    for s in stats:
        clr = CAT_COLORS.get(s["dominant_cat"], CAT_COLORS["Autre"])
        annee_range = (
            str(s["annee_min"]) if s["annee_min"] == s["annee_max"]
            else f"{s['annee_min']} – {s['annee_max']}"
        )
        cat_pills = "".join(
            pill_sm(cat, CAT_COLORS[cat])
            for cat, cnt in sorted(s["cat_counts"].items(), key=lambda x: -x[1])
            if cnt > 0
        )

        with st.container():
            st.markdown(f"""
            <div style="background:#fff;
                        border:1px solid #e0e0e0;
                        border-left:4px solid {clr};
                        border-radius:0 8px 8px 0;
                        padding:14px 22px 12px;">
              <div style="display:flex;justify-content:space-between;align-items:baseline;">
                <span style="font-size:16px;font-weight:700;color:#1E3A5F;">{s['auteur']}</span>
                <span style="font-size:13px;color:#888;">{s['n']} article{'s' if s['n']>1 else ''}</span>
              </div>
              <div style="margin-top:6px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
                <span style="color:#888;font-size:12px;">📅 {annee_range}</span>
                <span>{cat_pills}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            _, btn_col = st.columns([9, 3])
            with btn_col:
                if st.button("Voir les articles →", key=f"aut_{s['auteur']}", use_container_width=True):
                    st.session_state.auteur_selectionne = s["auteur"]
                    st.rerun()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


# ── Vue auteur : liste des articles d'un auteur ───────────────────────────────
def render_author_articles(df, auteur):
    col_back, col_title = st.columns([1, 9])

    with col_back:
        st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
        if st.button("← Retour", key="back_aut_list"):
            st.session_state.auteur_selectionne = None
            st.rerun()

    adf = df[df["auteur"] == auteur].copy()
    adf = adf.sort_values("annee", na_position="last")

    with col_title:
        st.markdown(f"## {auteur} — {len(adf)} article{'s' if len(adf)>1 else ''}")

    search = st.text_input(
        "Recherche",
        placeholder="Filtrer par titre…",
        label_visibility="collapsed",
    )

    if search.strip():
        adf = adf[adf["titre"].str.contains(search, case=False, na=False)]
        st.caption(f"{len(adf)} résultat(s) pour « {search} »")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    for _, row in adf.iterrows():
        article_card(row, key_prefix=f"a_{auteur[:8]}")


# ── Vue 3 : Détail article ─────────────────────────────────────────────────────
def render_article(df, article_id):
    match = df[df["article_id"] == article_id]
    if match.empty:
        st.error("Article introuvable.")
        if st.button("← Retour"):
            st.session_state.article_selectionne = None
            st.rerun()
        return

    row  = match.iloc[0]
    cat  = row["categorie"]
    clr  = CAT_COLORS.get(cat, CAT_COLORS["Autre"])
    year = st.session_state.annee_selectionnee
    aut  = st.session_state.auteur_selectionne

    # ── Navigation retour contextuelle ──────────────────────────────────────────
    if aut:
        retour_label = f"← Retour à {aut}"
    elif year:
        retour_label = f"← Retour à {year}"
    else:
        retour_label = "← Retour"

    if st.button(retour_label, key="back_article"):
        st.session_state.article_selectionne = None
        st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── En-tête article ─────────────────────────────────────────────────────────
    source = str(row.get("source_pdf", "") or "").strip()
    source_html = (
        f'<span style="color:#999;font-size:12px;font-style:italic;">{source}</span>'
        if source and source != "nan" else ""
    )
    page = row.get("page_debut")
    page_html = (
        f'<span style="color:#bbb;font-size:12px;">p.&nbsp;{int(page)}</span>'
        if pd.notna(page) else ""
    )
    top_right = " &nbsp;·&nbsp; ".join(x for x in [source_html, page_html] if x)

    auteur_str = row.get("auteur", "") or ""
    date_str   = str(row.get("publish_date", "") or "").strip()

    st.markdown(f"""
    <div style="border-left:5px solid {clr};padding:20px 28px 18px;
                background:#fafafa;border-radius:0 10px 10px 0;margin-bottom:20px;">
      <div style="display:flex;justify-content:space-between;
                  align-items:flex-start;margin-bottom:12px;">
        <div>{pill(cat, clr)}</div>
        <div style="text-align:right;">{top_right}</div>
      </div>
      <h1 style="font-family:Georgia,serif;font-size:26px;font-weight:700;
                 color:#1E3A5F;line-height:1.35;margin:0 0 14px 0;">
        {row['titre']}
      </h1>
      <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;">
        {"<span style='font-weight:600;color:#333;font-size:14px;'>" + auteur_str + "</span>" if auteur_str and auteur_str != "nan" else ""}
        {"<span style='color:#aaa;font-size:13px;'>" + date_str + "</span>" if date_str and date_str != "nan" else ""}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Entités groupées ─────────────────────────────────────────────────────────
    rows_entities = []
    if row["pays"]:
        rows_entities.append(
            '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px;">'
            '<span style="font-size:11px;color:#999;text-transform:uppercase;'
            'letter-spacing:.5px;min-width:90px;">Pays</span>'
            + "".join(pill(p, PAYS_COLOR) for p in row["pays"])
            + "</div>"
        )
    if row["personnalites"]:
        rows_entities.append(
            '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px;">'
            '<span style="font-size:11px;color:#999;text-transform:uppercase;'
            'letter-spacing:.5px;min-width:90px;">Personnalités</span>'
            + "".join(pill(p, PERSO_COLOR) for p in row["personnalites"])
            + "</div>"
        )
    if row["entreprises"]:
        rows_entities.append(
            '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px;">'
            '<span style="font-size:11px;color:#999;text-transform:uppercase;'
            'letter-spacing:.5px;min-width:90px;">Organisations</span>'
            + "".join(pill(p, ORG_COLOR) for p in row["entreprises"])
            + "</div>"
        )
    if rows_entities:
        st.markdown(
            '<div style="background:#fff;border:1px solid #e8e8e8;border-radius:8px;'
            'padding:14px 18px;margin-bottom:20px;">'
            + "".join(rows_entities)
            + "</div>",
            unsafe_allow_html=True,
        )

    # ── Chapeau ──────────────────────────────────────────────────────────────────
    chapeau = str(row.get("chapeau", "") or "").strip()
    if chapeau and chapeau != "nan":
        st.markdown(
            f'<div style="background:#f5f5f5;border-left:4px solid {clr};'
            f'border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:24px;">'
            f'<p style="font-family:Georgia,serif;font-style:italic;font-size:15px;'
            f'color:#333;line-height:1.7;margin:0;">{chapeau}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Contenu ──────────────────────────────────────────────────────────────────
    contenu = row.get("contenu", "")
    if pd.notna(contenu) and str(contenu).strip():
        body = format_content(str(contenu))
        st.markdown(
            f'<div style="max-width:760px;padding:8px 4px 32px;'
            f'font-family:Georgia,serif;font-size:15.5px;color:#1a1a1a;">'
            f'{body}'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Contenu non disponible.")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    if "vue"                not in st.session_state: st.session_state.vue                = "dashboard"
    if "annee_selectionnee" not in st.session_state: st.session_state.annee_selectionnee = None
    if "auteur_selectionne" not in st.session_state: st.session_state.auteur_selectionne = None
    if "article_selectionne" not in st.session_state: st.session_state.article_selectionne = None

    df = load_data()

    if st.session_state.article_selectionne:
        render_article(df, st.session_state.article_selectionne)
    elif st.session_state.auteur_selectionne:
        render_author_articles(df, st.session_state.auteur_selectionne)
    elif st.session_state.annee_selectionnee:
        render_year(df, st.session_state.annee_selectionnee)
    elif st.session_state.vue == "auteurs":
        render_authors_list(df)
    else:
        render_dashboard(df)


if __name__ == "__main__":
    main()

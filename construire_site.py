"""Fabrique la page web « Facturation Avocats 26-27 » à partir de factures.json.

Usage : python construire_site.py <fichier_sortie.html>
La page (site_modele.html) reçoit les données en JSON ; Claude la publie ensuite sur claude.ai.
Les numéros de compte bancaire ne sont pas mis dans la page.
"""
import datetime as dt
import json
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo
from collections import Counter
from pathlib import Path

ICI = Path(__file__).resolve().parent
FICHIER = ICI / "data" / "factures.json"
DONNEES = json.loads(FICHIER.read_text(encoding="utf-8"))
SOCIETES = ["NEW GREEN", "GLOBAL FARMING", "VITAL FROZEN", "ADOLAM", "GAN FRUITS"]


def facture_pour_site(f):
    calibres = Counter()
    for _, cal, colis, _, _ in f["palettes"]:
        calibres[cal] += colis
    return {
        "numero": f["numero"], "date": f["date"], "societe": f["societe"],
        "station": f.get("station"), "client": f["client"],
        "groupe": DONNEES["alias_clients"].get(f["client"], f["client"]),
        "destination": f["destination"], "incoterm": f["incoterm"], "produit": f["produit"],
        "variete": f["variete"], "designation": f["designation"], "emballage": f["emballage"],
        "kg_colis": f["kg_colis"], "lot": f["lot"], "palettes": f["palettes_facture"],
        "colis": f["colis_facture"], "brut": f["brut_facture"], "net": f["net_facture"],
        "prix_unit": f["prix_unit"], "devise": f["devise"], "montant": f["montant_facture"],
        "paiement": f.get("paiement"), "matricule": f.get("matricule"),
        "transporteur": f.get("transporteur"), "whatsapp_par": f.get("whatsapp_par"),
        "whatsapp_le": f.get("whatsapp_le"), "pdf": f"{f.get('dossier', '')}/{f['pdf']}",
        "remarques": f.get("remarques"), "colis_par_calibre": dict(calibres),
    }


_COURS = {"t": 0.0, "v": None}


def _json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.load(r)


def cours_eur_mad():
    """Cours EUR → MAD du moment (Yahoo Finance), sinon cours du jour (ExchangeRate-API).
    Gardé 5 minutes pour ne pas interroger le site de change à chaque visite."""
    if _COURS["v"] and time.time() - _COURS["t"] < 300:
        return _COURS["v"]
    maroc = ZoneInfo("Africa/Casablanca")
    v = None
    try:
        m = _json("https://query1.finance.yahoo.com/v8/finance/chart/EURMAD=X?range=1d&interval=5m")
        m = m["chart"]["result"][0]["meta"]
        v = {"taux": round(float(m["regularMarketPrice"]), 4), "source": "Yahoo Finance (marché)",
             "heure": f"{dt.datetime.fromtimestamp(m['regularMarketTime'], maroc):%d/%m/%Y %H:%M}"}
    except Exception:
        try:
            d = _json("https://open.er-api.com/v6/latest/EUR")
            v = {"taux": round(float(d["rates"]["MAD"]), 4), "source": "ExchangeRate-API (cours du jour)",
                 "heure": f"{dt.datetime.fromtimestamp(d['time_last_update_unix'], maroc):%d/%m/%Y %H:%M}"}
        except Exception:
            v = _COURS["v"]  # dernier cours connu, ou rien
    _COURS.update(t=time.time(), v=v)
    return v


def page_html(local=False):
    """La page complète ; local=True pour le site du Mac (questions via le serveur)."""
    donnees = json.loads(FICHIER.read_text(encoding="utf-8"))
    DONNEES.clear()
    DONNEES.update(donnees)  # relu à chaque appel : le serveur sert toujours les dernières factures
    factures = sorted(DONNEES["factures"], key=lambda f: (f["date"], f["numero"]))
    autres = sorted({f["societe"] for f in factures} - set(SOCIETES))
    data = {
        "mis_a_jour": f"{dt.datetime.fromtimestamp(FICHIER.stat().st_mtime):%d/%m/%Y à %H:%M}",
        "societes": SOCIETES + autres,
        "factures": [facture_pour_site(f) for f in factures],
        "cours": cours_eur_mad(),
        "objectifs_clients": DONNEES["objectifs_clients"],
        "a_completer": [{k: a.get(k) for k in ("pdf", "dossier", "whatsapp_par", "whatsapp_le")}
                        for a in DONNEES.get("a_completer", [])],
        "referentiel_societes": {n: {k: v for k, v in s.items() if k not in ("compte", "swift")}
                                 for n, s in DONNEES["societes"].items()},
    }
    modele = (ICI / "site_modele.html").read_text(encoding="utf-8")
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = modele.replace("/*__DONNEES__*/null", js).replace("/*__MODE_LOCAL__*/false", "true" if local else "false")
    return html, len(factures)


def main(sortie):
    html, n = page_html()
    Path(sortie).write_text(html, encoding="utf-8")
    print(f"{n} factures -> {sortie}")


if __name__ == "__main__":
    main(sys.argv[1])

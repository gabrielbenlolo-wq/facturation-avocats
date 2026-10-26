"""Fabrique la page web « Facturation Avocats 26-27 » à partir de factures.json.

Usage : python construire_site.py <fichier_sortie.html>
La page (site_modele.html) reçoit les données en JSON ; Claude la publie ensuite sur claude.ai.
Les numéros de compte bancaire ne sont pas mis dans la page.
"""
import datetime as dt
import json
import sys
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

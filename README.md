# Facturation Avocats 26-27

Site de suivi des factures avocats de la campagne 2026-2027 (NEW GREEN, GLOBAL FARMING, VITAL FROZEN, ADOLAM, GAN FRUITS).

- `data/factures.json` : les factures. Le Mac de Gabriel l'envoie ici à chaque facture relevée dans le groupe WhatsApp « Facturation Avocats ».
- `app.py` : le serveur (mot de passe, page, « Pose ta question » via l'API Anthropic).
- `construire_site.py` + `site_modele.html` : la page.
- `render.yaml` : la configuration Render. Chaque envoi sur GitHub republie le site.

Réglages Render (onglet Environment) : `SITE_PASSWORD` (identifiant `gabriel`) et `ANTHROPIC_API_KEY`.

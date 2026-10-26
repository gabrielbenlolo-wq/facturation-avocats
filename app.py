"""Site « Facturation Avocats 26-27 », hébergé sur Render.

Variables d'environnement (réglées dans Render) :
  SITE_PASSWORD      mot de passe du site (identifiant : gabriel)
  ANTHROPIC_API_KEY  clé API Anthropic pour « Pose ta question » (facultative)
  PORT               fourni par Render

Les données viennent de data/factures.json, envoyé sur GitHub par le Mac de Gabriel
à chaque nouvelle facture relevée ; Render republie alors le site tout seul.
"""
import base64
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import anthropic

import construire_site

MDP = os.environ.get("SITE_PASSWORD", "")
MODELE = "claude-opus-5-5"
client = anthropic.Anthropic() if os.environ.get("ANTHROPIC_API_KEY") else None

SQUELETTE = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
             '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);'
             'padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}'
             '[hidden]{display:none!important}</style></head><body>{page}</body></html>')


def demander_claude(turns):
    """turns : la page envoie d'abord les consignes + les données, puis la conversation."""
    messages = []
    for t in turns:
        role = "assistant" if t.get("role") == "assistant" else "user"
        texte = str(t.get("content", ""))
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n\n" + texte
        else:
            messages.append({"role": role, "content": texte})
    if not messages or messages[-1]["role"] != "user":
        return 400, {"code": "invalid_request"}
    try:
        reponse = client.beta.messages.create(
            model=MODELE,
            max_tokens=16000,
            output_config={"effort": "low"},
            cache_control={"type": "ephemeral"},  # les données, identiques d'une question à l'autre
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
        )
    except anthropic.RateLimitError:
        return 429, {"code": "rate_limited"}
    except anthropic.AuthenticationError:
        return 503, {"code": "not_logged"}
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        print(f"question en échec : {e!r}", flush=True)
        return 502, {"code": "upstream_error"}
    if reponse.stop_reason == "refusal":
        return 422, {"code": "refused"}
    texte = "".join(b.text for b in reponse.content if b.type == "text").strip()
    return (200, {"text": texte}) if texte else (502, {"code": "empty_completion"})


class Site(BaseHTTPRequestHandler):
    server_version = "FacturationAvocats"

    def autorise(self):
        attendu = base64.b64encode(f"gabriel:{MDP}".encode()).decode()
        recu = self.headers.get("Authorization", "").removeprefix("Basic ").strip()
        if MDP and hmac.compare_digest(recu, attendu):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Facturation Avocats", charset="UTF-8"')
        self.end_headers()
        return False

    def repondre(self, code, corps, type_="application/json; charset=utf-8"):
        data = corps if isinstance(corps, bytes) else json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/sante":  # contrôle de Render, sans mot de passe
            return self.repondre(200, {"ok": True})
        if not self.autorise():
            return
        if self.path.split("?")[0] not in ("/", "/index.html"):
            return self.repondre(404, {"code": "introuvable"})
        page, _ = construire_site.page_html(local=True)
        self.repondre(200, SQUELETTE.replace("{page}", page).encode(), "text/html; charset=utf-8")

    def do_POST(self):
        if not self.autorise():
            return
        if self.path != "/api/question":
            return self.repondre(404, {"code": "introuvable"})
        if client is None:
            return self.repondre(503, {"code": "no_key"})
        try:
            turns = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))["turns"]
        except (ValueError, KeyError):
            return self.repondre(400, {"code": "invalid_request"})
        self.repondre(*demander_claude(turns[-9:]))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    print(f"site démarré sur le port {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Site).serve_forever()

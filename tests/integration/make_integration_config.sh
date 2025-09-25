#!/usr/bin/env bash
set -euo pipefail

# --- Sécurité des fichiers : secrets en 600
umask 077

# --- Aller dans le dossier du script (tests/integration)
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$script_dir"

template="$script_dir/integration_config.yml.template"
output="$script_dir/integration_config.yml"

# --- Dépendances
if ! command -v envsubst >/dev/null 2>&1; then
  echo "ERROR: 'envsubst' introuvable. Installe gettext (ex: 'apt install gettext' ou 'brew install gettext')." >&2
  exit 1
fi

# --- Charger un .env.local si présent (non versionné), utile en local
# Format attendu: lignes KEY=VALUE, sans espaces autour du =
if [[ -f ".env.local" ]]; then
  # export automatique de toutes les variables définies dans le fichier
  set -a
  # shellcheck disable=SC1091
  source ".env.local"
  set +a
fi

# --- Variables requises pour les tests
required_vars=( NCE_USERNAME NCE_PASSWORD )

for v in "${required_vars[@]}"; do
  if [[ -z "${!v-}" ]]; then
    echo "ERROR: variable d'environnement requise absente: $v" >&2
    echo "       -> export $v=...   (ou renseigne-la dans tests/integration/.env.local)" >&2
    exit 1
  fi
done

# --- Variables optionnelles + valeurs par défaut (si absentes)
: "${NCE_VERIFY_SSL:=false}"

# --- Vérifs de base
[[ -f "$template" ]] || { echo "ERROR: template introuvable: $template" >&2; exit 1; }

# IMPORTANT: garder les variables entre guillemets dans le template YAML
# pour éviter les surprises d'analyse YAML.
# On laisse envsubst remplacer toutes les ${...} présentes.
envsubst < "$template" > "$output"

chmod 600 "$output"


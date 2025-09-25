## Ce que testent précisément les scénarios

1. **Nettoyage initial** – supprime toute ressource résiduelle (`state: absent`) sur *old* et *new* noms pour partir d’un état propre.   
2. **Création** d’un site avec un **ancien nom** (`test_site_old_name`). Vérifie `changed: true`.   
3. **Idempotence** d’une création répétée (deuxième run → `changed: false`). L’idempotence est conforme au module qui applique uniquement les sous-clés fournies sous `object`. 
4. **Mise à jour ciblée** (ex. `description`, `tags`) en s’appuyant sur un sélecteur fonctionnel (`selector: { city: … }`). Vérifie `changed: true` et présence d’un `diff`.   
5. **Check‑mode** (dry‑run) sur une mise à jour : doit reporter `changed: true` **sans** appliquer.   
6. **Rename** : fournit `selector.name: <ancien_nom>` et `object.name: <nouveau_nom>` → vérifie `changed: true`. Cette mécanique correspond à la règle de tes collections (“`name` peut être précisé dans le selector pour renommer… le nouveau nom est alors celui dans `object['name']`”). 
7. **Idempotence après rename** : rerun avec le nouveau nom → `changed: false`.   
8. **Lookup** via `cd60.nce.nce_lookup` (ressource `sites`) pour valider que le site est bien trouvé par `name`. 
9. **Suppression** (`state: absent`) puis **idempotence** de la suppression. 

> Les tests utilisent `nce_auth` pour obtenir/révoquer le token via `POST/DELETE /controller/v2/tokens`, conformément à ton bundle, avec `base_uri` par défaut `https://weu.naas.huawei.com:18002` et `validate_certs: false`. 

---

## Variables d’environnement à exporter

```bash
export NCE_BASE_URI="https://weu.naas.huawei.com:18002"
export NCE_USERNAME="tenant_admin@domain"

export NCE_PASSWORD="••••••"
read -s -p "NCE Password: " NCE_PASSWORD && export NCE_PASSWORD
export NCE_PASSWORD=$(< ~/.nce_password)

export NCE_VALIDATE_CERTS="false"

# Optionnel : données de test
export NCE_TEST_SITE_OLD="CD60-Test-Site-Temp"
export NCE_TEST_SITE_NEW="CD60-Test-Site"
export NCE_TEST_SITE_CITY="Beauvais"
export NCE_TEST_SITE_TZ="Europe/Paris"
export NCE_TEST_SITE_ADDR="1 Rue de la Préfecture"
export NCE_TEST_SITE_COUNTRY="FR"
```

> Si `NCE_USERNAME`/`NCE_PASSWORD` sont absents, le test **saute** proprement en `pre_tasks`. 

---

## Exécution

Depuis la racine de la collection :

```bash
ansible-test integration nce_site -vv --color --python 3.11
# ou pour tous les tests d’intégration :
ansible-test integration --retry-on-error --color -vv
```
define 
read -srp 'Mot de passe: ' NCE_PASSWORD && export NCE_PASSWORD
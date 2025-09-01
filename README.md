# Vue d’ensemble (version **PostgreSQL‑only**)

Objectif : fournir une architecture **solide, modulaire et évolutive** pour un e‑commerce complet **sans Redis ni S3/MinIO**. Tous les besoins (catalogue, commandes, paiements, stories produits) sont couverts avec **FastAPI + PostgreSQL** uniquement.

Stack de base :

* **FastAPI** (API REST, OpenAPI, async)
* **PostgreSQL 16+** (relationnel + JSONB + FTS + Large Objects/`bytea`)
* **SQLAlchemy 2.0 + Alembic** (ORM + migrations)
* **Stripe / FedaPay/Paystack** (paiements)
* **Docker & Docker Compose** (dev), **GitHub Actions** (CI/CD)
* **APScheduler** (planification) + **LISTEN/NOTIFY PostgreSQL** (events) au lieu de Redis/Celery

> **Pourquoi PostgreSQL‑only ?**
>
> * Stockage binaire via `bytea` ou **Large Objects (LO)**
> * Recherche full‑text native (tsvector) + trigram (pg\_trgm)
> * Files d’attente minimalistes via table `job_queue` + triggers + `LISTEN/NOTIFY`
> * Caching parcimonieux en base (materialized views) plutôt que Redis

---

## Architecture logique

```
[ Mobile App ]            [ Front Web React/Vite ]
       |                           |
       |                (Auth, Cart, Catalog, Checkout, Stories)
       |                           |
       +-------------> [ FastAPI Gateway (api/v1) ]
                                 |
               +-----------------+-------------------+
               |                 |                   |
        [ Domain Services ]  [ Integrations ]   [ Background ]
               |                 |                   |
         Catalog, Orders,     Instagram Graph     APScheduler jobs
         Cart, Users, RBAC,   API (pull),         (ingestion stories,
         Promotions, Media,   Webhooks paiement   thumbnails,
         Reviews, Inventory    ...)
               |                 |
               +---------+-------+------------------+
                         |
                    [ Data Layer ]
                         |
         PostgreSQL (tables, vues, FTS, LO/bytea, LISTEN/NOTIFY)
```

---

## Organisation du code

```
app/
 ├─ api/
 │   ├─ v1/
 │   │   ├─ auth.py
 │   │   ├─ users.py
 │   │   ├─ products.py
 │   │   ├─ categories.py
 │   │   ├─ media.py
 │   │   ├─ stories.py
 │   │   ├─ search.py
 │   │   ├─ cart.py
 │   │   ├─ checkout.py
 │   │   ├─ orders.py
 │   │   ├─ payments.py
 │   │   ├─ promotions.py
 │   │   ├─ reviews.py
 │   │   ├─ inventory.py
 │   │   └─ webhooks.py
 │   └─ deps.py
 │
 ├─ core/
 │   ├─ config.py        # Settings Pydantic (env vars)
 │   ├─ security.py      # JWT, password hashing, scopes
 │   ├─ cors.py
 │   ├─ logging.py
 │   └─ scheduler.py     # APScheduler init + jobs
 │
 ├─ models/              # SQLAlchemy ORM
 │   ├─ user.py          # User, Role, Permission
 │   ├─ product.py       # Product, Variant, SKU, Price, Media, Tag
 │   ├─ category.py
 │   ├─ story.py         # Story, StoryProductLink, OAuthToken
 │   ├─ inventory.py     # Stock, Reservation
 │   ├─ order.py         # Order, OrderItem, Shipment
 │   ├─ cart.py          # Cart, CartItem
 │   ├─ promotion.py     # Promotion, Coupon
 │   ├─ review.py
 │   ├─ payment.py       # Payment, Refund
 │   ├─ address.py       # Address (shipping/billing)
 │   ├─ media.py         # MediaAsset (bytea/LO), Derivative
 │   └─ job.py           # JobQueue, JobAttempt (background léger)
 │
 ├─ schemas/             # Pydantic (I/O API)
 │   ├─ ... (miroir des models)
 │
 ├─ repositories/        # Requêtes SQL et CRUD typés
 │   ├─ product_repo.py
 │   ├─ story_repo.py
 │   ├─ media_repo.py
 │   ├─ order_repo.py
 │   ├─ job_repo.py
 │   └─ ...
 │
 ├─ services/            # Logique métier
 │   ├─ product_service.py
 │   ├─ story_service.py
 │   ├─ media_service.py        # lecture/écriture blobs DB, thumbnails
 │   ├─ pricing_service.py
 │   ├─ cart_service.py
 │   ├─ checkout_service.py
 │   ├─ order_service.py
 │   ├─ payment_service.py
 │   ├─ inventory_service.py
 │   ├─ promotion_service.py
 │   ├─ review_service.py
 │   └─ search_service.py       # FTS PostgreSQL
 │
 ├─ integrations/
 │   ├─ instagram.py     # Graph API (pull stories -> DB)
 │   ├─ stripe.py        # ou fedapay.py / paystack.py
 │   └─ email.py         # SMTP/Sendgrid (optionnel)
 │
 ├─ background/
 │   ├─ jobs.py          # définitions des jobs (Python purs)
 │   ├─ runners.py       # exécuteur qui lit JobQueue + NOTIFY
 │   └─ thumbnails.py    # génération dérivés (via Pillow/ffmpeg)
 │
 ├─ utils/
 │   ├─ images.py        # PIL/ffmpeg helpers
 │   ├─ time.py
 │   └─ ids.py           # idempotency keys
 │
 ├─ main.py              # FastAPI app factory
 └─ alembic/             # migrations
```

---

## Modèle de données (PostgreSQL‑only)

### Utilisateurs & RBAC

* `user(id, email, username, password_hash, is_active, created_at)`
* `role(id, name)` (admin, manager, customer)
* `user_role(user_id, role_id)`
* `permission(id, code)` + `role_permission(role_id, permission_id)` *(optionnel)*

### Catalogue produits

* `category(id, parent_id, name, slug, position)`
* `product(id, sku_root, title, slug, description, long_description, brand, specs JSONB, is_active, created_at)`
* `product_variant(id, product_id, name, attributes JSONB)` *(couleur, taille)*
* `price(id, variant_id NULL, product_id NULL, currency, amount, compare_at_amount NULL, starts_at, ends_at)`
* `inventory(id, variant_id NULL, product_id NULL, qty_on_hand, qty_reserved, low_stock_threshold)`
* `tag(id, name, slug)` et `product_tag(product_id, tag_id)`

### Médias (stockés en base)

* `media_asset(id, sha256, filename, mime_type, size_bytes, data BYTEA/LO, width NULL, height NULL, duration_sec NULL, created_at)`
* `media_derivative(id, asset_id, kind, mime_type, size_bytes, data BYTEA/LO, width NULL, height NULL)` *(thumbnails, webp, mp4)*
* `product_media(id, product_id, asset_id, is_primary, position, alt)`

> **Choix `BYTEA` vs Large Object (LO)**
>
> * `BYTEA` (TOAST) : simple, transactions, pratique < \~20–50 MB
> * **LO** : mieux pour très gros fichiers, nécessite API LO
> * Possibilité hybride : `BYTEA` pour images, **LO** pour vidéos
> * Déduplication via `sha256` (ne pas stocker 2× le même blob)

### Panier & Commande

* `cart(id, user_id NULL, session_id, created_at, updated_at)`
* `cart_item(id, cart_id, product_id, variant_id NULL, qty, unit_price, currency)`
* `address(id, user_id, kind, full_name, phone, line1, line2, city, state, country, zip)`
* `order(id, user_id, status, subtotal, discount_total, shipping_total, tax_total, grand_total, currency, payment_status, created_at)`
* `order_item(id, order_id, product_id, variant_id NULL, qty, unit_price, currency)`
* `shipment(id, order_id, carrier, tracking_number, status, shipped_at, delivered_at)`

### Paiements & Promotions

* `payment(id, order_id, provider, amount, currency, status, provider_ref, created_at)`
* `coupon(id, code, type, value, starts_at, ends_at, usage_limit, used_count, is_active)`
* `promotion(id, name, rules JSONB, starts_at, ends_at, is_active)`

### Stories & intégrations sociales

* `story(id, platform, external_id, media_type, caption, posted_at, permalink, linked_product_id NULL, asset_id NULL)`
* `oauth_token(id, provider, access_token, refresh_token, expires_at, account_ref)`
* `story_product_link(story_id, product_id)` *(si plusieurs produits par story)*

### Jobs & Observabilité

* `job_queue(id, kind, payload JSONB, status, run_at, attempts, last_error, created_at)`
* `job_attempt(id, job_id, started_at, finished_at, ok, log)`
* `audit_log(id, actor_id, action, entity, entity_id, payload JSONB, created_at)`

> **Indexation recommandée** : `product.slug` (unique), `category.slug`, `price(starts_at, ends_at)`, `story(platform, posted_at)`, `order(status)`, `media_asset.sha256` (unique), FTS (`product_fts`), trigram sur `title`/`brand`/`tags`.

---

## Recherche & performances (sans moteur externe)

* **FTS PostgreSQL** : colonne générée `product_fts tsvector` indexée GIN, alimentée par trigger sur `title/description/tags/brand`
* **Trigram (pg\_trgm)** : pour tolérer les fautes (LIKE/ILIKE rapides)
* **Materialized views** : `popular_products`, `category_counts`
* **Pagination** : keyset (id, created\_at) plutôt qu’offset si nécessaire

---

## Background sans Redis

* **APScheduler** démarre dans `main.py` → tâches planifiées (ex : `pull_instagram_stories` toutes les 10 min)
* **Queue DB** : `job_queue` + `LISTEN/NOTIFY` ; un `runner` consomme et exécute
* **Idempotence** : clé `external_id` (stories), `sha256` (médias)
* **Thumbnails** : créer des `media_derivative` via jobs (générés une seule fois)

---

## Contrats API (inchangés hors médias)

### Media

* `POST /api/v1/media/upload` (FormData : `file`) → crée `media_asset(data=BYTEA/LO)` et retourne `{ asset_id, filename, mime_type, size_bytes }`
* `GET /api/v1/media/{asset_id}` → **stream** depuis la DB (headers `Content-Type`, `ETag` = sha256, `Cache-Control`)
* `POST /api/v1/media/{asset_id}/derivatives` (admin) → génère miniature/webp en tâche DB

### Stories (Instagram)

* `POST /api/v1/stories/ingest/instagram` → enfile un job DB
* Le job appelle Graph API, télécharge le média en mémoire puis **stocke `asset_id`** + story en base
* Option : création d’un **product draft** relié à la story

---

## Flux clés

### 1) Ingestion d’une story Instagram → Produit

1. Job `pull_instagram_stories()` planifié via APScheduler
2. Récupère les stories actives (Graph API)
3. Pour chaque story :

   * Télécharge le média → `media_asset(data=BYTEA/LO, sha256)`
   * Crée `story(external_id unique, asset_id)`
   * (Option) Crée `product` ébauche + `product_media(asset_id)`
   * Lien story ↔ produit via `linked_product_id` ou table de liaison

### 2) Création produit depuis Mobile App

* `POST /api/v1/media/upload` → `asset_id`
* `POST /api/v1/products` (+ `media`: liste d’`asset_id`) → crée produit, prix, stock, relations médias

### 3) Parcours client (Front Web)

* `GET /products` (filtres, FTS)
* `GET /products/{slug}`
* `POST /cart/items` → `POST /checkout` → paiement → `webhooks`
* `GET /media/{asset_id}` pour afficher les images

---

## Sécurité & conformité

* JWT access/refresh, scopes par route (admin vs public)
* CORS restreint aux domaines front
* Validation Pydantic stricte + idempotency keys pour POST critiques
* RGPD : rétention médias/stories, droit d’effacement, audit log
* Signatures Webhook (Stripe/FedaPay)

---

## Déploiement & CI/CD (PostgreSQL‑only)

**Docker Compose (dev)**

```
version: "3.9"
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+psycopg://maef:maef@db:5432/maef
      - JWT_SECRET=devsecret
      - IG_APP_ID=... # si stories
      - IG_APP_SECRET=...
    depends_on: [db]
  db:
    image: postgres:16
    environment:
      - POSTGRES_USER=maef
      - POSTGRES_PASSWORD=maef
      - POSTGRES_DB=maef
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

**Env vars (exemples)**

* `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/maef`
* `JWT_SECRET=...` `JWT_EXPIRES=3600` `JWT_REFRESH_EXPIRES=2592000`
* `IG_APP_ID, IG_APP_SECRET, IG_REDIRECT_URI`
* `STRIPE_SECRET_KEY` *(ou FedaPay/Paystack)*

**GitHub Actions**

* lint + tests (pytest)
* build image Docker
* déploiement (SSH/K8s/PaaS)

---

## Bonnes pratiques spécifiques au DB‑storage

* **Taille des blobs** : privilégier images < 10 MB (JPEG/WebP). Vidéos possibles via LO.
* **Compression** : laisser TOAST gérer (BYTEA) ; pour vidéos, encoder en H.264/H.265.
* **Déduplication** : hash `sha256` unique pour éviter doublons.
* **Streaming** : `Response(content=iter_chunks(...), media_type=mime)` pour gros fichiers.
* **Sauvegardes** : `pg_dump` + snapshots disque (tous médias sont dans la DB → backups = critique).
* **Partionnement** : table `media_asset` par mois si volume élevé.
* **Quotas** : champs `size_bytes` cumulés par user pour contrôler l’espace.

---

## Mapping avec ton front (React/Vite)

* `FeaturedProducts.jsx` → `GET /products?featured=true`
* `ProductCard.jsx/ProductGallery.jsx` → images via `GET /media/{asset_id}`
* `Shop/ProductGrid.jsx` → `GET /products` (FTS + filtres)
* `ProductDetail.jsx` → `GET /products/{slug}` (inclure `related`)
* `Cart`/`Checkout` → endpoints correspondants
* **Stories section** → `GET /stories?linked=true&limit=...` + rendu carrousel images/vidéos depuis `asset_id`

---

### TL;DR

# Welcome to Microblog!

This is an example application featured in my [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world). See the tutorial for instructions on how to work with it.

The version of the application featured in this repository corresponds to the 2024 edition of the Flask Mega-Tutorial. You can find the 2018 and 2021 versions of the code [here](https://github.com/miguelgrinberg/microblog-2018). And if for any strange reason you are interested in the original code, dating back to 2012, that is [here](https://github.com/miguelgrinberg/microblog-2012).

---

# Tests de charge (atelier 3 EPSI)

Fork de [microblog](https://github.com/miguelgrinberg/microblog) pour faire des tests de charge avec [Locust](https://locust.io).

## Lancer l'application en local

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
flask run --port 5055
```

## Lancer les tests de charge

```bash
cd test/load
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# avec l'interface web (http://localhost:8089)
locust -f locustfile.py --host http://127.0.0.1:5055

# en ligne de commande
locust -f locustfile.py --headless -u 10 -r 5 -t 30s --host http://127.0.0.1:5055
```

Le `locustfile.py` contient 3 profils d'utilisateurs :

- **Visiteur** (poids 2) : accueil, login, inscription, mot de passe oublie, login rate, reset password (POST), page 404
- **Membre** (poids 5) : s'inscrit et se connecte au demarrage puis : accueil, publier un post, explore (+ page 2),
  profil, popup profil, modifier son profil, follow/unfollow, envoyer un message, messages, notifications, recherche, export des posts
- **ClientApi** (poids 1) : cree un compte via l'API, recupere un token puis `/api/users`, `/api/users/<id>`, followers, following, PUT

Les formulaires sont proteges par un token CSRF (Flask-WTF) donc on charge la page du formulaire avant chaque POST pour le recuperer.

## Resultats

Machine : MacBook (Apple Silicon), serveur de dev Flask (`flask run`), base SQLite.
Tir : 150 utilisateurs, montee de 10/s, 120 s -> ~11 200 requetes.

| Requete | Mediane (ms) | p95 (ms) | Max (ms) | Echecs |
|---|---|---|---|---|
| POST /auth/login | 97 | 200 | 280 | 0 |
| POST /api/tokens | 87 | 180 | 184 | 0 |
| POST /auth/register | 110 | 160 | 215 | 0 |
| POST /api/users | 110 | 160 | 157 | 0 |
| GET /api/users | 11 | 57 | 179 | 0 |
| GET /explore?page=n | 15 | 56 | 147 | 0 |
| GET /explore | 13 | 55 | 323 | 0 |
| POST /index (nouveau post) | 16 | 46 | 182 | 0 |
| GET /export_posts | 5 | 23 | 75 | **100 %** |
| autres pages | 2 - 9 | 9 - 39 | - | 0 |

## Known issues

- **`/export_posts` renvoie une erreur 500 a chaque fois** : la route lance une tache en arriere-plan avec RQ,
  qui a besoin d'un serveur Redis. Sans Redis l'exception n'est pas geree. Il faudrait verifier que Redis
  est dispo et afficher un message d'erreur propre au lieu d'une 500.
- **Login / inscription / creation de token lents (~100 ms de mediane, 200 ms au p95)** : c'est le hachage du
  mot de passe (werkzeug, scrypt/pbkdf2) qui est volontairement couteux. C'est normal pour la securite, mais sous
  forte charge ces routes saturent le CPU en premier. Pistes : limiter le nombre de tentatives (rate limiting) et
  mettre plusieurs workers (gunicorn) pour ne pas bloquer les autres pages.
- **`/explore` et `/explore?page=n` ralentissent quand le nombre de posts augmente** (page la plus lourde : ~30 Ko,
  p95 a 55 ms alors que les pages simples sont sous 10 ms). Pour chaque post affiche le template va chercher
  l'auteur (requetes N+1) et l'avatar. Pistes : charger les auteurs avec une jointure (`selectinload`),
  ajouter un index sur `post.timestamp`, mettre en cache.
- **`POST /index` (publier un post)** : la detection de langue (`langdetect`) est faite a chaque post, ce qui
  rajoute du temps de traitement. On pourrait la faire en tache de fond.
- **`/api/users`** : p95 a 57 ms, la liste est paginee mais chaque utilisateur est serialise avec des compteurs
  (posts, followers, following) calcules par des requetes separees.
- **`/notifications`** est appele toutes les 10 secondes par le javascript de chaque page ouverte : avec beaucoup
  d'utilisateurs connectes ca fait beaucoup de requetes pour rien. Un websocket ou un intervalle plus long serait mieux.
- Le serveur de dev Flask + SQLite n'est pas fait pour la prod : SQLite verrouille toute la base a chaque ecriture,
  donc les ecritures (posts, follow, messages) vont se bloquer entre elles quand la charge augmente.

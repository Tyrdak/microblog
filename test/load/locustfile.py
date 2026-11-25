"""Tests de charge de microblog avec Locust.

3 types d'utilisateurs :
 - Visiteur : pas connecte, pages publiques (login, inscription, mot de passe oublie)
 - Membre : s'inscrit, se connecte puis utilise le site (posts, explore, profil, follow, messages...)
 - ClientApi : utilise l'API REST (token + /api/users)

Les formulaires Flask-WTF ont un token CSRF : on le recupere dans la page avant chaque POST.
"""
import random
import re
import uuid

from locust import HttpUser, between, task

CSRF_RE = re.compile(r'name="csrf_token" type="hidden" value="([^"]+)"')
PASSWORD = "motdepasse"

# liste des membres crees pendant le test (pour follow / messages)
membres_crees = []


def get_csrf(client, url, name=None):
    """Charge une page et retourne le token CSRF du formulaire"""
    resp = client.get(url, name=name)
    match = CSRF_RE.search(resp.text)
    return match.group(1) if match else ""


def nouveau_nom():
    return "user_" + uuid.uuid4().hex[:10]


class Visiteur(HttpUser):
    """Utilisateur non connecte"""
    weight = 2
    wait_time = between(1, 3)

    @task(5)
    def accueil(self):
        # redirige vers /auth/login
        self.client.get("/")

    @task(3)
    def page_login(self):
        self.client.get("/auth/login")

    @task(2)
    def page_inscription(self):
        self.client.get("/auth/register")

    @task(1)
    def page_mot_de_passe_oublie(self):
        self.client.get("/auth/reset_password_request")

    @task(2)
    def login_mauvais_mot_de_passe(self):
        token = get_csrf(self.client, "/auth/login")
        self.client.post("/auth/login", data={
            "csrf_token": token,
            "username": "inconnu",
            "password": "faux",
        }, name="/auth/login [POST echec]")

    @task(1)
    def demande_reset_password(self):
        token = get_csrf(self.client, "/auth/reset_password_request")
        self.client.post("/auth/reset_password_request", data={
            "csrf_token": token,
            "email": "personne@example.com",
        }, name="/auth/reset_password_request [POST]")

    @task(1)
    def page_inexistante(self):
        with self.client.get("/page/qui/existe/pas", name="/404",
                             catch_response=True) as resp:
            if resp.status_code == 404:
                resp.success()


class Membre(HttpUser):
    """Utilisateur inscrit et connecte"""
    weight = 5
    wait_time = between(1, 3)

    def on_start(self):
        self.username = nouveau_nom()
        token = get_csrf(self.client, "/auth/register")
        self.client.post("/auth/register", data={
            "csrf_token": token,
            "username": self.username,
            "email": f"{self.username}@example.com",
            "password": PASSWORD,
            "password2": PASSWORD,
        }, name="/auth/register [POST]")

        token = get_csrf(self.client, "/auth/login")
        self.client.post("/auth/login", data={
            "csrf_token": token,
            "username": self.username,
            "password": PASSWORD,
        }, name="/auth/login [POST]")
        membres_crees.append(self.username)

    def on_stop(self):
        self.client.get("/auth/logout")

    def autre_membre(self):
        autres = [m for m in membres_crees if m != self.username]
        return random.choice(autres) if autres else None

    @task(10)
    def accueil(self):
        self.client.get("/index")

    @task(5)
    def publier(self):
        token = get_csrf(self.client, "/index")
        self.client.post("/index", data={
            "csrf_token": token,
            "post": f"Hello depuis locust {uuid.uuid4().hex[:6]}",
        }, name="/index [POST nouveau post]")

    @task(6)
    def explore(self):
        self.client.get("/explore")

    @task(2)
    def explore_page_2(self):
        self.client.get("/explore?page=2", name="/explore?page=[n]")

    @task(4)
    def mon_profil(self):
        self.client.get(f"/user/{self.username}", name="/user/[username]")

    @task(3)
    def popup_profil(self):
        autre = self.autre_membre() or self.username
        self.client.get(f"/user/{autre}/popup", name="/user/[username]/popup")

    @task(2)
    def modifier_profil(self):
        token = get_csrf(self.client, "/edit_profile")
        self.client.post("/edit_profile", data={
            "csrf_token": token,
            "username": self.username,
            "about_me": "Je suis un utilisateur de test de charge",
        }, name="/edit_profile [POST]")

    @task(3)
    def suivre_puis_ne_plus_suivre(self):
        autre = self.autre_membre()
        if autre is None:
            return
        token = get_csrf(self.client, f"/user/{autre}", name="/user/[username]")
        self.client.post(f"/follow/{autre}", data={"csrf_token": token},
                         name="/follow/[username]")
        token = get_csrf(self.client, f"/user/{autre}", name="/user/[username]")
        self.client.post(f"/unfollow/{autre}", data={"csrf_token": token},
                         name="/unfollow/[username]")

    @task(2)
    def envoyer_message(self):
        autre = self.autre_membre()
        if autre is None:
            return
        token = get_csrf(self.client, f"/send_message/{autre}",
                         name="/send_message/[username]")
        self.client.post(f"/send_message/{autre}", data={
            "csrf_token": token,
            "message": "Salut ! (message de test)",
        }, name="/send_message/[username] [POST]")

    @task(3)
    def messages(self):
        self.client.get("/messages")

    @task(4)
    def notifications(self):
        # appele en boucle par le javascript de la page
        self.client.get("/notifications?since=0", name="/notifications")

    @task(2)
    def recherche(self):
        self.client.get("/search?q=locust", name="/search?q=[mot]")

    @task(1)
    def export_posts(self):
        self.client.get("/export_posts")


class ClientApi(HttpUser):
    """Utilisation de l'API REST"""
    weight = 1
    wait_time = between(1, 3)

    def on_start(self):
        self.username = nouveau_nom()
        resp = self.client.post("/api/users", json={
            "username": self.username,
            "email": f"{self.username}@example.com",
            "password": PASSWORD,
        }, name="/api/users [POST]")
        self.user_id = resp.json().get("id") if resp.ok else 1
        resp = self.client.post("/api/tokens", auth=(self.username, PASSWORD))
        token = resp.json().get("token") if resp.ok else ""
        self.client.headers["Authorization"] = f"Bearer {token}"

    @task(3)
    def liste_utilisateurs(self):
        self.client.get("/api/users")

    @task(3)
    def un_utilisateur(self):
        self.client.get(f"/api/users/{self.user_id}", name="/api/users/[id]")

    @task(1)
    def followers(self):
        self.client.get(f"/api/users/{self.user_id}/followers",
                        name="/api/users/[id]/followers")

    @task(1)
    def following(self):
        self.client.get(f"/api/users/{self.user_id}/following",
                        name="/api/users/[id]/following")

    @task(1)
    def modifier(self):
        self.client.put(f"/api/users/{self.user_id}",
                        json={"about_me": "maj via l'API"},
                        name="/api/users/[id] [PUT]")

from locust import HttpUser, task, between


class Visiteur(HttpUser):
    wait_time = between(1, 3)

    @task
    def accueil(self):
        self.client.get("/")

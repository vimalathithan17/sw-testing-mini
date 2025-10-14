from locust import HttpUser, task, between
import random

class ApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        # Create a user for this simulated client
        uname = f"user_{random.randint(1, 1_000_000)}"
        r = self.client.post("/users", json={"name": uname})
        if r.status_code == 201:
            self.user_id = r.json()["id"]
        else:
            self.user_id = None

    @task(3)
    def create_order(self):
        if not getattr(self, "user_id", None):
            return
        amount = round(random.random() * 100, 2)
        self.client.post("/orders", json={"user_id": self.user_id, "amount": str(amount)})

    @task(1)
    def list_orders(self):
        self.client.get("/orders")

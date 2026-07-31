from locust import HttpUser, task, between, events
import json
import random
import string
import time


class MLPipelineUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.token = None
        self.user_email = f"test_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}@example.com"
        self.user_password = "testpassword123"
        self.dataset_id = None
        self.model_id = None
        self._register()
        self._login()

    def _register(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.user_email,
                "username": f"user_{''.join(random.choices(string.ascii_lowercase, k=8))}",
                "password": self.user_password,
                "full_name": "Load Test User",
            },
        )
        if response.status_code == 201:
            self.token = response.json().get("access_token")

    def _login(self):
        if self.token:
            return
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": self.user_email,
                "password": self.user_password,
            },
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    def _get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(10)
    def health_check(self):
        self.client.get("/health")

    @task(8)
    def get_algorithms(self):
        self.client.get("/api/v1/algorithms")

    @task(5)
    def list_datasets(self):
        self.client.get(
            "/api/v1/datasets",
            headers=self._get_headers(),
        )

    @task(5)
    def list_models(self):
        self.client.get(
            "/api/v1/models",
            headers=self._get_headers(),
        )

    @task(3)
    def list_experiments(self):
        self.client.get(
            "/api/v1/experiments",
            headers=self._get_headers(),
        )

    @task(3)
    def list_ab_tests(self):
        self.client.get(
            "/api/v1/ab-tests",
            headers=self._get_headers(),
        )

    @task(2)
    def get_me(self):
        self.client.get(
            "/api/v1/auth/me",
            headers=self._get_headers(),
        )

    @task(2)
    def create_model(self):
        response = self.client.post(
            "/api/v1/models",
            json={
                "name": f"Model_{''.join(random.choices(string.ascii_lowercase, k=6))}",
                "algorithm": random.choice([
                    "random_forest",
                    "gradient_boosting",
                    "logistic_regression",
                    "svm",
                    "knn",
                ]),
                "target_column": "target",
            },
            headers=self._get_headers(),
        )
        if response.status_code == 201:
            self.model_id = response.json().get("id")

    @task(1)
    def make_prediction(self):
        if not self.model_id:
            return
        self.client.post(
            f"/api/v1/models/{self.model_id}/predict",
            json={
                "data": [
                    {
                        "sepal length (cm)": random.uniform(4, 8),
                        "sepal width (cm)": random.uniform(2, 4.5),
                        "petal length (cm)": random.uniform(1, 7),
                        "petal width (cm)": random.uniform(0.1, 2.5),
                    }
                ]
            },
            headers=self._get_headers(),
        )


class APIEndpointUser(HttpUser):
    wait_time = between(0.5, 1.5)
    weight = 2

    def on_start(self):
        self.token = None
        self._login()

    def _login(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@mlpipeline.com",
                "password": "admin123",
            },
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    def _get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(15)
    def api_health(self):
        self.client.get("/health")

    @task(10)
    def api_docs(self):
        self.client.get("/docs")

    @task(8)
    def api_algorithms(self):
        self.client.get("/api/v1/algorithms")

    @task(5)
    def api_monitoring_stats(self):
        self.client.get(
            "/api/v1/monitoring/stats",
            headers=self._get_headers(),
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Load test started!")
    print(f"Target: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("Load test completed!")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    if exception:
        print(f"Request failed: {request_type} {name} - {exception}")

"""Auto Clustering — Auto-detect optimal clusters and apply multiple clustering methods."""
import logging
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score

logger = logging.getLogger(__name__)


@dataclass
class ClusterResult:
    method: str = ""
    n_clusters: int = 0
    labels: list[int] = field(default_factory=list)
    silhouette: float = 0.0
    calinski_harabasz: float = 0.0
    davies_bouldin: float = 0.0
    cluster_sizes: dict = field(default_factory=dict)
    cluster_centers: list[list[float]] = field(default_factory=list)
    feature_importance: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "method": self.method, "n_clusters": self.n_clusters,
            "labels": self.labels[:500],
            "silhouette": round(self.silhouette, 4),
            "calinski_harabasz": round(self.calinski_harabasz, 4),
            "davies_bouldin": round(self.davies_bouldin, 4),
            "cluster_sizes": self.cluster_sizes,
            "cluster_centers": [[round(c, 4) for c in row] for row in self.cluster_centers[:10]],
            "feature_importance": self.feature_importance,
            "duration_ms": round(self.duration_ms, 2),
            "summary": self.summary,
        }


class AutoClusterer:

    def __init__(self):
        self._scaler = StandardScaler()

    def find_optimal_k(self, X: np.ndarray, k_range: range = None) -> dict:
        if k_range is None:
            k_range = range(2, min(11, len(X)))
        
        k_list = list(k_range)
        if len(k_list) < 1:
            return {"optimal_k": 2, "results": [], "best_silhouette": 0}

        X_scaled = self._scaler.fit_transform(X)
        inertias = []
        silhouettes = []
        results = []

        for k in k_list:
            try:
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = km.fit_predict(X_scaled)
                sil = silhouette_score(X_scaled, labels)
                inertias.append(km.inertia_)
                silhouettes.append(sil)
                results.append({"k": k, "inertia": km.inertia_, "silhouette": sil})
            except Exception:
                inertias.append(0)
                silhouettes.append(0)

        best_k = k_list[np.argmax(silhouettes)] if silhouettes else 2
        return {
            "optimal_k": best_k,
            "results": results,
            "best_silhouette": max(silhouettes) if silhouettes else 0,
        }

    def cluster_kmeans(self, X: pd.DataFrame, n_clusters: int = None) -> ClusterResult:
        start = datetime.now()
        X_scaled = self._scaler.fit_transform(X.fillna(0))

        if n_clusters is None:
            opt = self.find_optimal_k(X.fillna(0).values)
            n_clusters = opt["optimal_k"]

        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)

        result = ClusterResult(
            method="kmeans", n_clusters=n_clusters,
            labels=labels.tolist(),
            silhouette=silhouette_score(X_scaled, labels),
            calinski_harabasz=calinski_harabasz_score(X_scaled, labels),
            davies_bouldin=davies_bouldin_score(X_scaled, labels),
            cluster_centers=km.cluster_centers_.tolist(),
        )
        result.cluster_sizes = {str(i): int(np.sum(labels == i)) for i in range(n_clusters)}
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"KMeans k={n_clusters}, silhouette={result.silhouette:.3f}"
        return result

    def cluster_dbscan(self, X: pd.DataFrame, eps: float = 0.5,
                       min_samples: int = 5) -> ClusterResult:
        start = datetime.now()
        X_scaled = self._scaler.fit_transform(X.fillna(0))

        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(X_scaled)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

        result = ClusterResult(method="dbscan", n_clusters=n_clusters, labels=labels.tolist())
        if n_clusters >= 2:
            non_noise = labels != -1
            if non_noise.sum() >= 2:
                result.silhouette = silhouette_score(X_scaled[non_noise], labels[non_noise])
        result.cluster_sizes = {
            str(i): int(np.sum(labels == i)) for i in set(labels)
        }
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"DBSCAN: {n_clusters} clusters, {int(np.sum(labels == -1))} noise points"
        return result

    def cluster_agglomerative(self, X: pd.DataFrame,
                              n_clusters: int = 3) -> ClusterResult:
        start = datetime.now()
        X_scaled = self._scaler.fit_transform(X.fillna(0))

        agg = AgglomerativeClustering(n_clusters=n_clusters)
        labels = agg.fit_predict(X_scaled)

        result = ClusterResult(
            method="agglomerative", n_clusters=n_clusters, labels=labels.tolist(),
            silhouette=silhouette_score(X_scaled, labels),
            calinski_harabasz=calinski_harabasz_score(X_scaled, labels),
            davies_bouldin=davies_bouldin_score(X_scaled, labels),
        )
        result.cluster_sizes = {str(i): int(np.sum(labels == i)) for i in range(n_clusters)}
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Agglomerative k={n_clusters}, silhouette={result.silhouette:.3f}"
        return result

    def cluster_gmm(self, X: pd.DataFrame, n_components: int = 3) -> ClusterResult:
        start = datetime.now()
        X_scaled = self._scaler.fit_transform(X.fillna(0))

        gmm = GaussianMixture(n_components=n_components, random_state=42)
        labels = gmm.fit_predict(X_scaled)

        result = ClusterResult(
            method="gmm", n_clusters=n_components, labels=labels.tolist(),
            silhouette=silhouette_score(X_scaled, labels),
        )
        result.cluster_sizes = {str(i): int(np.sum(labels == i)) for i in range(n_components)}
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"GMM k={n_components}, silhouette={result.silhouette:.3f}"
        return result

    def auto_cluster(self, X: pd.DataFrame, max_k: int = 8) -> dict:
        numeric = X.select_dtypes(include=[np.number]).fillna(0)
        if len(numeric.columns) < 2 or len(numeric) < 10:
            return {"error": "Need at least 2 numeric columns and 10 rows"}

        optimal = self.find_optimal_k(numeric.values, range(2, min(max_k + 1, len(numeric))))

        results = {}
        results["kmeans"] = self.cluster_kmeans(numeric, optimal["optimal_k"]).to_dict()
        if len(numeric) > 10:
            results["dbscan"] = self.cluster_dbscan(numeric).to_dict()
        results["agglomerative"] = self.cluster_agglomerative(numeric, optimal["optimal_k"]).to_dict()
        results["gmm"] = self.cluster_gmm(numeric, optimal["optimal_k"]).to_dict()

        best_method = max(results.keys(), key=lambda k: results[k].get("silhouette", 0))
        results["best"] = {"method": best_method, "optimal_k": optimal["optimal_k"]}
        return results

"""Dimensionality Reduction — PCA, t-SNE, UMAP for scraped high-dimensional data."""
import logging
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA, IncrementalPCA
from sklearn.manifold import TSNE

logger = logging.getLogger(__name__)


@dataclass
class DimReduceResult:
    method: str = ""
    n_components: int = 0
    original_features: int = 0
    explained_variance: list[float] = field(default_factory=list)
    cumulative_variance: list[float] = field(default_factory=list)
    total_variance_explained: float = 0.0
    transformed_data: list[list[float]] = field(default_factory=list)
    loadings: dict = field(default_factory=dict)
    component_labels: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "method": self.method, "n_components": self.n_components,
            "original_features": self.original_features,
            "explained_variance": [round(v, 4) for v in self.explained_variance],
            "cumulative_variance": [round(v, 4) for v in self.cumulative_variance],
            "total_variance_explained": round(self.total_variance_explained, 4),
            "transformed_data": self.transformed_data[:200],
            "loadings": self.loadings,
            "component_labels": self.component_labels,
            "duration_ms": round(self.duration_ms, 2),
            "summary": self.summary,
        }


class DimReducer:

    def pca(self, X: pd.DataFrame, n_components: int = None,
            variance_threshold: float = 0.95) -> DimReduceResult:
        start = datetime.now()
        numeric = X.select_dtypes(include=[np.number]).fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(numeric)

        if n_components is None:
            full_pca = PCA().fit(X_scaled)
            cumvar = np.cumsum(full_pca.explained_variance_ratio_)
            n_components = int(np.searchsorted(cumvar, variance_threshold) + 1)
            n_components = max(2, min(n_components, len(numeric.columns)))

        pca = PCA(n_components=n_components)
        transformed = pca.fit_transform(X_scaled)

        loadings = {}
        for i in range(n_components):
            component_name = f"PC{i + 1}"
            top_features = sorted(
                zip(numeric.columns, pca.components_[i]),
                key=lambda x: abs(x[1]), reverse=True
            )[:10]
            loadings[component_name] = {f: round(float(v), 4) for f, v in top_features}

        result = DimReduceResult(
            method="pca", n_components=n_components,
            original_features=len(numeric.columns),
            explained_variance=pca.explained_variance_ratio_.tolist(),
            cumulative_variance=np.cumsum(pca.explained_variance_ratio_).tolist(),
            total_variance_explained=float(np.sum(pca.explained_variance_ratio_)),
            transformed_data=transformed.tolist(),
            loadings=loadings,
            component_labels=[f"PC{i + 1}" for i in range(n_components)],
        )
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"PCA: {len(numeric.columns)}→{n_components} dims, {result.total_variance_explained:.1%} variance"
        return result

    def tsne(self, X: pd.DataFrame, n_components: int = 2,
             perplexity: float = 30.0) -> DimReduceResult:
        start = datetime.now()
        numeric = X.select_dtypes(include=[np.number]).fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(numeric)

        if len(numeric) < 4:
            return DimReduceResult(
                method="tsne", n_components=n_components,
                original_features=len(numeric.columns),
                summary="Insufficient data for t-SNE (need at least 4 samples)",
            )

        actual_perplexity = min(perplexity, max(2, len(numeric) - 1))
        tsne = TSNE(n_components=n_components, perplexity=actual_perplexity,
                    random_state=42, n_iter=1000)
        transformed = tsne.fit_transform(X_scaled)

        result = DimReduceResult(
            method="tsne", n_components=n_components,
            original_features=len(numeric.columns),
            transformed_data=transformed.tolist(),
            component_labels=[f"t-SNE {i + 1}" for i in range(n_components)],
        )
        result.total_variance_explained = 1.0
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"t-SNE: {len(numeric.columns)}→{n_components} dims"
        return result

    def incremental_pca(self, X: pd.DataFrame, n_components: int = 10,
                        batch_size: int = 100) -> DimReduceResult:
        start = datetime.now()
        numeric = X.select_dtypes(include=[np.number]).fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(numeric)

        ipca = IncrementalPCA(n_components=n_components, batch_size=batch_size)
        transformed = ipca.fit_transform(X_scaled)

        result = DimReduceResult(
            method="incremental_pca", n_components=n_components,
            original_features=len(numeric.columns),
            explained_variance=ipca.explained_variance_ratio_.tolist(),
            cumulative_variance=np.cumsum(ipca.explained_variance_ratio_).tolist(),
            total_variance_explained=float(np.sum(ipca.explained_variance_ratio_)),
            transformed_data=transformed.tolist(),
        )
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Incremental PCA: {len(numeric.columns)}→{n_components} dims"
        return result

    def auto_reduce(self, X: pd.DataFrame, target_dim: int = 2) -> dict:
        numeric = X.select_dtypes(include=[np.number]).fillna(0)
        if len(numeric.columns) <= target_dim:
            return {"error": f"Already {len(numeric.columns)} dims, cannot reduce to {target_dim}"}

        results = {}
        try:
            results["pca"] = self.pca(X, target_dim).to_dict()
        except Exception as e:
            results["pca"] = {"error": str(e)}

        if len(numeric) <= 5000:
            try:
                results["tsne"] = self.tsne(X, target_dim).to_dict()
            except Exception as e:
                results["tsne"] = {"error": str(e)}

        best = min(
            [(k, v) for k, v in results.items() if "error" not in v],
            key=lambda x: x[1].get("duration_ms", float("inf")),
            default=None,
        )
        if best:
            results["best"] = {"method": best[0]}
        return results

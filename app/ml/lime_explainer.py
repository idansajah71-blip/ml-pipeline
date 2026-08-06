from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _get_lime():
    try:
        from lime.lime_tabular import LimeTabularExplainer
        return LimeTabularExplainer
    except ImportError:
        return None


LimeTabularExplainer = _get_lime()


class LIMEExplainer:
    """
    LIME (Local Interpretable Model-agnostic Explanations) wrapper.
    
    Provides both global feature importance (aggregated from local explanations)
    and per-prediction explanations using LIME.
    """

    def __init__(self):
        self.explainer = None
        self.is_available = LimeTabularExplainer is not None

    def fit(
        self,
        X_train: np.ndarray,
        feature_names: List[str],
        class_names: Optional[List[str]] = None,
        problem_type: str = 'classification',
        mode: str = 'classification',
    ):
        if not self.is_available:
            logger.warning("LIME not installed. Explainability features will be limited.")
            return

        try:
            categorical_features = []
            for i in range(X_train.shape[1]):
                unique_vals = np.unique(X_train[:, i])
                if len(unique_vals) <= 20:
                    categorical_features.append(i)

            self.explainer = LimeTabularExplainer(
                X_train,
                feature_names=feature_names,
                class_names=class_names,
                categorical_features=categorical_features,
                mode=mode,
                discretize_continuous=True,
            )
        except Exception as e:
            logger.error(f"Failed to initialize LIME explainer: {e}")
            self.explainer = None

    def explain_prediction(
        self,
        model,
        instance: np.ndarray,
        num_features: int = 10,
        top_labels: int = 3,
    ) -> Dict[str, Any]:
        if self.explainer is None:
            return {'error': 'LIME explainer not initialized'}

        try:
            explanation = self.explainer.explain_instance(
                instance,
                model.predict_proba if hasattr(model, 'predict_proba') else model.predict,
                num_features=num_features,
                top_labels=top_labels,
            )

            contributions = []
            for label_idx, exp in explanation.as_list():
                if isinstance(label_idx, str):
                    feature_name = label_idx
                    contribution = exp
                else:
                    feature_name = explanation.feature_names[label_idx] if hasattr(explanation, 'feature_names') and label_idx < len(explanation.feature_names) else f'feature_{label_idx}'
                    contribution = exp
                contributions.append({
                    'feature': feature_name,
                    'contribution': round(float(contribution), 6),
                    'direction': 'positive' if contribution > 0 else 'negative',
                })

            contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)

            return {
                'contributions': contributions[:num_features],
                'intercept': round(float(explanation.intercept), 6) if hasattr(explanation, 'intercept') else 0,
                'prediction_local': round(float(explanation.local_pred), 6) if hasattr(explanation, 'local_pred') else None,
                'score': round(float(explanation.score), 6) if hasattr(explanation, 'score') else None,
            }

        except Exception as e:
            logger.error(f"LIME explanation failed: {e}")
            return {'error': str(e)}

    def explain_global(
        self,
        model,
        X_train: np.ndarray,
        feature_names: List[str],
        n_samples: int = 100,
    ) -> Dict[str, Any]:
        if self.explainer is None:
            return {'error': 'LIME explainer not initialized'}

        try:
            sample_size = min(n_samples, len(X_train))
            indices = np.random.choice(len(X_train), sample_size, replace=False)
            sample = X_train[indices]

            all_contributions = []
            for instance in sample:
                try:
                    exp = self.explainer.explain_instance(
                        instance,
                        model.predict_proba if hasattr(model, 'predict_proba') else model.predict,
                        num_features=len(feature_names),
                        top_labels=1,
                    )
                    for label_idx, feat_contrib in exp.as_list():
                        all_contributions.append(abs(float(feat_contrib)))
                except Exception:
                    continue

            if all_contributions:
                feature_importance = {}
                per_feature = np.array(all_contributions[:len(feature_names)])
                for i, name in enumerate(feature_names[:len(per_feature)]):
                    feature_importance[name] = round(float(per_feature[i]), 6)

                feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
                return {
                    'feature_importance': feature_importance,
                    'n_samples': sample_size,
                    'method': 'lime',
                }

            return {'feature_importance': {}, 'n_samples': 0}

        except Exception as e:
            logger.error(f"LIME global explanation failed: {e}")
            return {'error': str(e)}


def explain_with_lime(
    model,
    X_train: np.ndarray,
    X_instance: Optional[np.ndarray],
    feature_names: List[str],
    class_names: Optional[List[str]] = None,
    problem_type: str = 'classification',
    num_features: int = 10,
    n_global_samples: int = 100,
) -> Dict[str, Any]:
    explainer = LIMEExplainer()
    explainer.fit(
        X_train, feature_names,
        class_names=class_names,
        problem_type=problem_type,
        mode='classification' if problem_type == 'classification' else 'regression',
    )

    result = {'method': 'lime'}

    if X_instance is not None:
        result['prediction_explanation'] = explainer.explain_prediction(
            model, X_instance, num_features=num_features,
        )

    global_result = explainer.explain_global(
        model, X_train, feature_names, n_samples=n_global_samples,
    )
    result['global_importance'] = global_result

    return result

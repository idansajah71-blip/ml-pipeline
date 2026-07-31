import pytest
import pandas as pd
import numpy as np
import io
import os
import tempfile
from app.ml.processor import DataProcessor
from app.ml.trainer import ModelTrainer
from app.ml.pipeline import MLPipeline


@pytest.fixture
def processor():
    return DataProcessor()


@pytest.fixture
def trainer():
    return ModelTrainer()


@pytest.fixture
def pipeline():
    return MLPipeline()


@pytest.fixture
def sample_csv_bytes():
    csv_content = """feature1,feature2,feature3,target
1.0,2.0,3.0,class_a
4.0,5.0,6.0,class_b
7.0,8.0,9.0,class_a
10.0,11.0,12.0,class_b
13.0,14.0,15.0,class_a
16.0,17.0,18.0,class_b
19.0,20.0,21.0,class_a
22.0,23.0,24.0,class_b
"""
    return csv_content.encode()


@pytest.fixture
def sample_df():
    np.random.seed(42)
    n = 100
    return pd.DataFrame({
        'feature1': np.random.randn(n),
        'feature2': np.random.randn(n),
        'feature3': np.random.randn(n),
        'target': np.random.choice(['class_a', 'class_b', 'class_c'], n),
    })


@pytest.fixture
def numeric_df():
    np.random.seed(42)
    n = 100
    return pd.DataFrame({
        'feature1': np.random.randn(n),
        'feature2': np.random.randn(n),
        'feature3': np.random.randn(n),
        'target': np.random.choice([0, 1], n),
    })


class TestDataProcessor:
    def test_load_csv(self, processor, sample_csv_bytes):
        df = processor.load_data(sample_csv_bytes, 'test.csv')
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 8
        assert list(df.columns) == ['feature1', 'feature2', 'feature3', 'target']

    def test_load_unsupported_format(self, processor):
        with pytest.raises(ValueError, match="Unsupported file format"):
            processor.load_data(b'data', 'test.txt')

    def test_get_data_info(self, processor, sample_df):
        info = processor.get_data_info(sample_df)
        assert 'columns' in info
        assert 'dtypes' in info
        assert 'shape' in info
        assert 'statistics' in info
        assert 'head' in info
        assert len(info['columns']) == 4
        assert info['shape'] == (100, 4)

    def test_get_data_info_numeric_types(self, processor, numeric_df):
        info = processor.get_data_info(numeric_df)
        assert info['dtypes']['feature1'] == 'numeric'
        assert info['dtypes']['target'] == 'numeric'

    def test_get_data_info_categorical_types(self, processor, sample_df):
        info = processor.get_data_info(sample_df)
        assert info['dtypes']['target'] == 'categorical'

    def test_preprocess_basic(self, processor, sample_df):
        X_train, X_test, y_train, y_test, metadata = processor.preprocess(
            sample_df, 'target', test_size=0.2, random_state=42
        )
        assert len(X_train) + len(X_test) == len(sample_df)
        assert len(y_train) + len(y_test) == len(sample_df)
        assert 'feature_names' in metadata
        assert 'n_features' in metadata
        assert 'n_classes' in metadata
        assert metadata['n_features'] == 3
        assert metadata['n_classes'] == 3

    def test_preprocess_encodes_categorical(self, processor, sample_df):
        X_train, X_test, y_train, y_test, metadata = processor.preprocess(
            sample_df, 'target', test_size=0.2, random_state=42
        )
        assert all(X_train.dtypes.apply(lambda x: np.issubdtype(x, np.number)))
        assert all(X_test.dtypes.apply(lambda x: np.issubdtype(x, np.number)))

    def test_preprocess_numeric_only(self, processor, numeric_df):
        X_train, X_test, y_train, y_test, metadata = processor.preprocess(
            numeric_df, 'target', test_size=0.3, random_state=42
        )
        assert len(X_train) + len(X_test) == 100
        assert 'scaled_columns' in metadata

    def test_preprocess_input(self, processor, sample_df):
        processor.preprocess(sample_df, 'target', test_size=0.2, random_state=42)
        input_data = [{'feature1': 1.0, 'feature2': 2.0, 'feature3': 3.0}]
        result = processor.preprocess_input(input_data, ['feature1', 'feature2', 'feature3'])
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ['feature1', 'feature2', 'feature3']
        assert len(result) == 1


class TestModelTrainer:
    def test_train_random_forest(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='random_forest')
        assert model is not None
        assert info['algorithm'] == 'random_forest'
        assert 'parameters' in info
        assert 'trained_at' in info

    def test_train_gradient_boosting(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='gradient_boosting')
        assert info['algorithm'] == 'gradient_boosting'

    def test_train_logistic_regression(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='logistic_regression')
        assert info['algorithm'] == 'logistic_regression'

    def test_train_svm(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='svm')
        assert info['algorithm'] == 'svm'

    def test_train_knn(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='knn')
        assert info['algorithm'] == 'knn'

    def test_train_decision_tree(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='decision_tree')
        assert info['algorithm'] == 'decision_tree'

    def test_train_adaboost(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='adaboost')
        assert info['algorithm'] == 'adaboost'

    def test_train_bagging(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='bagging')
        assert info['algorithm'] == 'bagging'

    def test_train_mlp(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='mlp')
        assert info['algorithm'] == 'mlp'

    def test_train_unknown_algorithm(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        with pytest.raises(ValueError, match="Unknown algorithm"):
            trainer.train(X, y, algorithm='nonexistent')

    def test_train_with_custom_params(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        model, info = trainer.train(X, y, algorithm='random_forest', parameters={'n_estimators': 50})
        assert info['parameters']['n_estimators'] == 50

    def test_evaluate(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        trainer.train(X_train, y_train, algorithm='random_forest')
        metrics = trainer.evaluate(X_test, y_test)
        assert 'accuracy' in metrics
        assert 'precision_macro' in metrics
        assert 'recall_macro' in metrics
        assert 'f1_macro' in metrics
        assert 'confusion_matrix' in metrics
        assert 0 <= metrics['accuracy'] <= 1

    def test_evaluate_without_training(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        with pytest.raises(ValueError, match="Model not trained yet"):
            trainer.evaluate(X, y)

    def test_save_and_load_model(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        trainer.train(X, y, algorithm='random_forest')

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'model.joblib')
            trainer.save_model(filepath)
            assert os.path.exists(filepath)

            new_trainer = ModelTrainer()
            new_trainer.load_model(filepath)
            assert new_trainer.algorithm == 'random_forest'
            assert new_trainer.model is not None

    def test_get_feature_importance(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        trainer.train(X, y, algorithm='random_forest')
        importance = trainer.get_feature_importance(['feature1', 'feature2', 'feature3'])
        assert importance is not None
        assert len(importance) == 3
        assert all(v >= 0 for v in importance.values())

    def test_get_feature_importance_without_training(self, trainer):
        result = trainer.get_feature_importance(['f1', 'f2'])
        assert result is None

    def test_cross_validate(self, trainer, numeric_df):
        X = numeric_df.drop(columns=['target'])
        y = numeric_df['target']
        trainer.train(X, y, algorithm='random_forest')
        cv_results = trainer.cross_validate(X, y, cv=3)
        assert 'accuracy' in cv_results
        assert 'mean' in cv_results['accuracy']
        assert 'std' in cv_results['accuracy']


class TestMLPipeline:
    def test_run_training(self, pipeline, sample_csv_bytes):
        result = pipeline.run_training(
            file_content=sample_csv_bytes,
            filename='test.csv',
            target_column='target',
            algorithm='random_forest',
        )
        assert result['status'] == 'completed'
        assert result['algorithm'] == 'random_forest'
        assert 'metrics' in result
        assert 'accuracy' in result['metrics']
        assert result['metrics']['accuracy'] > 0
        assert 'experiment_id' in result
        assert 'duration_seconds' in result

    def test_run_training_with_custom_params(self, pipeline, sample_csv_bytes):
        result = pipeline.run_training(
            file_content=sample_csv_bytes,
            filename='test.csv',
            target_column='target',
            algorithm='random_forest',
            parameters={'n_estimators': 50},
        )
        assert result['status'] == 'completed'
        assert result['parameters']['n_estimators'] == 50

    def test_run_training_invalid_algorithm(self, pipeline, sample_csv_bytes):
        result = pipeline.run_training(
            file_content=sample_csv_bytes,
            filename='test.csv',
            target_column='target',
            algorithm='nonexistent',
        )
        assert result['status'] == 'failed'
        assert 'error' in result

    def test_run_training_invalid_file(self, pipeline):
        result = pipeline.run_training(
            file_content=b'invalid data',
            filename='test.txt',
            target_column='target',
        )
        assert result['status'] == 'failed'

    def test_predict(self, pipeline, sample_csv_bytes):
        pipeline.run_training(
            file_content=sample_csv_bytes,
            filename='test.csv',
            target_column='target',
            algorithm='random_forest',
        )
        predictions = pipeline.predict(
            data=[{'feature1': 1.0, 'feature2': 2.0, 'feature3': 3.0}],
            feature_names=['feature1', 'feature2', 'feature3'],
        )
        assert 'predictions' in predictions
        assert len(predictions['predictions']) == 1
        assert 'prediction' in predictions['predictions'][0]
        assert 'latency_ms' in predictions

    def test_predict_with_probabilities(self, pipeline, sample_csv_bytes):
        pipeline.run_training(
            file_content=sample_csv_bytes,
            filename='test.csv',
            target_column='target',
            algorithm='random_forest',
        )
        result = pipeline.predict(
            data=[{'feature1': 1.0, 'feature2': 2.0, 'feature3': 3.0}],
            feature_names=['feature1', 'feature2', 'feature3'],
        )
        pred = result['predictions'][0]
        assert 'probability' in pred
        assert 'probabilities' in pred
        assert pred['probability'] > 0

    def test_predict_without_model(self, pipeline):
        with pytest.raises(ValueError, match="No model loaded"):
            pipeline.predict(
                data=[{'feature1': 1.0}],
                feature_names=['feature1'],
            )

    def test_save_and_load_artifacts(self, pipeline, sample_csv_bytes):
        pipeline.run_training(
            file_content=sample_csv_bytes,
            filename='test.csv',
            target_column='target',
            algorithm='random_forest',
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = pipeline.save_artifacts(tmpdir)
            assert os.path.exists(paths['model_path'])
            assert os.path.exists(paths['processor_path'])
            assert os.path.exists(paths['metadata_path'])

            new_pipeline = MLPipeline()
            metadata = new_pipeline.load_artifacts(tmpdir)
            assert metadata['algorithm'] == 'random_forest'

            predictions = new_pipeline.predict(
                data=[{'feature1': 1.0, 'feature2': 2.0, 'feature3': 3.0}],
                feature_names=['feature1', 'feature2', 'feature3'],
            )
            assert 'predictions' in predictions

    def test_experiment_id_unique(self, pipeline, sample_csv_bytes):
        result1 = pipeline.run_training(
            file_content=sample_csv_bytes,
            filename='test.csv',
            target_column='target',
        )
        result2 = pipeline.run_training(
            file_content=sample_csv_bytes,
            filename='test.csv',
            target_column='target',
        )
        assert result1['experiment_id'] != result2['experiment_id']

    def test_all_algorithms(self, pipeline, sample_csv_bytes):
        algorithms = [
            'random_forest', 'gradient_boosting', 'logistic_regression',
            'svm', 'knn', 'decision_tree', 'adaboost', 'bagging', 'mlp',
        ]
        for algo in algorithms:
            result = pipeline.run_training(
                file_content=sample_csv_bytes,
                filename='test.csv',
                target_column='target',
                algorithm=algo,
            )
            assert result['status'] == 'completed', f"Algorithm {algo} failed"
            assert result['algorithm'] == algo

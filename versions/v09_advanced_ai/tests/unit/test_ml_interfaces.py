import pytest

from core.ml.surrogate import ActiveLearningStrategy, SurrogateModel


def test_surrogate_model_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        SurrogateModel()


def test_active_learning_strategy_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        ActiveLearningStrategy()


def test_concrete_surrogate_must_implement_both_methods():
    class Incomplete(SurrogateModel):
        def fit(self, experiments):
            pass
        # falta predict()

    with pytest.raises(TypeError):
        Incomplete()


def test_concrete_surrogate_with_both_methods_instantiates():
    class Minimal(SurrogateModel):
        def fit(self, experiments):
            self.fitted = True

        def predict(self, inputs):
            return {"prediction": "not_validated"}

    instance = Minimal()
    instance.fit([])
    assert instance.predict({}) == {"prediction": "not_validated"}

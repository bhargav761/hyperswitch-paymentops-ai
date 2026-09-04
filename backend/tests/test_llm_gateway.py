from app.llm.gateway import LLMGateway, LLMProvider


class FakeProvider(LLMProvider):
    def generate(self, *, prompt, context=None):
        return f"fake:{prompt}"


def test_gateway_delegates_to_provider():
    gateway = LLMGateway(FakeProvider())

    result = gateway.generate(
        prompt="Why are payments failing?",
        context={"failure_rate": 0.288},
    )

    assert result == "fake:Why are payments failing?"


def test_gateway_is_provider_neutral():
    gateway = LLMGateway(FakeProvider())

    assert gateway.generate(prompt="test") == "fake:test"

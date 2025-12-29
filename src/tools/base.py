from abc import ABC, abstractmethod

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description for the model to understand what the tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON schema for the parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs):
        pass

    def to_ollama_format(self):
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': self.parameters
            }
        }

from abc import ABC, abstractmethod

class BaseProvider(ABC):
    @abstractmethod
    def generate_response(self, messages, tools=None):
        pass

    @abstractmethod
    def stream_response(self, messages, tools=None):
        pass

    @abstractmethod
    def list_models(self):
        pass

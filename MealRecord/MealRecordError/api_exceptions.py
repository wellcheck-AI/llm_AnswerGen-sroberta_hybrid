
class InvalidAPIKeyError(Exception):
    def __init__(self, message:str="Invalid API key attempt", provided_api_key:str=None):
        self.message = message
        self.provided_api_key = provided_api_key
        super().__init__(self.message)

    def __str__(self):
        return f"InvalidAPIKey: {self.message}"

    def metadata(self):
        return {"providedKey": self.provided_api_key}
    

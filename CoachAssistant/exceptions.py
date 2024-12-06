class PineconeIndexNameError(Exception):
    def __str__(self):
        return "index does not exists"
    
class PineconeUnexceptedException(Exception):
    def __init__(self, error_log):
        super().__init__(f"{str(error_log)}\nPineconeUnexceptedException")

class InvalidInputError(Exception):
    def __init__(self, message:str="Invalid Input"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"InvalidInputError: {self.message}"
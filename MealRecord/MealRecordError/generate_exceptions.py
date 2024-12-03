class ResponseParsingError(Exception):
    def __init__(self, message:str="Response parsing failed.", raw_response:str=""):
        self.message = message
        self.raw_response = raw_response
        super().__init__(self.message)

    def __str__(self):
        return f"ResponseParsingError: {self.raw_response}"
    
class GenerationFailedError(Exception):
    def __init__(self, message:str="AI unable to calculate nutrition", food_name:str=""):
        self.food_name = food_name
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"GenerationFailed: {self.message}(Input: {self.food_name})"
    
class NutritionError(Exception):
    def __init__(self, message:str="Invalid nutrient values", nutrition:dict=None):
        self.message = message
        self.nutrition = nutrition
        super().__init__(self.message)

    def __str__(self):
        return f"NutritionError: {self.message}"    
    
    def metadata(self):
        return self.nutrition
    
class InvalidInputError(Exception):
    def __init__(self, message:str="Missing or empty food name", inform_msg:str="", extra:dict=None):
        self.message = message
        self.extra = extra
        self.inform_msg = inform_msg
        super().__init__(self.message)

    def __str__(self):
        return f"InvalidFoodName: {self.message}"

    def metadata(self):
        return {"body": self.extra}
    
    def inform_message(self):
        return self.inform_msg
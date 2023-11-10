class Storage():
        def __init__(self):
            self.models = []
            self.n_of_models = 0

        def save_model(self, model):
            self.models.append(model)
            self.n_of_models = len(self.models)

        def delete_model(self, model_index):
            del self.models[model_index]
            self.n_of_models = len(self.models)
            
        def print_model(model_index):
            pass
        
        def get_models_numbered(self):

            model_numbers = range(len(self.models))
            models_and_model_numbers = zip(model_numbers, self.models)
            
            return models_and_model_numbers

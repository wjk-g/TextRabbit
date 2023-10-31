class Storage():
        def __init__(self):
            self.models = []
            self.n_of_models = 0

        def save_model(self, model):
            self.models.append(model)
            self.n_of_models = len(self.models)
        
        def return_html_summary(self):

            model_number = 0
            
            rows = ""
            for model in self.models:
                model_number += 1
                single_model = f"""
                    <tr>
                        <td>
                            {model_number}
                        </td>
                        <td>
                            {model.model_type}
                        </td>
                        <td>
                            {model.n_clusters}
                        </td>
                        <td>
                            {model.created_at}
                        </td>
                        <td>
                            <form name="download-{model_number}" class="table-buttons"><input type="submit" value="pobierz"></form>
                        </td>
                        <td>
                            <form name="remove-{model_number}" class="table-buttons"><input type="submit" value="usuń"></form>
                        </td>
                    </tr>
                    """
                rows += single_model
            
            table = f"<table><th></th><th>model</th><th>l. klastrów</th><th>data utworzenia</th><th></th><th></th>{rows}</table>"
            
            return table
                

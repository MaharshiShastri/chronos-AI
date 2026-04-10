from sentence_transformers import SentenceTransformer
import torch

class Embedder:
    def __init__(self, model_name="all-MiniLM-L6-V2"):
        #Downloading/Updating and loading the model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- RAG: Initializing Embedder on [{self.device.upper()}] ---")
        
        self.model = SentenceTransformer(model_name, device=self.device)
        self.model.encode(["warmup"])
        print(f"--- RAG: {model_name} Loaded Successfully on {torch.cuda.get_device_name(0)} ---")

    def generate_embeddings(self, text_list):
        #Turn a list of string into vector representation

        if isinstance(text_list, str): #If string type variable, then convert to list using list declaration
            print(f"Type of text_list was string: {text_list}")
            text_list = [text_list]
            print(f"Now the type of text_list is list: {text_list}")
        
        embeddings = self.model.encode(text_list, show_progress_bar=False)
        return embeddings #Return the vector representation of the task_list
    
rag_embedder = Embedder()
        
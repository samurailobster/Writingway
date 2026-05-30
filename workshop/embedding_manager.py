# embedding_manager.py
import faiss
import numpy as np
import tiktoken


# For demonstration, we use a dummy embedding function.
# In practice, you would replace this with a call to an embedding model/API.
def get_embedding(text):
    # Convert text to a fixed-size vector.
    # Here we use a simple example by encoding tokens and normalizing.
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    token_ids = encoding.encode(text)
    vector = np.array(token_ids, dtype=np.float32)
    # Pad or truncate to fixed size, e.g., 128 dimensions.
    desired_dim = 128
    if vector.shape[0] < desired_dim:
        vector = np.pad(vector, (0, desired_dim - vector.shape[0]), 'constant')
    else:
        vector = vector[:desired_dim]
    return vector

class EmbeddingIndex:
    def __init__(self, dim=128):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.texts = []  # To keep a mapping of index to text

    def add_text(self, text):
        vector = get_embedding(text)
        vector = np.expand_dims(vector, axis=0)  # FAISS expects 2D array
        self.index.add(vector)
        self.texts.append(text)

    def query(self, text, k=3):
        vector = get_embedding(text)
        vector = np.expand_dims(vector, axis=0)
        distances, indices = self.index.search(vector, k)
        results = []
        for idx in indices[0]:
            # Skip indices that are -1 (indicating no result)
            if idx == -1:
                continue
            if idx < len(self.texts):
                results.append(self.texts[idx])
        return results

# Example usage:
if __name__ == "__main__":
    ei = EmbeddingIndex()
    ei.add_text("This is the first conversation chunk.")
    ei.add_text("Another important scene with key details.")
    ei.add_text("A random off-topic discussion.")
    results = ei.query("key details")
    print("Query results:", results)

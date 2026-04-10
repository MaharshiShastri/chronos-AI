from embedder import rag_embedder

test_text = ["Hello, how are you doing?", "Its a really hot day, hope it gets cooler at night", "An Ice-Cream might be useful"]
vector = rag_embedder.generate_embeddings(test_text)

print(f"Text: {test_text}")
print(f"Vector Shape: {vector.shape}")
print(f"First 5 numbers: {vector[0][:5]}")
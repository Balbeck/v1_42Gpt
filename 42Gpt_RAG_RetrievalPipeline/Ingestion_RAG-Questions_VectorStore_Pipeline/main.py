import json
import os
import requests

# - - - [ Variables ] - - -
DOCUMENTS_BASE_PATH = ".." # -> A modifier pour standardiser et securiser !!!

JSON_FILE_TO_EMBED = "../LLMWiki/claudeQuestions.json"
OLLAMA_BASE_URL = "http://localhost:11434"

# OLLAMA_EMBEDDING_MODEL = "embeddinggemma:300m" # dim: 768
OLLAMA_EMBEDDING_MODEL = "snowflake-arctic-embed:335m" # dim: 1024
# OLLAMA_EMBEDDING_MODEL = "qwen3-embedding:8b" # dim: 4096 

# DB sur Base JSON (Fichier de stockage des vecteurs -> on Retrive en calculant avec numpy ^^ )
VECTOR_DB_PATH = "../LLMWiki/vector_store.json"
# - - - - - - - - - - - -





# - - - [ STOCKAGE JSON ] - - - (Au lieu de ChromaDB)
# On stocke une liste dans fichier JSON
# Chaque entry ressemble a :
# {
#     "filename": "python_intro.md",
#     "question": "Qu'est-ce qu'une liste ?",
#     "embedding": [0.12, -0.87, 0.34, ...]
# }
def save_to_json_store(filepath: str, question: str, embedding: list[float]):
	"""
	Ajoute une entree (filename + question + vecteur) dans le fichier JSON.
	Si le fichier existe deja, on charge son contenu et on ajoute dedans.
	"""

	if os.path.exists(VECTOR_DB_PATH):
		with open(VECTOR_DB_PATH, "r", encoding="utf-8") as f:
			store = json.load(f)
	else:
		store = []

	store.append({
		"filepath": filepath,
		"question": question,
		"embedding": embedding
	})

	with open(VECTOR_DB_PATH, "w", encoding="utf-8") as f:
		json.dump(store, f, ensure_ascii=False, indent=2)




def generate_embedding(text: str) -> list[float] | None:
	url = f"{OLLAMA_BASE_URL}/api/embeddings"
	payload = {
		"model": OLLAMA_EMBEDDING_MODEL,
		"prompt": text
	}

	try:
		response = requests.post(url, json=payload, timeout=30)
		response.raise_for_status() # Exception if HTTP error code
		data = response.json()
		embedding = data.get("embedding")

		if embedding is None:
			print(f" ❌ Ollama n'a pas retourné d'embedding pour : '{text}'")
			return None

		return embedding 

	except requests.exceptions.ConnectionError:
		print(f" ❌ [ Error ] Impossible de contacter Ollama sur {OLLAMA_BASE_URL}")
		return None
	except requests.exceptions.Timeout:
		print(f" ❌ [ Error ] Ollama Timeout -> 30s")
		return None
	except Exception as e:
		print(f" ❌ [ Error ] Inattendue lors de l'appel Ollama : {e}")
		return None





def load_and_index(json_path: str):
	"""   
	Format JSON attendu :
	{
		"documents": [
			{
				"filename": "nom_du_fichier.md",
				"questions": [
					"Question 1 ?",
					"Question 2 ?",
				]
			}
		]
	}
	"""
	# Path verif
	if not os.path.exists(json_path):
		print(f" ❌ Fichier introuvable : {json_path}")
		return

	# Lecture JSON
	with open(json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	documents = data.get("documents", [])
	print(f"📚 {len(documents)} documents trouves\n")
		
	for doc in documents:
		filepath = doc.get("filename", "inconnu")
		questions = doc.get("questions", [])
		# print(f"  📄 Document : {filepath} - {len(questions)} question(s)")

		full_path = DOCUMENTS_BASE_PATH + filepath
		# print(f"🔨 full_path: [ {full_path} ]")
		if not os.path.exists(full_path):
			print(f"‼️  Error fichier inexistant: [ {full_path} ]")
		# print(f"  📄 {filepath}  ({len(questions)} questions")
		
		for i, question in enumerate(questions, start=0):
			print(f"       -> {question}")
			embedding = generate_embedding(question)

			if embedding is None:
				print(f" ❌ Embedding failed... continue.")
				continue

			save_to_json_store(filepath, question, embedding)
			# print(f"	✅ JSON Store  —> vecteur dim: {len(embedding)}")

	print(f"✅ Embeding Done -> JSON store : {VECTOR_DB_PATH}")



if __name__ == "__main__":
    load_and_index(JSON_FILE_TO_EMBED)

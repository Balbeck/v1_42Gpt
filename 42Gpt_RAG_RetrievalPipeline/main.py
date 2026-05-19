import json
import os
import requests
import numpy as np


# - - - [ Variables ] - - -
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_GENERATION_MODEL = "mistral:latest" #mistral7B

# OLLAMA_EMBEDDING_MODEL = "embeddinggemma:300m" # dim: 768
OLLAMA_EMBEDDING_MODEL = "snowflake-arctic-embed:335m" # dim: 1024
# OLLAMA_EMBEDDING_MODEL = "qwen3-embedding:8b" # dim: 4096 

VECTOR_DB_PATH = "./LLMWiki/vector_store.json"

#Ou sont les fichier raw .md
DOCUMENTS_FOLDER = "."
TOP_K = 5 # Nbr Max results to return
MAX_DOCS = 2 # Nbr max full doc to use in final prompt
MIN_SCORE = 0.85 #Score Mini de similarite entre [0 - 1]
# - - - - - - - - - - - -



def generate_embedding(text: str) -> list[float] | None:
	"""
	Transforme un texte en vecteur via Ollama.
	"""
	url = f"{OLLAMA_BASE_URL}/api/embeddings"
	payload = {
		"model": OLLAMA_EMBEDDING_MODEL,
		"prompt": text
	}

	try:
		response = requests.post(url, json=payload, timeout=30)
		response.raise_for_status()
		data = response.json()
		return data.get("embedding")

	except requests.exceptions.ConnectionError:
		print(f" ❌ [ Error ] Impossible de contacter Ollama sur {OLLAMA_BASE_URL}")
		return None
	except Exception as e:
		print(f" ❌ [ Error ] {e}")

		return None


# ==============================================================================
# RETRIEVAL 3A : RECHERCHE DANS LE JSON STORE (numpy)
# ==============================================================================
#
# La similarité cosinus mesure l'angle entre deux vecteurs.
# Formule :
#
#        A · B
#   ─────────────────    (produit scalaire divisé par le produit des normes)
#   ‖A‖ × ‖B‖
#
# Résultat entre -1 et 1 :
#   1.0  → textes identiques en sens
#   0.0  → textes sans rapport
#  -1.0  → textes de sens opposé
#
# numpy nous permet de faire ce calcul sur TOUS les vecteurs stockés
# en une seule opération (pas de boucle for), c'est très rapide.
# ==============================================================================

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
	"""
	Calcule la similarité cosinus entre deux vecteurs numpy.
	"""
	dot_product = np.dot(vec_a, vec_b)           # A · B
	norm_a = np.linalg.norm(vec_a)               # ‖A‖
	norm_b = np.linalg.norm(vec_b)               # ‖B‖

	if norm_a == 0 or norm_b == 0:
		return 0.0  # Évite une division par zéro

	return dot_product / (norm_a * norm_b)


def search_json_store(query_embedding: list[float], top_k: int = TOP_K) -> list[dict]:
	"""
	Cherche les entrées les plus similaires dans le fichier JSON.
	1. Charger tous les vecteurs stockés
	2. Calculer la similarité cosinus entre la question et chaque vecteur
	3. Trier par score décroissant
	4. Retourner les top_k meilleurs résultats

	Retourne une liste de dicts :
	[
		{ "filepath": ..., "question": ..., "score": ... },
		...,
	]
	"""
	if not os.path.exists(VECTOR_DB_PATH):
		print(f" ❌ [ Error ] JSON store introuvable : {VECTOR_DB_PATH}")
		return []

	with open(VECTOR_DB_PATH, "r", encoding="utf-8") as f:
		store = json.load(f)

	if not store:
		print(" ❌ [ Error ] Le JSON store est vide.")
		return []

	# Convertit le vecteur de la question en array numpy
	query_vec = np.array(query_embedding)

	# Calcul des scores pour chaque entrée stockée
	results = []
	for entry in store:
		stored_vec = np.array(entry["embedding"])
		score = cosine_similarity(query_vec, stored_vec)
		results.append({
			"filepath": entry["filepath"],
			"question": entry["question"],
			"score": score
		})

	# Tri par score décroissant, on garde les top_k
	results.sort(key=lambda x: x["score"], reverse=True)
	return results[:top_k]



def print_results(title: str, results: list[dict]):
	"""
	Affiche les résultats de recherche de façon lisible.
	"""
	print(f"\n  {'─' * 50}")
	print(f"  {title}")
	print(f"  {'─' * 50}")

	if not results:
		print(" ‼️ Aucun résultat.")
		return

	for rank, r in enumerate(results, start=1):
		print(f"  #{rank}  📄 {r['filepath']}  (score: {r['score']:.4f})")
		print(f"       Question indexée : {r['question']}")




# ==============================================================================
# DÉDUPLICATION ET SÉLECTION DES DOCUMENTS
# ==============================================================================
#
# Problème : TOP_K=n peut retourner plusieurs entrées pour le même fichier.
# Ex: python_intro.md apparaît 3 fois avec des scores différents.
#   - On parcourt les résultats triés par score (le meilleur en premier)
#   - On ajoute un filename dans la liste de sortie seulement s'il n'y est pas déjà
#   - On s'arrête dès qu'on a MAX_DOCS fichiers uniques
#
# Retourne une liste de paths complets vers les fichiers .md
# ==============================================================================
def deduplicate_and_select(results: list[dict], max_docs: int = MAX_DOCS) -> list[str]:
	seen_filepath = set()
	selected_paths = []

	for result in results:
		if result["score"] < MIN_SCORE:
			break

		filepath = result["filepath"]
		if filepath not in seen_filepath:
			seen_filepath.add(filepath)
			path = DOCUMENTS_FOLDER + filepath
			selected_paths.append(path)
			print(f"\t\t✅ Sélectionné : {filepath}  (score: {result['score']:.4f})")

			if len(selected_paths) >= max_docs:
				break

	return selected_paths



def read_documents(doc_paths: list[str]) -> dict[str, str]:
	contents = {}

	for path in doc_paths:
		filename = os.path.basename(path)
		if not os.path.exists(path):
			print(f" ❌ [ Error ] - Fichier introuvable : {path}")
			print(f" -> Check that '{filename}' is in [ '{DOCUMENTS_FOLDER}' ]")
			continue

		with open(path, "r", encoding="utf-8") as f:
			contents[filename] = f.read()
		# print(f"   📖 {filename}  ({len(contents[filename])} chars)")

	return contents



def generate_finale_answer(query: str, doc_contents: dict[str, str]) -> str:
	"""
	Envoie la question + les documents à Mistral 7b via Ollama.
	Retourne la réponse générée sous forme de string.
	"""
	if not doc_contents:
		return " ❌ Aucun document disponible pour générer une réponse."

	# Construction du contexte : on concatène tous les documents
	context_parts = []
	for filename, content in doc_contents.items():
		context_parts.append(f"--- Document : {filename} ---\n{content}")

	context = "\n\n".join(context_parts)

	prompt = f"""Tu es un assistant qui répond aux questions en se basant uniquement sur les documents fournis.

DOCUMENTS DE REFERENCE :
{context}

QUESTION :
{query}

INSTRUCTIONS :
- Réponds uniquement à partir des informations contenues dans les documents ci-dessus.
- Si la réponse ne s'y trouve pas, dis-le clairement.
- Sois précis !
- Tu dois etre le plus exhaustif possible !
- Si besoin renvoie l'integralite des informations du DOCUMENTS DE REFERENCE.

RÉPONSE :"""

	url = f"{OLLAMA_BASE_URL}/api/generate"
	payload = {
		"model": OLLAMA_GENERATION_MODEL,
		"prompt": prompt,
		"stream": False    # On attend la réponse complète
	}

	try:
		print(f"\t🤖 Send request to {OLLAMA_GENERATION_MODEL}...")
		response = requests.post(url, json=payload, timeout=120)
		response.raise_for_status()

		data = response.json()
		return data.get("response", "[ERREUR] Pas de réponse dans la réponse Ollama.")

	except requests.exceptions.ConnectionError:
		return f" ❌ [ Error ] Impossible de contacter Ollama sur {OLLAMA_BASE_URL}"
	except requests.exceptions.Timeout:
		return " ❌ [ Error ] Mistral n'a pas répondu dans les temps (timeout 120s)"
	except Exception as e:
		return f" ❌ [ Error ] {e}"




if __name__ == "__main__":
	print(f"Modèle : {OLLAMA_EMBEDDING_MODEL}  |  Top-K : {TOP_K}")
	print()

	#  - [1] - [ Query / Question ] - - -
	query = input("Pose ta question : ").strip()
	if not query:
		print(" ❌ Question/Query vide")
		exit(1)


	#  - [2] - [ Embeding de la Query ] - - -
	print(f"🫆 Generate Embeding: '{query}'")
	query_embedding = generate_embedding(query)
	if query_embedding is None:
		print(" ❌ [ Error ] in embeding generation")
		exit(1)


	# - [3] - [ Recherche: Calcul Similarite cosinus Pour get top k results ] - - -
	print(f"\t🔎 Recherche dans le JsonStore ^^ ...")
	results = search_json_store(query_embedding) # Recherche via JSON store
	if not results:
		print(" ❌ Nothing Found")
		exit(1)
	print_results("🗂  Résultats JSON + numpy", results)


	# - [4] - [ Selection des Doc a donner en contexte au LLM ] - - -
	print(f"\t📚 Selection des documents (max {MAX_DOCS})...")
	selected_paths = deduplicate_and_select(results)
	if not selected_paths:
		print(" ❌ Aucun document sélectionné.")
		exit(1)


	# - [5] - [ Get/Read files ] - - -
	print(f"\t📚 Lecture des documents...")
	doc_contents = read_documents(selected_paths)
	if not doc_contents:
		print(" ❌ Aucun document lisible.")
		exit(1)
 

	# - [6] - [ Final Answer Generation ] - - -
		# Send formated final answer to User
	answer = generate_finale_answer(query, doc_contents)
	print("\n🤖  - *[ Response ]* -  🤖")
	print(answer)
	print("-" * 60)
	print()

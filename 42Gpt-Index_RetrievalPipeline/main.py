
import ast
import json
import os
import re
import requests


# 				- - - [ Variables ] - - -
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_GENERATION_MODEL = "mistral:latest" #mistral7B

DOCUMENTS_FOLDER = "./LLMWiki/documents/"
INDEX_PATH = "./LLMWiki/index.md"
MAX_DOCS = 2 # Nombre max de doc utilises pour le context
# 				- - - - - - - - - - - -



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



def generate_index_answer(query: str, index: str)-> str:
	# Envoie Question + Index au LLM
	prompt = f"""
		Tu es un assistant qui répond aux questions en se basant uniquement sur les documents fournis.
		INDEX :
		{index}

		QUESTION :
		"{query}"

		INSTRUCTIONS :
		- Réponds uniquement à partir des informations contenues dans l'index.
		- Si aucun document ne semble pertinent, retourne UNIQUEMENT [].
		- Sois précis !
		- tu peux identifier MAXIMUM {MAX_DOCS} documents! ou moins si necessaire !
		- Si tu penses que la reponse a la QUESTIONn peut etre dans un des documents references dans l'index dans ce cas
		Retourne UNIQUEMENT [] contenant le path du ou des documents.

		RÉPONSE :
	"""

	url = f"{OLLAMA_BASE_URL}/api/generate"
	payload = {
		"model": OLLAMA_GENERATION_MODEL,
		"prompt": prompt,
		"stream": False # Wait reponse complete
	}


	try:
		print(f"📜 [ Check Index.md ] with {OLLAMA_GENERATION_MODEL}...")
		response = requests.post(url, json=payload, timeout=120)
		response.raise_for_status()
		data = response.json()

		return data.get("response", " ❌ [ Error ] Pas de reponse dans la reponse Ollama.")

	except requests.exceptions.ConnectionError:
		return f" ❌ [ Error ] Impossible to connect to {OLLAMA_BASE_URL}"
	except requests.exceptions.Timeout:
		return f" ❌ [ Error ] {OLLAMA_GENERATION_MODEL} did not respond on time (timeout 120s)"
	except Exception as e:
		return f" ❌ [ Error ] {e}"




def generate_finale_answer(query: str, doc_contents: dict[str, str]) -> str:
	# Envoie Question + Docs au LLM

	if not doc_contents:
		return " ❌ Aucun document disponible pour générer une réponse."

	context_parts = []
	for filename, content in doc_contents.items():
		context_parts.append(f"--- Document : {filename} ---\n{content}\n")

	context = "\n".join(context_parts)

	prompt = f"""
		Tu es un assistant qui répond aux questions en se basant uniquement sur les documents fournis.
		DOCUMENTS DE RÉFÉRENCE :
		{context}

		QUESTION :
		"{query}"

		INSTRUCTIONS :
		- Réponds uniquement à partir des informations contenues dans les documents ci-dessus.
		- Si la réponse ne s'y trouve pas, dis-le clairement.
		- Sois tres précis, exhaustif et surtout n'inventes rien !
		- Si besoin renvoie les informations integrales des documents.

		RÉPONSE :
	"""

	url = f"{OLLAMA_BASE_URL}/api/generate"
	payload = {
		"model": OLLAMA_GENERATION_MODEL,
		"prompt": prompt,
		"stream": False # Wait reponse complete
	}


	try:
		print(f"🤖 Envoi a {OLLAMA_GENERATION_MODEL}...")
		response = requests.post(url, json=payload, timeout=120)
		response.raise_for_status()
		data = response.json()

		return data.get("response", " ❌ [ Error ] Pas de reponse dans la reponse Ollama.")

	except requests.exceptions.ConnectionError:
		return f" ❌ [ Error ] Impossible to connect to {OLLAMA_BASE_URL}"
	except requests.exceptions.Timeout:
		return f" ❌ [ Error ] {OLLAMA_GENERATION_MODEL} did not respond on time (timeout 120s)"
	except Exception as e:
		return f" ❌ [ Error ] {e}"




def parse_index_response(text: str) -> list[str]:
	# Extrait le 1er [...] de la reponse LLM et le parse en liste Python
	match = re.search(r"\[.*?\]", text, re.DOTALL)
	if not match:
		return []
	try:
		value = ast.literal_eval(match.group(0))
		return [str(p) for p in value] if isinstance(value, list) else []
	except (ValueError, SyntaxError):
		return []




if __name__ == "__main__":

	try:
		#  - [1] - [ Query / Question ] - - -
		query = input("Pose ta question : ").strip()
		if not query:
			print(" ❌ Question/Query vide. See y'a Bro ! 🙋🏼‍♂️")
			exit(1)


		#  - [2] - [ Check Index to see if smt matchs with the Question ] - - -
			# Give LLM Prompt avec Question + Index
			# Response Format JSON:
			# 			- Si LLM identifie docs return path 1 ou 2 docs pertinents
			#			- Si Pas d'info return JSON vide {}
		index = read_documents([INDEX_PATH])
		if not index:
			print(f" ❌ [ Error ] - Fichier introuvable : {INDEX_PATH}")
			exit()
		index_text = index[os.path.basename(INDEX_PATH)]
		index_answer = generate_index_answer(query, index_text)


		#  - [3] - [ Check LLM Index Response ] - - -
			# If {} -> print: 'Je n'ai malheuresement pas de document relatif a votre question dans ma base documentaire, vous pouvez toujours visiter le notion de 42 Paris afin de trouver une reponse'
			# If {docPaths} -> Read les docs dans une var 'docContext' et send Q + docContext au LLM pour final answer
		raw_paths = parse_index_response(index_answer)
		doc_paths = [os.path.join(DOCUMENTS_FOLDER, p) for p in raw_paths]
		if not doc_paths:
			print("🤖  - *[ Response ]* -  🤖")
			print("  Je n'ai malheureusement pas de document relatif a votre question dans ma base documentaire.")
			print("  Vous pouvez consulter le Notion de 42 Paris pour trouver une reponse.\n")
			exit(0)

		print(f"📚 Lecture des docs...")
		doc_contents = read_documents(doc_paths)
		if not doc_contents:
			print(" ❌ [ Error ] - Aucun document lisible.")
			exit(1)


		#  - [4] - [ Parse & Deliver Final Answer ] - - -
			# Send formated final answer to User
		answer = generate_finale_answer(query, doc_contents)
		print("🤖  - *[ Response ]* -  🤖")
		print(answer)
		print("-" * 60)
		print()


	except Exception as e:
		print(e)

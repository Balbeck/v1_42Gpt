# Etapes Developpement Simple.
## Overview Dev General:
 - Pipeline [ Ingestion ]:
	- Pipeline [ Get/Gather Documents from Srcs ] -> scraping, pdf, docx, md ... 
		- (save Sources, URL pour chaque Doc + organiser par Sources, fileSystem)
	- Pipeline [ Maintient a Jour Docs presents ] -> dif sha 256, Cron...
	- Pipeline [ Formating Docs ] -> Tout en .md, format avec source, meta...
	- Pipeline [ Classification - Enrichissement ] -> Index OR Embedings OR Mix

 - Pipeline [ Retrieval ]:
	- UserQuestion
	- Check if data related (according method, Index vs Embeding vs Mix)
	- Generate Answer -> 'No Datas related' OR 'Final prompt UserQ + Docs'

## Etapes [ Ingestion - Preparation ]
 - 1: On dispose des docs au format MD cleanned pour un dossier wiki, donc: 
 	- On Skip pour le moment [Pipeline Gather]
	- On Skip pour le moment [Pipeline Mise a Jour]
	- On Skip pour le moment [Pipeline Formating Docs] 
 - 2: Faire [ Pipeline Classification - Organisation des Docs ]
	 - Choisir Methode (Index, Embeding, Mix) !
	 - Choix 1er tests: Index !
	 - Creer programme qui qui orchestre la creation de l'index: 
	 	 - chaque titre sera le path du document
		 - puis un resume avec les mots cles sur le doc

## Etapes [ Retrieval - Inference ]
	 - Framework Simple d'execution !

## Etapes [ Lab ]
	 - Le Lab plus base sur Ingestion ou Retrieval au debut ?
	 - Retrieval je pense ! 
	 - POurvoir generer automatiquement un Json avec toutes les questions couvertes par un document pour le retrival testing 😁
	 - Voir pour avoir une pipeline dedie de test ou on compare les resultats dun test avec le bon docs et la questions. Un LLM compare la reponse finale avec la realite pour voir si il y a des oublies ou des erreurs, imprecisions, hallucinations, erreur de formatage...
	 

# Questions ?:
 - Comment organiser le repo, file system ?
 - Ou mettre le dossier /MdDocs ?
 - 


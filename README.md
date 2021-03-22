# Site des interludes

Ce répo contient le sites des interludes

## Lancement rapide

        git clone https://git.eleves.ens.fr/dlesbre/site-interludes.git &&
        cd site-interlude &&
		python3 -m venv venv &&
		source venv/bin/activate &&
        make start

## Installation

Pour tester modifier le repo, après l'avoir cloné :

1. Créer un [environement
   virtuel](https://docs.python.org/3/tutorial/venv.html) (`python3-venv`)

		python3 -m venv venv

	(si vous le nommez autre chose que venv, ajouter le dossier correspondant
    au `.gitignore`)

2. Lancer l'environnement virtuel

		source venv/bin/activate

3. Installer la dernière version de pip

		python3 -m pip install --upgrade pip

4. Installer les requirements

		pip3 install -r requirements.txt

5. Copier/linker le fichier `interludes/secret_example.py` dans `interludes/secret.py`

		ln -s interludes/secret_example.py interludes/secret.py

6. Faire les les migrations

		make migrate

## Test

Pour pouvoir afficher et tester le site (après avoir tout installé)

1. Lancer l'environnement virtuel si ce n'est pas déjà fait (si le prompt du
   terminal ne commence pas par `(venv)`)

		source venv/bin/activate

2. Lancer le serveur avec

		python manage.py runserver

   Cette commande bloque le terminal, le serveur tourne tant qu'elle n'est pas
   interrompue (par `Ctrl+C` ou autre)

3. Dans un navigateur, le site se trouve à l'adresse
   [http://localhost:8000/](http://localhost:8000/)

4. Créer un compte super-utilisateur avec `make adduser`. Les réglages se modifient depuis les pages d'admin de Django [http://localhost:8000/admin](http://localhost:8000/admin).

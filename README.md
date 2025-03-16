Skanak - Bot Discord

Description

Skanak est un bot Discord personnalisé conçu pour être utilisé sur un seul serveur. Il propose des fonctionnalités d'économie, de gestion de salons, d'interactions amusantes et bien plus.

Installation et Configuration

Clonez le dépôt

git clone https://github.com/skunk2407/Skanak.git
cd Skanak

Installez les dépendances

pip install -r requirements.txt

Créez un fichier .env pour stocker les informations sensibles comme :

DISCORD_TOKEN= "votre_token"
GUILD_ID= "id_du_serveur"
LOG_CHANNEL_ID= "id_du_channel_logs"
WELCOME_CHANNEL_ID= "id_du_channel_bienvenue"

Lancez le bot

python bot.py

Fonctionnalités

1. Système économique (economy/)

Gestion d'un magasin virtuel et d'une monnaie interne.

Commandes :

/shop : Affiche la boutique.

/buy <objet> : Achète un objet.

/add <objet> : Ajoute un objet à la boutique.

/remove <objet> : Retire un objet de la boutique.

!work : Gagne de l'argent en travaillant.

!daily : Récupère une récompense quotidienne.

/balance : Affiche l'argent de l'utilisateur.

2. Commandes Fun (fun_commands/)

!cheese : Une commande mystérieuse 🧀.

3. Gestion des Rôles (roles.py)

Ajout et suppression de rôles aux membres.

4. Messages de Bienvenue (welcome.py)

Envoie un message personnalisé lorsqu'un nouveau membre rejoint le serveur.

5. Anniversaires (birthday.py)

Permet d'enregistrer les anniversaires des membres et de les notifier.

Structure des fichiers

bot.py : Fichier principal du bot.

commands/ : Contient les commandes organisées par catégories.

economy/ : Gestion de l'économie et de la boutique.

fun_commands/ : Commandes d'amusement et d'interaction.

roles.py : Gestion des rôles du serveur.

welcome.py : Gestion de l'accueil des nouveaux membres.

birthday.py : Système d'anniversaires.

.env : Stocke les informations sensibles (exclu du repo).

requirements.txt : Liste des dépendances Python.

Améliorations futures

Ajout d'un système de quêtes pour l'économie.

Amélioration des réactions automatiques aux messages.

Système de logs plus détaillé.

Crédit

Auteur : skunk2407

Ce bot est open-source, n'hésitez pas à proposer des contributions ! 💪


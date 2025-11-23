# Rapport de Projet : Architecture C2 & Keylogger

| Informations | Détails |
| :--- | :--- |
| **Étudiants** | GOUBLE Lilian, SOUVANNAVONG Will |
| **Matière** | STAAVL - [Architecture sécurisée et Analyse de vulnérabilité] |
| **Année** | 2025-2026 |

/!\ Configuration : Ne pas oublier de configurer les IPs dans le script avant utilisation /!\

---

## 1. La Machine Victime (Agent "Spyware V4")

Le code a été développé en **Python** en utilisant les bibliothèques `pynput` pour le clavier, `requests` pour le réseau et `Pillow` pour la gestion des images.

> **Note :** Une aide significative a été apportée par **GEMINI AI** pour la réalisation et l'optimisation des scripts.

### Fonctionnalités implémentées :

* **Identification Unique :** Génération d'un UUID (`uuid4`) au lancement pour distinguer chaque victime de manière unique.
* **Keylogging Nettoyé :** Capture des touches avec filtrage des caractères spéciaux (Shift, Ctrl, Alt) pour rendre le log lisible et fluide ("Human Readable").
* **Surveillance du Presse-Papier (Feature Additionnelle) :** Un thread dédié surveille le changement de contenu du presse-papier (vecteur fréquent de fuite de mots de passe) et l'injecte directement dans les logs.
* **Capture d'écran :** Envoi périodique (toutes les 30s) d'une capture d'écran de la victime, encodée en **Base64** pour le transport léger.
* **Exfiltration HTTP :** Envoi des données via des requêtes `POST` au format JSON vers le serveur attaquant.
* **Résilience :** Utilisation d'un tampon (buffer) mémoire qui stocke les frappes temporairement et force l'envoi (`flush`) en cas d'interruption du programme (`SIGINT`).

## 2. La Machine Attaquante (Serveur C2)

Le serveur a été conçu avec le micro-framework **Flask**. Il répond aux exigences de réception, de traitement et de stockage des données exfiltrées.

### Fonctionnement :

* **Écoute :** Le serveur écoute sur le port `5000`.
* **Réception :** Traitement des objets JSON envoyés par les agents.
* **Stockage Structuré :** Création automatique d'un dossier `loot/{UUID}/` pour chaque nouvelle victime connectée.
* **Séparation des données :**
    * Les textes (frappes et presse-papier) sont ajoutés au fichier `keylog.txt`.
    * Les images Base64 sont décodées et sauvegardées en fichiers `.jpg` horodatés.
* **Gestion du Pare-feu :** Configuration de règles spécifiques pour autoriser le trafic entrant sur le port `5000`.

## 3. Le Contrôleur

Le contrôleur est intégré au serveur sous forme d'endpoints API et d'un Dashboard Web, permettant d'administrer les victimes en temps réel.

### Commandes disponibles :

* `stop_capture` (Pause) : Interrompt temporairement le processus d'enregistrement sur la victime tout en gardant le canal de communication ouvert (Heartbeat).
* `kill` (Arrêt) : Termine définitivement l'agent à distance.

## 4. Execution et preuves

### server.py lancé chez l'attaquant :
<img width="940" height="428" alt="image" src="https://github.com/user-attachments/assets/c996b00b-e88c-411b-8877-cff3474a1a2d" />

### keylogger.py lancé sur la victime : 
<img width="940" height="235" alt="image" src="https://github.com/user-attachments/assets/eb4ab157-5c79-404d-a9d2-71fa69a3ce74" />

### Arrivée des logs :
<img width="940" height="339" alt="image" src="https://github.com/user-attachments/assets/b3eaaf80-646d-48ca-905d-58ec733bac6d" />

### Presse papier toujours print :
<img width="599" height="124" alt="image" src="https://github.com/user-attachments/assets/dc8d6a26-901b-44d6-84ea-8a9455f8a695" />

### Panel de base :
<img width="940" height="510" alt="image" src="https://github.com/user-attachments/assets/fcf6d7a2-5ee6-455c-b698-2a5df2e936b5" />

### Panel avec victime :
<img width="940" height="351" alt="image" src="https://github.com/user-attachments/assets/54ada48a-60cc-4ad1-a54a-35b79e3995dd" />

### Différents états [Lancé, Pause, Kill]
<img width="561" height="186" alt="image" src="https://github.com/user-attachments/assets/033ccf47-f5eb-4e39-b964-7c99222d9a8d" />
<img width="555" height="200" alt="image" src="https://github.com/user-attachments/assets/c8d7601b-a6e2-4943-83d9-d95d97294ef8" />
<img width="554" height="191" alt="image" src="https://github.com/user-attachments/assets/38d5c685-bdcd-41bd-b40f-2660b39481b8" />



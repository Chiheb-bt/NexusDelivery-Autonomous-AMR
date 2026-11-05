# NEXUSDELIVERY — NARRATION TECHNIQUE DU PROOF OF CONCEPT (FR)
## Récit d'Ingénierie & Démonstration du Système Autonome de Bout en Bout
**Auteur :** Chiheb-bt — Chiheb Robotics Systems Lab  
**Projet :** NEXUSDELIVERY (NEXUS Autonomous Urban Last-Mile AMR Platform)  
**Niveau de Maturité :** TRL 3–4 (Validation Expérimentale en Simulation Physique Haute Fidélité)  
**Langue :** Français technique professionnel (première personne du singulier)  
**Cadence Recommandée :** 150 – 160 mots/min  

---

### [00:00 - 00:30] Introduction & Problématique Last-Mile
Bienvenue. Je suis Chiheb-bt, et je vous présente aujourd'hui la validation technique de **NEXUSDELIVERY**, une plateforme robotique mobile autonome conçue pour la livraison urbaine du dernier kilomètre en environnement piétonnier.

La logistique du dernier kilomètre concentre jusqu'à cinquante-trois pour cent du coût total d'acheminement des colis. Notre objectif d'ingénierie est de valider une architecture robotique purement vision — sans aucun capteur LiDAR onéreux et sans dépendance au signal GPS, fréquemment dégradé entre les immeubles urbains.

---

### [00:30 - 01:10] Modèle du Robot & Simulation Physique Gazebo
Voici notre robot mobile simulé sous Gazebo Classic avec son solveur physique ODE à mille Hertz. Il s'agit d'une cinématique différentielle à deux roues motrices actives à bandage caoutchouc et deux roulettes passives stabilisatrices, offrant un rayon de braquage nul indispensable pour les trottoirs étroits.

Le châssis monocoque en aluminium intègre une baie cargo fermée avec une trappe motorisée articulée jusqu'à soixante degrés. La perception repose sur une caméra stéréoscopique de profondeur active RGB-D montée en face avant, couplée à une centrale inertielle six axes et à l'odométrie des roues.

---

### [01:10 - 01:50] Spécifications & Portail Client en Ligne
En parallèle de l'autonomie robotique, nous avons développé la plateforme web opérationnelle complète accessible sur le port localhost huit mille quatre-vingts.

Sur le portail client, l'utilisateur s'authentifie, explore le catalogue de commandes gourmandes ou médicales d'urgence, et sélectionne sa destination directement sur la carte vectorielle de la ville. Les coordonnées de dépose sont vérifiées mathématiquement pour s'assurer qu'elles reposent exclusivement sur des trottoirs navigables et non sur la chaussée routière ou dans des emprises bâties.

---

### [01:50 - 02:40] Suivi de Mission en Temps Réel & Supervision Flotte
Une fois la commande confirmée, le gestionnaire de mission ROS deux assigne le robot depuis le dépôt logistique central. 

Le portail client bascule en mode suivi de mission en direct : la télémétrie Gazebo retransmet la distance restante, la vitesse instantanée, et le flux vidéo direct de la caméra frontale avec détection d'obstacles en temps réel.

Côté exploitation, le Fleet Supervisor Cockpit offre une vue d'ensemble tactique avec localisation odométrique, état de charge de la batterie LiFePO4, état FSM de la machine d'état de sécurité, et contrôle d'arrêt d'urgence logiciel.

---

### [02:40 - 03:40] Remise Sécurisée par Code OTP & Déverrouillage Trappe 60°
Lorsque le robot atteint le seuil du client, il s'immobilise strictement avec une marge inférieure à cinquante centimètres. La machine d'état passe en attente indéfinie du client — sans minuterie prématurée de repli.

Le client saisit son code de sécurité OTP unique à six chiffres généré par HMAC-SHA256. Dès validation du code, la trappe cargo s'ouvre automatiquement à soixante virgule un degrés dans Gazebo, permettant le retrait sécurisé du colis. Dès confirmation par le client, la trappe se verrouille et le robot entame son retour autonome au dépôt logistique.

---

### [03:40 - 04:10] Résultats Expérimentaux & Conclusion
Au terme de notre campagne de validation :
- Cent douze mètres parcourus sans aucune collision.
- Tolérance d'arrêt inférieure à un mètre.
- Cent pour cent des soixante-quinze tests unitaires et d'intégration validés.
- Architecture TRL trois à quatre pleinement établie.

Ce projet démontre la faisabilité concrète d'une autonomie robotique de trottoir accessible, robuste et vérifiable de bout en bout. Merci pour votre attention.

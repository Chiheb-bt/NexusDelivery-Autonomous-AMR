# NEXORA : PROJET DE ROBOT AUTONOME DE LIVRAISON DU DERNIER KILOMÈTRE
## Script de Narration Technique et Récit d'Ingénierie (Voix Première Personne)
**Auteur :** Chiheb Ben Taher  
**Format :** Récit Documentaire d'Ingénierie Robotique  
**Langue :** Français académique et technique fluide  
**Cadence cible :** 150 - 160 mots par minute  
**Durée estimée :** 6 minutes 15 secondes (~970 mots)  
**Voix de synthèse neuronale :** `fr-FR-HenriNeural` (Microsoft Neural TTS)

---

### [00:00 - 00:35] OUVERTURE : LA PROBLÉMATIQUE DU DERNIER KILOMÈTRE

Bienvenue. Je m'appelle Chiheb, et je vous présente aujourd'hui mon projet de fin d'études en ingénierie robotique : NEXORA, une plateforme autonome de livraison urbaine conçue spécifiquement pour les trottoirs piétons.

La logistique du dernier kilomètre représente aujourd'hui plus de cinquante pour cent du coût total d'acheminement des colis. Les camionnettes de livraison encombrent les centres urbains, polluent, et peinent à stationner. 

Mon objectif avec ce projet a été de concevoir, développer et valider de bout en bout un robot mobile autonome capable de naviguer de manière fluide et sécurisée sur les trottoirs, sans GPS et sans capteur LiDAR onéreux, pour livrer un colis directement à la porte du client.

---

### [00:35 - 01:20] CHAPITRE 1 : LE ROBOT ET L'ARCHITECTURE DIFFÉRENTIELLE

Voici mon robot, modélisé en URDF et simulé dans Gazebo avec ses propriétés inertielles et ses contacts physiques réels.

J'ai délibérément choisi une architecture cinématique différentielle à deux roues motrices actives à l'avant, complétée par des roulettes passives stabilisatrices à l'arrière. Ce choix offre un rayon de braquage nul, indispensable pour pivoter sur place dans les couloirs piétons étroits et éviter les obstacles imprévus.

Le châssis intègre une baie cargo fermée, équipée d'une trappe motorisée capable d'une ouverture articulée à soixante degrés. Sur la face avant, l'ensemble de perception repose sur une caméra de profondeur RGB-D calibrée, couplée à une centrale inertielle six axes. 

Pourquoi avoir exclu le LiDAR et le GPS de cette première version ? C'est un choix d'ingénierie assumé : les LiDARs tridimensionnels augmentent drastiquement le coût matériel d'une flotte, tandis que le signal GPS décroche fréquemment dans les canyons urbains entre les immeubles. J'ai donc voulu démontrer qu'une autonomie robuste est possible par simple vision stéréoscopique et odométrie inertielle.

---

### [01:20 - 02:00] CHAPITRE 2 : L'ENVIRONNEMENT DE SIMULATION GAZEBO

Pour valider ce système sans danger, j'ai construit et configuré un environnement de simulation réaliste sous Gazebo Classic, articulé autour du monde Small City Dynamic, sur une grille métrique de cent soixante mètres sur quatre-vingt-seize mètres.

Cet environnement reproduit fidèlement la réalité urbaine : un dépôt logistique central avec ses portes de chargement, un réseau de trottoirs pavés, des bordures de voirie, des intersections régulées par feux tricolores, et des zones de passage piéton.

Des modèles d'obstacles statiques et des piétons dynamiques traversent la trajectoire du robot. La physique ODE calcule en permanence les frottements roue-sol, les glissements et les forces d'impact, garantissant que les comportements observés en simulation reflètent fidèlement les contraintes d'un déploiement physique.

---

### [02:00 - 03:10] CHAPITRE 3 : L'INGÉNIERIE LOGICIELLE SOUS ROS 2

Passons maintenant sous le capot, dans l'architecture logicielle distribuée sous ROS 2 Humble.

Le système s'articule autour de nœuds spécialisés. Le nœud City Driver assure le suivi de trajectoire par un algorithme de Pure Pursuit avec adaptation dynamique de la vitesse en fonction de la courbure du tracé. 

Le pipeline de perception traite en temps réel le flux caméra à trente images par seconde. Une segmentation métrique du couloir avant identifie les obstacles et les piétons, déclenchant un déport latéral sécurisé ou un arrêt d'urgence en deçà d'un mètre de distance.

Au cours du développement, j'ai rencontré deux anomalies critiques qui ont exigé un véritable travail de diagnostic :
Premièrement, une collision systématique contre le mur sud du dépôt. En analysant les coordonnées dans le planificateur d'itinéraire, j'ai découvert que les waypoints de sortie ciblaient un point situé à y égale deux mètres cinquante, directement à l'intérieur du maillage du bâtiment. J'ai corrigé ce bug en verrouillant les coordonnées sur le portail physique vérifié à moins vingt-sept mètres cinquante et moins zéro mètre soixante-quinze.

Deuxièmement, un décalage d'intrinsèques caméra : le code évaluait une résolution fixe de trois cent vingt par deux cent quarante sur un flux Gazebo publié en six cent quarante par quatre cent quatre-vingts, aveuglant soixante-quinze pour cent du champ de vision. L'implémentation d'intrinsèques adaptatifs a immédiatement rétabli une détection complète des piétons.

---

### [03:10 - 04:00] CHAPITRE 4 : L'EXPÉRIENCE CLIENT ET LE COCKPIT DE SUPERVISION

Un robot de livraison n'a de sens que s'il s'intègre dans un service commercial complet. C'est pourquoi j'ai développé un portail client moderne et un cockpit superviseur, reliés à ROS 2 par un serveur Web Bridge sécurisé.

Sur le portail, le client crée son compte, valide son adresse e-mail grâce à un système de jetons cryptographiques, et sélectionne sa destination directement sur une carte interactive validée par la topologie de Gazebo. Les zones interdites, comme l'intérieur des bâtiments ou le milieu des chaussées, sont automatiquement rejetées.

Le cockpit superviseur offre à l'opérateur une traçabilité totale en temps réel : position odométrique, vitesse instantanée, état de la batterie, et surtout, un étiquetage honnête de la provenance des données : télémétrie Gazebo en direct, dernière position connue, ou simulation hors ligne. Aucune donnée simulée n'est déguisée en faux capteur matériel.

---

### [04:00 - 05:30] CHAPITRE 5 : LE CYCLE DE MISSION ET LA REMISE SÉCURISÉE

Voici maintenant une mission complète en direct. Dès que la commande est confirmée, le gestionnaire de mission verrouille le colis dans la soute et affecte le robot.

Le robot quitte le dépôt, franchit le portail avec une marge de sécurité d'un mètre quarante, et s'engage sur le trottoir. Lorsqu'un piéton traverse, la perception visuelle le détecte à quatre mètres. Le contrôleur ralentit, amorce un évitement latéral propre, puis reprend son tracé nominal.

À l'arrivée devant le domicile du client, le robot s'arrête strictement dans une tolérance de cinquante centimètres. 
Auparavant, le code contenait un minuteur de démonstration qui repartait automatiquement après deux secondes. J'ai supprimé cette minuterie : le robot reste désormais immobile indéfiniment en état d'attente client.

Le client reçoit un code de sécurité à six chiffres sur son téléphone. Dès qu'il saisit son code sur le portail, le système valide l'empreinte, et l'actionneur physique de Gazebo ouvre la trappe cargo à soixante degrés. Le client retire son colis et confirme la réception. La trappe se referme, se verrouille, et seulement alors, le robot entame son voyage retour vers le dépôt logistique.

---

### [05:30 - 06:30] CHAPITRE 6 : RÉSULTATS EXPERIMENTAUX ET PERSPECTIVES

Pour valider rigoureusement ce travail, j'ai mis en place une suite de cent trente-deux tests automatisés couvrant la cinématique, la sécurité de la base de données, les contrats d'API et le cycle de mission complet en vingt-quatre étapes. Tous les tests sont validés à cent pour cent sans aucune régression.

Le projet valide aujourd'hui un niveau de maturité technologique TRL trois à quatre en environnement simulé de haute fidélité. 

En toute transparence académique, le passage sur prototype physique nécessitera de résoudre trois défis : l'éblouissement infrarouge de la caméra stéréoscopique sous le soleil zénithal, la dérive odométrique sur de longues distances par l'intégration d'un algorithme d'odométrie visuelle-inertielle, et le portage de l'inférence neuronale sur l'accélérateur Hailo-8L.

Ce projet démontre qu'avec une architecture bien pensée, de la rigueur mathématique et un travail d'ingénierie méthodique, une livraison autonome urbaine fiable et accessible est à portée de main. Je vous remercie pour votre attention.


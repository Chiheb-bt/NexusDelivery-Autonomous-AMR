import asyncio
import os

try:
    import edge_tts
    async def amain():
        voice = "fr-FR-HenriNeural"
        text = """
Bienvenue. Je suis Chiheb Ben Taher, et je vous présente aujourd'hui la validation technique de NEXUSDELIVERY, une plateforme robotique mobile autonome conçue pour la livraison urbaine du dernier kilomètre en environnement piétonnier.

La logistique du dernier kilomètre concentre jusqu'à cinquante-trois pour cent du coût total d'acheminement des colis. Notre objectif d'ingénierie est de valider une architecture robotique purement vision, sans aucun capteur LiDAR onéreux et sans dépendance au signal GPS, fréquemment dégradé entre les immeubles urbains.

Voici notre robot mobile simulé sous Gazebo Classic avec son solveur physique ODE à mille Hertz. Il s'agit d'une cinématique différentielle à deux roues motrices actives à bandage caoutchouc et deux roulettes passives stabilisatrices, offrant un rayon de braquage nul indispensable pour les trottoirs étroits.

Le châssis monocoque en aluminium intègre une baie cargo fermée avec une trappe motorisée articulée jusqu'à soixante degrés. La perception repose sur une caméra stéréoscopique de profondeur active RGB-D montée en face avant, couplée à une centrale inertielle six axes et à l'odométrie des roues.

En parallèle de l'autonomie robotique, nous avons développé la plateforme web opérationnelle complète accessible sur le port local huit mille quatre-vingts.

Sur le portail client, l'utilisateur s'authentifie, explore le catalogue de commandes gourmandes ou médicales d'urgence, et sélectionne sa destination directement sur la carte vectorielle de la ville. Les coordonnées de dépose sont vérifiées mathématiquement pour s'assurer qu'elles reposent exclusivement sur des trottoirs navigables et non sur la chaussée routière ou dans des emprises bâties.

Une fois la commande confirmée, le gestionnaire de mission ROS deux assigne le robot depuis le dépôt logistique central. 

Le portail client bascule en mode suivi de mission en direct : la télémétrie Gazebo retransmet la distance restante, la vitesse instantanée, et le flux vidéo direct de la caméra frontale avec détection d'obstacles en temps réel.

Côté exploitation, le Fleet Supervisor Cockpit offre une vue d'ensemble tactique avec localisation odométrique, état de charge de la batterie LiFePO4, état FSM de la machine d'état de sécurité, et contrôle d'arrêt d'urgence logiciel.

Lorsque le robot atteint le seuil du client, il s'immobilise strictement avec une marge inférieure à cinquante centimètres. La machine d'état passe en attente indéfinie du client, sans minuterie prématurée de repli.

Le client saisit son code de sécurité OTP unique à six chiffres généré par HMAC-SHA256. Dès validation du code, la trappe cargo s'ouvre automatiquement à soixante virgule un degrés dans Gazebo, permettant le retrait sécurisé du colis. Dès confirmation par le client, la trappe se verrouille et le robot entame son retour autonome au dépôt logistique.

Au terme de notre campagne de validation : cent douze mètres parcourus sans aucune collision, tolérance d'arrêt inférieure à un mètre, cent pour cent des tests unitaires et d'intégration validés, et une architecture TRL trois à quatre pleinement établie.

Ce projet démontre la faisabilité concrète d'une autonomie robotique de trottoir accessible, robuste et vérifiable de bout en bout. Merci pour votre attention.
"""
        communicate = edge_tts.Communicate(text.strip(), voice, rate="+2%")
        out_mp3 = "/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY/results/proof_of_concept/final_delivery/NEXUSDELIVERY_VOICEOVER_FR.mp3"
        await communicate.save(out_mp3)
        print("Generated TTS mp3:", out_mp3)

    asyncio.run(amain())
except ImportError:
    print("edge_tts not installed, will check pip")

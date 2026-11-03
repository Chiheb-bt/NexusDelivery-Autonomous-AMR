# NEXORA : PLAN DE MONTAGE & SCÈNES DU FILM D'INGÉNIERIE

**Film :** `NEXORA_ENGINEERING_FILM.mp4` (1080p Full HD @ 30 FPS)  
**Durée Totale :** 390.3 secondes (6 minutes 30 secondes)  
**Narration :** Première personne (Voix d'ingénieur `fr-FR-HenriNeural`)  
**Piste Audio :** `narration_fr.wav` (48 kHz Stéréo)  

---

## Tableau de Découpage des Scènes

| Scène # | Chapitre | Plage Temporelle | Durée | Sujet Visuel Principal (100% Authentique) | Données & Télémétrie en Incrustation (HUD) | Piste Audio |
|:---:|---|:---:|:---:|---|---|:---:|
| **01** | **Ouverture : Problématique du Dernier Kilomètre** | 00:00 – 00:38 | 38.0s | Vue frontale et cinématique du robot `rdsim` dans son dépôt à Gazebo | Modèle URDF authentique, dimensions $0.82\text{m} \times 0.62\text{m}$, masse $22\text{kg}$ | `ch_01.mp3` |
| **02** | **Chapitre 1 : Le Robot & Architecture Différentielle** | 00:38 – 01:38 | 60.0s | Orbite 360° autour du robot : roues différentielles, caméra frontale, soute cargo, trappe motorisée 60° | Cinématique différentielle $v, \omega$, joint `cargo_hatch_joint` ($0.0 \rightarrow 1.05\text{ rad}$) | `ch_02.mp3` |
| **03** | **Chapitre 2 : L'Environnement de Simulation Gazebo** | 01:38 – 02:20 | 42.0s | Visite du monde `small_city_dynamic.world` : trottoirs, passages piétons, feux tricolores, carrefours | Moteur ODE 1000 Hz, grille métrique $160\text{m} \times 96\text{m}$, frottement $\mu=1.0$ | `ch_03.mp3` |
| **04** | **Chapitre 3 : L'Ingénierie Logicielle sous ROS 2** | 02:20 – 03:35 | 75.0s | Graphe computationnel RQT, segmentation du couloir visuel, évitement de piéton, correction bug mur | Fréquence nœuds (Driver 50 Hz, Vision 30 Hz), résolution $640\times480$, bypass supprimé | `ch_04.mp3` |
| **05** | **Chapitre 4 : L'Expérience Client & Cockpit Superviseur** | 03:35 – 04:28 | 53.0s | Interface client moderne, vérification e-mail par jeton, sélection de baie, cockpit superviseur | Provenance télémétrique honnête : `LIVE GAZEBO TELEMETRY`, RBAC, SQLite WAL | `ch_05.mp3` |
| **06** | **Chapitre 5 : Cycle de Mission & Remise Sécurisée** | 04:28 – 05:36 | 68.0s | Départ du dépôt, navigation sur trottoir, arrêt strict 0.5m, attente client indéfinie, validation OTP, ouverture trappe | 20 états de mission, validation OTP 6 chiffres, actionneur de trappe, retour au dépôt | `ch_06.mp3` |
| **07** | **Chapitre 6 : Résultats Expérimentaux & Perspectives** | 05:36 – 06:30 | 54.3s | Graphique de trajectoire odométrique, matrice de 132 tests automatisés (100% succès), roadmap TRL 7-8 | Zéro LiDAR, Zéro GPS, $0.0\text{m}$ collision, latence CPU $14.2\text{ms}$, passage NPU Hailo-8L | `ch_07.mp3` |

---

## 2. Piste Vidéo Teaser (45 Secondes)

| Séquence | Durée | Contenu Visuel | Audio |
|---|:---:|---|---|
| **Accroche** | 00:00 – 00:10 | Orbite dynamique du robot dans Gazebo | Extrait introduction NEXORA |
| **Perception** | 00:10 – 00:22 | Pipeline de vision en direct avec couloir métrique & détection piéton | Explication autonomie caméra-seule |
| **Remise Colis** | 00:22 – 00:35 | Arrivée au pas de porte, validation OTP et ouverture physique de la trappe à 60° | Démonstration du verrouillage sécurisé |
| **Conclusion** | 00:35 – 00:45 | Synthèse des 132 tests et perspectives matérielles | Signature du projet d'ingénierie |


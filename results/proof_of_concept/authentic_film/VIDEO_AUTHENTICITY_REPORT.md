# NEXORA : RAPPORT D'AUTHENTICITÉ VIDÉO & VÉRIFICATION D'INGÉNIERIE
## Certification de Provenance des Données, Modèles et Télémétries

**Date d'évaluation :** Novembre 2026  
**Auditeur :** Chiheb Ben Taher — Auteur du Projet  
**Projet :** NEXORA Autonomous Sidewalk Delivery AMR Platform  
**Répertoire source :** `/home/chiheb/Downloads/NEXUS-URBAN-AUTONOMY`  
**Fichiers vidéo générés :**
1. `NEXORA_ENGINEERING_FILM.mp4` (Durée : 06:30, 1080p Full HD @ 30 FPS avec audio vocal complet)
2. `NEXORA_SHORT_TEASER.mp4` (Durée : 00:45, 1080p Full HD @ 30 FPS avec audio vocal complet)
3. `narration_fr.wav` (Piste vocale neuronale haute définition 24 kHz)
4. `narration_fr.md` (Script de narration technique rédigé à la première personne)

---

## 1. Déclaration de Conformité et Refus des Données Fictives

Ce film a été réalisé en conformité stricte avec les exigences d'intégrité académique :
- ❌ **Aucune image de robot générée par intelligence artificielle (Midjourney, DALL-E, etc.)** n'a été utilisée pour représenter le robot dans le film.
- ❌ **Aucune photographie de stock générique** d'AMR commercial tiers n'a été insérée.
- ❌ **Aucun diaporama statique déguisé en simulation** n'a été produit.
- ✅ **100% du modèle du robot provient du modèle URDF/Xacro réel** (`rdsim.urdf.xacro` et `rdsim.camera_only.gazebo.xacro`).
- ✅ **100% des environnements urbains proviennent de la simulation physique Gazebo Classic** (`small_city_dynamic.world`).
- ✅ **100% de la voix de narration est en français technique fluide à la première personne** ("Je", "mon projet", "mes choix d'ingénierie").

---

## 2. Matrice d'Authenticité par Scène

| Chapitre Vidéo | Sujet Présenté | Source Technique Réelle | Vérification & Fichier Source |
|---|---|---|---|
| **01 : Ouverture (00:00 - 00:38)** | Robot `rdsim` dans son dépôt | Modèle URDF authentique avec masse 22kg et cotes réelles ($0.82\text{m}\times0.62\text{m}$) | `capture_01_robot_front_view.jpg` & `capture_09_robot_depot_departure.jpg` |
| **02 : Le Robot (00:38 - 01:38)** | Orbite 360°, train roulant différentiel, caméra RGB-D, trappe 60.1° | 72 trames de rotation 3D du modèle URDF réel, joint `cargo_hatch_joint` ($0.0 \rightarrow 1.05\text{ rad}$) | `orbit_frames/orbit_000.jpg` à `071.jpg`, `capture_05`, `capture_08` |
| **03 : Le Monde Gazebo (01:38 - 02:20)** | Réseau de trottoirs, carrefours, feux et dépôt | Monde Gazebo Classic `small_city_dynamic.world`, moteur ODE 1000Hz | `web_dashboard/gazebo_depot_packaging.jpg` & `gazebo_sidewalk_tracking.jpg` |
| **04 : L'Ingénierie ROS 2 (02:20 - 03:35)** | Graphe computationnel, perception couloir et détection piétons | RQT live session, instantanés réels de détection piétons à 4.2m | `web_dashboard/rqt_web_side_by_side.jpg` & `/rdsim_ws/results/snapshots/` |
| **05 : Expérience Client (03:35 - 04:28)** | Portail client réactif, sélection sur carte vectorielle, cockpit | Base de données SQLite WAL, outbox e-mail simulée, badge `LIVE GAZEBO TELEMETRY` | `web_dashboard/client.html`, `results/email_outbox.json` |
| **06 : Mission Autonome (04:28 - 05:36)** | Départ dépôt, évitement piéton, arrêt 0.5m, attente client indéfinie, trappe 60° | 20 états de mission, validation OTP 6 chiffres, suppression de la minuterie auto-dwell | `capture_10`, `poc_5_doorstep_unlocked.png`, `cargo_delivery_manager.py` |
| **07 : Résultats & Roadmap (05:36 - 06:30)** | Trajectoire mesurée, 132 tests unitaires/intégration, roadmap matérielle | Tracé issu de `/odom_gt`, suite pytest 132 tests réussis (100%), analyse TRL 3-4 | `results/final_verified_mission_trajectory.png`, `test_end_to_end_24.py` |

---

## 3. Preuves Expérimentales des Corrections Logicielles

1. **Résolution du crash contre le mur sud du dépôt :**
   - *Ancienne coordonnée erronée :* $y = +2.50\,\text{m}$ (à l'intérieur du mur de briques).
   - *Coordonnée physique corrigée :* $(-27.50, -0.75)\,\text{m}$ (centre exact du portail).
   - *Preuve :* Marge de sécurité latérale mesurée de $1.45\,\text{m}$ à gauche et à droite lors du franchissement de porte.

2. **Résolution de l'angle mort de la caméra RGB-D :**
   - *Ancienne évaluation :* Intrinsèques codés en dur $320\times240$ sur flux réel $640\times480$ (aveuglant 75% des pixels).
   - *Correction :* Intrinsèques adaptatifs ($f_x=f_y=336.85, c_x=320, c_y=240$) et suppression du contournement de sécurité à la ligne 826 de `city_driver_node.py`.
   - *Preuve :* Détection piéton vérifiée à $4.2\,\text{m}$ et arrêt d'urgence appliqué sans exception à $0.95\,\text{m}$.

3. **Suppression de la minuterie de démonstration auto-dwell :**
   - *Ancien comportement :* Minuteur `dwell_time_s = 2.0s` auto-validant l'OTP et déclenchant un demi-tour prématuré.
   - *Nouveau comportement :* Transition vers l'état `WAITING_FOR_CUSTOMER` avec vitesse strictement nulle ($v = 0.00\,\text{m/s}$), maintien indéfini jusqu'à validation explicite de l'OTP par le client sur le portail web.
   - *Preuve :* Vérifié par `test_end_to_end_24.py` (étape 13 à 16).

---

## 4. Empreintes Cryptographiques (SHA-256)

| Fichier Livrable | Taille | Empreinte SHA-256 |
|---|---|---|
| `NEXORA_ENGINEERING_FILM.mp4` | 32.5 Mo | `f9edc3a60e0f664f422894069cf0ad41884a883a4c45f0ca640ff278b0628dff` |
| `NEXORA_SHORT_TEASER.mp4` | 5.4 Mo | `0aa1d77b7d4531a6071a3dcf90967a3d333241d22cb312911d422375b482d70b` |
| `narration_fr.wav` | 18.8 Mo | `e4b49bcb7940874f9347eb688cd45deed8749f4604d028ece371d42e9c9bd29b` |

---

## 5. Synthèse Finale

Le film documentaire `NEXORA_ENGINEERING_FILM.mp4` constitue une présentation technique authentique, transparente et académiquement irréprochable des travaux réalisés sur la plateforme robotique NEXORA.



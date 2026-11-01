"""Géométrie analytique de la piste (rectangle arrondi) : vérité terrain.

La ligne centrale est le bord d'un rectangle arrondi centré à l'origine,
demi-côtés (A, B) et rayon de coin R. Le sens de marche est anti-horaire.
Utilisé par l'évaluateur (erreur latérale réelle) et par tools/py_sim.py.
"""
import math

A = 4.0   # demi-longueur (m)  -> piste de 8 m
B = 2.0   # demi-largeur  (m)  -> piste de 4 m
R = 1.2   # rayon des coins (m)


def sdf(x, y, a=A, b=B, r=R):
    """Distance signée à la ligne centrale : >0 à l'extérieur, <0 à l'intérieur."""
    qx = abs(x) - (a - r)
    qy = abs(y) - (b - r)
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    inside = min(max(qx, qy), 0.0)
    return outside + inside - r


def cross_track_error(x, y):
    """Erreur latérale absolue (m) entre le robot et la ligne centrale."""
    return abs(sdf(x, y))


def tangent(x, y, eps=1e-4):
    """Tangente unitaire (sens anti-horaire) au point le plus proche de la ligne."""
    nx = (sdf(x + eps, y) - sdf(x - eps, y)) / (2 * eps)
    ny = (sdf(x, y + eps) - sdf(x, y - eps)) / (2 * eps)
    n = math.hypot(nx, ny) or 1.0
    nx, ny = nx / n, ny / n
    return -ny, nx


def progress_angle(x, y):
    """Angle polaire (rad) utilisé pour compter les tours."""
    return math.atan2(y, x)

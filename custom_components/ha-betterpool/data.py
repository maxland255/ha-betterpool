"""Module de calculs physiques et chimiques purs pour BetterPool."""

import math


def calculate_pool_volume(length: float, width: float, average_depth: float) -> float:
    """Calculate pool volume."""
    if length <= 0 or width <= 0 or average_depth <= 0:
        return 0.0
    return round(length * width * average_depth, 2)


def calculate_filtration_time(temperature: float) -> float:
    """
    Calculate filtration time.

    Hybride method:
    - Minder than 10°C : Temperature / 3.0 (Minimum 2h)
    - Between 10 and 28°C : Temperature / 2.0
    - More than 28°C : 14.0 + (Temperature - 28.0) * 3.0
    """
    if temperature <= 0:
        return 0.0

    if temperature < 10:
        return max(2.0, round(temperature / 3.0, 2))

    if temperature >= 28:
        time = 14.0 + (temperature - 28.0) * 3.0
        return min(24.0, round(time, 1))

    return round(temperature / 2.0, 2)


def calculate_active_chlorine_percentage(ph: float, temperature: float) -> float:
    """
    Calcule le pourcentage de chlore actif (acide hypochloreux HClO) dans l'eau.

    Utilise l'équation de dissociation d'Henderson-Hasselbalch en ajustant le pKa
    du chlore selon la température (le chlore est plus sensible au pH à chaud).
    """
    if ph <= 0:
        return 0.0

    temp_kelvin = temperature + 273.15
    p_ka = 3000.0 / temp_kelvin - 10.0686 + 0.0253 * temp_kelvin

    try:
        ratio = 1.0 / (1.0 + math.pow(10, ph - p_ka))
        return round(ratio * 100.0, 1)
    except OverflowError:
        return 0.0


def get_temp_factor(temp: float) -> float:
    """Calcule le facteur de température (TF) pour le LSI."""
    if temp <= 0:
        return 0.0
    return round((math.log10(temp) * 1.1) - 0.5, 2) if temp > 0 else 0.0


def get_calcium_factor(th_ppm: float) -> float:
    """Calcule le facteur de Dureté Calcique (CF) pour le LSI à partir des ppm (ou mg/L)."""
    if th_ppm <= 0:
        return 0.0
    return round(math.log10(th_ppm) - 0.7, 2)


def get_alcalinity_factor(tac_ppm: float) -> float:
    """Calcule le facteur d'Alcalinité Totale (AF) pour le LSI à partir des ppm (ou mg/L)."""
    if tac_ppm <= 0:
        return 0.0
    return round(math.log10(tac_ppm), 2)


def calculate_corrected_tac(tac: float, stabilizer: float | None = None) -> float:
    """
    Calcule le TAC corrigé (Alcalinité Carbonate) en ppm.

    Soustrait l'alcalinité cyanurate (générée par le stabilisant) du TAC total.
    Formule : TAC_corrigé = TAC - (Stabilisant / 3)
    """
    if stabilizer is not None and stabilizer > 0:
        return max(0.0, round(tac - (stabilizer / 3.0), 1))
    return round(tac, 1)


def calculate_lsi(
    ph: float,
    temp: float,
    th: float,
    tac: float,
    pool_type: str = "chlore",
    stabilizer: float | None = None,
) -> float:
    """
    Calcule l'indice de saturation de Langelier (LSI).

    Un LSI entre -0.3 et +0.3 indique une eau parfaitement équilibrée.
    Un LSI < -0.3 indique une eau corrosive (attaque les joints, tuyaux, liners).
    Un LSI > +0.3 indique une eau incrustante (dépôt de calcaire).
    """
    effective_tac = calculate_corrected_tac(tac, stabilizer)

    tf = get_temp_factor(temp)
    cf = get_calcium_factor(th)
    af = get_alcalinity_factor(effective_tac)

    tds_factor = 12.2 if pool_type == "sel" else 12.1

    lsi = ph + tf + cf + af - tds_factor
    return round(lsi, 2)


def calculate_ph_dosage(
    current_ph: float, pool_volume: float, pool_type: str = "chlore"
) -> float:
    """
    Calcule la quantité de correcteur de pH nécessaire en kg.

    La cible de pH s'adapte automatiquement selon le type de traitement :
    - chlore : cible à 7.2
    - sel : cible à 7.4
    - brome : cible à 7.6

    Retourne :
    - Une valeur positive (ex: 1.2) : kg de pH Plus à ajouter.
    - Une valeur négative (ex: -0.8) : kg de pH Moins à ajouter.
    - 0.0 : aucun ajustement nécessaire.
    """
    if current_ph <= 0 or pool_volume <= 0:
        return 0.0

    # Détermination de la cible selon le traitement
    if pool_type == "sel":
        target_ph = 7.4
    elif pool_type == "brome":
        target_ph = 7.6
    else:  # chlore
        target_ph = 7.2

    # Zone de tolérance de +/- 0.2 autour de la cible pour éviter les micro-dosages
    if (target_ph - 0.2) <= current_ph <= (target_ph + 0.2):
        return 0.0

    delta_ph = target_ph - current_ph

    # Règle : 10g (0.01 kg) par m³ pour faire varier le pH de 0.1
    dosage = pool_volume * delta_ph * 0.1

    return round(dosage, 2)


def calculate_chlorine_status(orp: float | None) -> str:
    """
    Détermine le statut de désinfection de l'eau basé uniquement sur l'ORP.

    L'ORP (potentiel d'oxydoréduction) mesure directement l'efficacité réelle
    de désinfection en millivolts (mV).

    Retourne : 'low', 'good', 'high' ou 'unknown'
    """
    if orp is None:
        return "unknown"

    if orp < 650.0:
        return "low"
    elif 650.0 <= orp <= 780.0:
        return "good"
    else:
        return "high"

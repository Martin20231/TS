using UnityEngine;

/// <summary>
/// Lokale Zugsteuerung entlang der Z-Achse mit träger Beschleunigung und Bremsung.
/// Wird nur auf dem Besitzer-Client aktiv ausgeführt.
/// </summary>
public class TrainController : MonoBehaviour
{
    [Header("Geschwindigkeit")]
    [Tooltip("Maximale Vorwärtsgeschwindigkeit in m/s")]
    [SerializeField] private float maxSpeed = 20f;

    [Tooltip("Wie schnell der Zug beschleunigt (m/s²) – wirkt wie Masse")]
    [SerializeField] private float acceleration = 3f;

    [Tooltip("Wie stark gebremst wird (m/s²)")]
    [SerializeField] private float brakeForce = 6f;

    [Tooltip("Natürlicher Widerstand ohne Eingabe (m/s²)")]
    [SerializeField] private float drag = 1.5f;

    private float currentSpeed;

    /// <summary>Aktuelle Geschwindigkeit entlang der Z-Achse (nur lesen).</summary>
    public float CurrentSpeed => currentSpeed;

    /// <summary>
    /// Verarbeitet Tastatureingabe und bewegt den Zug nur auf der Z-Achse.
    /// Wird von TrainNetworkSync auf dem Besitzer-Client aufgerufen.
    /// </summary>
    public void ProcessMovement()
    {
        // W = beschleunigen, S = bremsen
        bool accelerate = Input.GetKey(KeyCode.W);
        bool brake = Input.GetKey(KeyCode.S);

        if (accelerate)
        {
            currentSpeed += acceleration * Time.deltaTime;
        }
        else if (brake)
        {
            // Bremsen reduziert die Geschwindigkeit in Richtung Null
            currentSpeed = Mathf.MoveTowards(currentSpeed, 0f, brakeForce * Time.deltaTime);
        }
        else
        {
            // Ohne Eingabe rollt der Zug langsam aus (Reibung)
            currentSpeed = Mathf.MoveTowards(currentSpeed, 0f, drag * Time.deltaTime);
        }

        currentSpeed = Mathf.Clamp(currentSpeed, 0f, maxSpeed);

        // Nur Z-Achse verändern – X und Y bleiben unverändert
        Vector3 position = transform.position;
        position.z += currentSpeed * Time.deltaTime;
        transform.position = position;
    }
}

using Unity.Netcode;
using UnityEngine;

/// <summary>
/// Synchronisiert Position und Rotation des Zuges über das Netzwerk.
/// Nur der Besitzer steuert; alle anderen Clients interpolieren zur empfangenen Position.
/// </summary>
[RequireComponent(typeof(NetworkObject))]
[RequireComponent(typeof(TrainController))]
public class TrainNetworkSync : NetworkBehaviour
{
    [Header("Netzwerk-Interpolation")]
    [Tooltip("Wie schnell Remote-Clients zur synchronisierten Position gleiten")]
    [SerializeField] private float interpolationSpeed = 12f;

    // Nur der Besitzer darf schreiben; alle Clients können lesen
    private readonly NetworkVariable<Vector3> networkPosition = new NetworkVariable<Vector3>(
        default,
        NetworkVariableReadPermission.Everyone,
        NetworkVariableWritePermission.Owner);

    private readonly NetworkVariable<Quaternion> networkRotation = new NetworkVariable<Quaternion>(
        Quaternion.identity,
        NetworkVariableReadPermission.Everyone,
        NetworkVariableWritePermission.Owner);

    private TrainController trainController;

    private void Awake()
    {
        trainController = GetComponent<TrainController>();
    }

    public override void OnNetworkSpawn()
    {
        base.OnNetworkSpawn();

        if (IsOwner)
        {
            // Besitzer: lokale Steuerung aktiv, initiale Werte ins Netzwerk schreiben
            trainController.enabled = true;
            networkPosition.Value = transform.position;
            networkRotation.Value = transform.rotation;
        }
        else
        {
            // Remote-Clients: keine Eingabe, nur empfangene Werte anwenden
            trainController.enabled = false;
            transform.SetPositionAndRotation(networkPosition.Value, networkRotation.Value);
        }
    }

    private void Update()
    {
        if (!IsSpawned)
        {
            return;
        }

        if (IsOwner)
        {
            // Besitzer bewegt den Zug lokal und sendet den Zustand
            trainController.ProcessMovement();
            networkPosition.Value = transform.position;
            networkRotation.Value = transform.rotation;
        }
        else
        {
            // Remote-Clients: weiche Interpolation zur Netzwerk-Position
            transform.position = Vector3.Lerp(
                transform.position,
                networkPosition.Value,
                Time.deltaTime * interpolationSpeed);

            transform.rotation = Quaternion.Slerp(
                transform.rotation,
                networkRotation.Value,
                Time.deltaTime * interpolationSpeed);
        }
    }
}

using Unity.Netcode;
using UnityEngine;

/// <summary>
/// Einfaches Startmenü per OnGUI zum schnellen Testen von Host und Client.
/// </summary>
public class NetworkBootstrap : MonoBehaviour
{
    private void OnGUI()
    {
        const int buttonWidth = 220;
        const int buttonHeight = 44;
        const int padding = 10;

        GUILayout.BeginArea(new Rect(padding, padding, buttonWidth + padding, 160));

        if (NetworkManager.Singleton == null)
        {
            GUILayout.Label("NetworkManager fehlt in der Szene!");
            GUILayout.EndArea();
            return;
        }

        bool isConnected = NetworkManager.Singleton.IsClient || NetworkManager.Singleton.IsServer;

        if (!isConnected)
        {
            if (GUILayout.Button("Als Host starten", GUILayout.Width(buttonWidth), GUILayout.Height(buttonHeight)))
            {
                // Host = Server + Client in einer Instanz
                NetworkManager.Singleton.StartHost();
            }

            if (GUILayout.Button("Als Client beitreten", GUILayout.Width(buttonWidth), GUILayout.Height(buttonHeight)))
            {
                NetworkManager.Singleton.StartClient();
            }
        }
        else
        {
            string role = NetworkManager.Singleton.IsHost ? "Host" : "Client";
            GUILayout.Label($"Verbunden als: {role}");
        }

        GUILayout.EndArea();
    }
}

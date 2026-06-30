/**
 * TS Multiplayer Radar – Session, Konvoi, Leitstand, Ghost-Spuren.
 * Erwartet globale Karten-Variablen aus index.html (map, localPlayerName, socket, …).
 */
(function () {
    "use strict";

    const STORAGE_KEY = "ts-mp-session";
    const ghostLayers = new Map();
    let convoyAlertKm = 2.0;
    let sessionRole = "driver";
    let sessionData = null;

    function $(id) {
        return document.getElementById(id);
    }

    function loadStoredSession() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
        } catch {
            return null;
        }
    }

    function saveSession(sessionId, role) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessionId, role }));
        window.MP_SESSION_ID = sessionId || "";
        sessionRole = role || "driver";
    }

    function formatDist(km) {
        if (typeof window.formatDistance === "function") {
            return window.formatDistance(km);
        }
        return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
    }

    function setTab(name) {
        document.querySelectorAll(".mp-tab").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.tab === name);
        });
        document.querySelectorAll(".mp-tab-panel").forEach((panel) => {
            panel.classList.toggle("hidden", panel.dataset.tab !== name);
        });
        localStorage.setItem("ts-mp-tab", name);
    }

    function renderConvoyHtml(convoy) {
        if (!convoy.length) {
            return "<p class='status'>Keine anderen Züge in der Nähe.</p>";
        }
        return convoy.map((c) => {
            const dir = c.same_direction ? "gleiche Richtung" : "andere Richtung";
            const alert = c.distance_km <= convoyAlertKm ? " mp-convoy-near" : "";
            return `<div class="mp-convoy-row${alert}">
                <strong>${c.player}</strong> · ${formatDist(c.distance_km)}
                · ${Math.round(c.speed_kph)} km/h · ${dir}
                ${c.loco ? ` · ${c.loco}` : ""}
            </div>`;
        }).join("");
    }

    function updateConvoyDisplays(convoy) {
        const html = renderConvoyHtml(convoy);
        for (const id of ["mp-convoy", "mp-convoy-menu"]) {
            const el = $(id);
            if (el) el.innerHTML = html;
        }

        const status = $("mp-convoy-status");
        if (status) {
            const nearest = convoy[0];
            if (nearest) {
                const near = nearest.distance_km <= convoyAlertKm ? " ⚠" : "";
                status.textContent = `Nächster Zug: ${nearest.player} · ${formatDist(nearest.distance_km)}${near}`;
            } else if (sessionData?.members) {
                const others = sessionData.members.filter((m) => m.player !== playerName() && m.active);
                status.textContent = others.length
                    ? `${others.length} Zug/Züge in Session aktiv`
                    : "Warte auf andere Spieler …";
            } else {
                status.textContent = "";
            }
        }
    }

    function appendInboxMessage(msg) {
        const box = $("mp-inbox");
        if (!box) return;
        const target = msg.target ? ` → ${msg.target}` : " (alle)";
        const row = document.createElement("div");
        row.className = "mp-msg";
        row.textContent = `${msg.sender}${target}: ${msg.text}`;
        box.appendChild(row);
        while (box.children.length > 20) {
            box.removeChild(box.firstChild);
        }
        const inboxBox = $("mp-inbox-box");
        if (inboxBox && !inboxBox.open) {
            inboxBox.open = true;
        }
    }

    function renderInboxFromSession() {
        const box = $("mp-inbox");
        if (!box) return;
        const messages = sessionData?.messages || [];
        const relevant = messages.filter((msg) => !msg.target || msg.target === playerName());
        box.innerHTML = relevant.slice(-12).map((msg) => {
            const target = msg.target ? ` → ${msg.target}` : " (alle)";
            return `<div class="mp-msg"><strong>${msg.sender}</strong>${target}: ${msg.text}</div>`;
        }).join("") || "<p class='status'>Noch keine Nachrichten</p>";
    }

    function showToast(text) {
        const el = $("mp-toast");
        if (!el) return;
        el.textContent = text;
        el.classList.add("visible");
        clearTimeout(showToast._t);
        showToast._t = setTimeout(() => el.classList.remove("visible"), 5000);
    }

    function renderLobby() {
        const box = $("mp-lobby-body");
        if (!box) return;

        if (!window.MP_SESSION_ID) {
            box.innerHTML = `
                <p class="status">Keine Session aktiv. Erstelle eine Fahrt oder tritt einer bei.</p>
                <label class="mp-field">Name der Fahrt
                    <input type="text" id="mp-session-name" value="Adlershof Abend" />
                </label>
                <button type="button" class="ctrl-btn" id="mp-btn-create">Session erstellen</button>
                <hr class="mp-hr" />
                <label class="mp-field">Session-Code
                    <input type="text" id="mp-session-code" placeholder="z.B. aus Einladungslink" />
                </label>
                <label class="mp-field">Rolle
                    <select id="mp-join-role">
                        <option value="driver">Lokführer</option>
                        <option value="dispatch">Leitstand</option>
                    </select>
                </label>
                <button type="button" class="ctrl-btn" id="mp-btn-join">Beitreten</button>
            `;
            $("mp-btn-create")?.addEventListener("click", createSession);
            $("mp-btn-join")?.addEventListener("click", () => joinSession($("mp-session-code").value));
            return;
        }

        const members = sessionData?.members || [];
        const ready = sessionData?.ready_count || 0;
        const joinUrl = `${location.origin}/?session=${window.MP_SESSION_ID}`;

        let html = `
            <p class="status"><strong>${sessionData?.name || "Fahrt"}</strong></p>
            <p class="status">Code: <code>${window.MP_SESSION_ID}</code></p>
            <input class="mp-copy" readonly value="${joinUrl}" onclick="this.select()" />
            <p class="status">${ready}/${members.length} bereit · Rolle: ${sessionRole}</p>
            <div class="mp-member-list">
        `;

        for (const m of members) {
            const badge = m.active
                ? '<span class="badge badge-live">Live</span>'
                : '<span class="badge badge-off">Offline</span>';
            const roleLabel = m.role === "dispatch" ? "Leitstand" : "Lokführer";
            html += `<div class="mp-member-row">
                ${badge} <strong>${m.player}</strong>
                ${m.player === playerName() ? "(du)" : ""}
                · ${roleLabel}
                ${m.loco ? `· ${m.loco}` : ""}
                ${m.active ? `· ${Math.round(m.speed_kph)} km/h` : ""}
            </div>`;
        }

        html += `</div>
            <div class="mp-actions">
                <button type="button" class="ctrl-btn" id="mp-btn-ready">Bereit</button>
                <button type="button" class="ctrl-btn" id="mp-btn-leave">Verlassen</button>
            </div>
            <details class="help-box"><summary>Fahrstatistik</summary>
            <div id="mp-scores"></div></details>`;

        box.innerHTML = html;

        const scores = $("mp-scores");
        if (scores) {
            scores.innerHTML = members.map((m) => `
                <div class="mp-score-row">
                    <strong>${m.player}</strong>:
                    ${m.stats.distance_km} km · max ${m.stats.max_speed_kph} km/h
                    · ${m.stats.stops} Halte · ${m.stats.driving_minutes} min Fahrt
                </div>
            `).join("") || "<p class='status'>Noch keine Daten</p>";
        }

        $("mp-btn-ready")?.addEventListener("click", toggleReady);
        $("mp-btn-leave")?.addEventListener("click", leaveSession);
    }

    function renderDispatch() {
        const box = $("mp-dispatch-body");
        if (!box) return;

        if (!window.MP_SESSION_ID) {
            box.innerHTML = "<p class='status'>Zuerst einer Session beitreten (Tab Session).</p>";
            return;
        }

        const messages = sessionData?.messages || [];
        const members = (sessionData?.members || []).filter((m) => m.player !== playerName());

        let html = `
            <p class="status">Nachrichten an Lokführer in deiner Session.</p>
            <div id="mp-convoy" class="mp-convoy"></div>
            <div id="mp-msg-list" class="mp-msg-list">
        `;

        for (const msg of messages.slice(-12)) {
            const target = msg.target ? ` → ${msg.target}` : " (alle)";
            html += `<div class="mp-msg"><strong>${msg.sender}</strong>${target}: ${msg.text}</div>`;
        }

        html += `</div>
            <label class="mp-field">An
                <select id="mp-msg-target">
                    <option value="">Alle Fahrer</option>
                    ${members.map((m) => `<option value="${m.player}">${m.player}</option>`).join("")}
                </select>
            </label>
            <label class="mp-field">Nachricht
                <input type="text" id="mp-msg-text" placeholder="z.B. In Adlershof warten" />
            </label>
            <button type="button" class="ctrl-btn" id="mp-btn-send">Senden</button>
            <div class="mp-quick">
                <button type="button" class="ctrl-btn mp-quick-btn" data-text="Halten und warten.">Halten</button>
                <button type="button" class="ctrl-btn mp-quick-btn" data-text="Weiterfahrt frei.">Frei</button>
                <button type="button" class="ctrl-btn mp-quick-btn" data-text="Rangieren langsam.">Rangieren</button>
            </div>`;

        box.innerHTML = html;

        $("mp-btn-send")?.addEventListener("click", sendDispatch);
        $("mp-msg-text")?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") sendDispatch();
        });
        document.querySelectorAll(".mp-quick-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                $("mp-msg-text").value = btn.dataset.text || "";
                sendDispatch();
            });
        });

        updateConvoyPanel();
    }

    async function createSession() {
        const name = ($("mp-session-name")?.value || "Fahrt").trim();
        try {
            const res = await fetch("/api/sessions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name }),
            });
            const data = await res.json();
            if (!data.ok) throw new Error(data.error || "Fehler");
            await joinSession(data.session_id, sessionRole);
            showToast(`Session „${name}" erstellt`);
        } catch (err) {
            showToast(`Fehler: ${err.message}`);
        }
    }

    function playerName() {
        if (typeof localPlayerName !== "undefined" && localPlayerName) {
            return localPlayerName;
        }
        return $("cfg-player")?.textContent?.trim() || "MeinZug";
    }

    async function joinSession(sessionId, role) {
        const id = (sessionId || "").trim();
        if (!id) {
            showToast("Session-Code fehlt");
            return;
        }
        const joinRole = role || $("mp-join-role")?.value || "driver";
        const name = playerName();
        try {
            const res = await fetch(`/api/sessions/${encodeURIComponent(id)}/join`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    player: name,
                    role: joinRole,
                }),
            });
            const data = await res.json();
            if (!data.ok) throw new Error(data.error || "Session nicht gefunden");
            saveSession(id, joinRole);
            sessionData = data;
            subscribeSession();
            renderLobby();
            renderDispatch();
            renderInboxFromSession();
            showToast(`Session ${id} beigetreten`);
            const status = $("mp-session-status");
            if (status) {
                status.innerHTML = `Session: ${data.name} (<code>${id}</code>) — <code>session_id</code> in config.json`;
            }
        } catch (err) {
            showToast(`Beitritt fehlgeschlagen: ${err.message}`);
        }
    }

    async function toggleReady() {
        if (!window.MP_SESSION_ID) return;
        const member = sessionData?.members?.find((m) => m.player === playerName());
        const ready = !(member?.ready);
        await fetch(`/api/sessions/${encodeURIComponent(window.MP_SESSION_ID)}/ready`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ player: playerName(), ready }),
        });
    }

    function leaveSession() {
        saveSession("", "driver");
        sessionData = null;
        clearGhostTrails();
        renderLobby();
        renderDispatch();
        const status = $("mp-session-status");
        if (status) status.textContent = "Keine Session";
        showToast("Session verlassen");
    }

    async function sendDispatch() {
        if (!window.MP_SESSION_ID) return;
        const text = ($("mp-msg-text")?.value || "").trim();
        const target = $("mp-msg-target")?.value || null;
        if (!text) return;
        try {
            await fetch(`/api/sessions/${encodeURIComponent(window.MP_SESSION_ID)}/messages`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sender: playerName(),
                    text,
                    target: target || undefined,
                }),
            });
            $("mp-msg-text").value = "";
        } catch (err) {
            showToast(`Senden fehlgeschlagen: ${err.message}`);
        }
    }

    function subscribeSession() {
        if (!window.socket || !window.MP_SESSION_ID) return;
        window.socket.emit("join_session", { session_id: window.MP_SESSION_ID });
    }

    function clearGhostTrails() {
        if (typeof map === "undefined") return;
        for (const layer of ghostLayers.values()) {
            map.removeLayer(layer);
        }
        ghostLayers.clear();
    }

    function updateGhostTrails(trails) {
        if (typeof map === "undefined" || !trails) return;

        const activePlayers = new Set(Object.keys(trails));
        for (const player of ghostLayers.keys()) {
            if (!activePlayers.has(player)) {
                map.removeLayer(ghostLayers.get(player));
                ghostLayers.delete(player);
            }
        }

        for (const [player, points] of Object.entries(trails)) {
            if (player === playerName() || !points?.length) continue;
            const latlngs = points.map((p) => [p.lat, p.lon]);
            const color = typeof getPlayerColor === "function" ? getPlayerColor(player) : "#888";
            let line = ghostLayers.get(player);
            if (!line) {
                line = L.polyline(latlngs, {
                    color,
                    weight: 3,
                    opacity: 0.35,
                    dashArray: "6 8",
                    interactive: false,
                }).addTo(map);
                ghostLayers.set(player, line);
            } else {
                line.setLatLngs(latlngs);
            }
        }
    }

    async function updateConvoyPanel() {
        if (!window.MP_SESSION_ID) {
            updateConvoyDisplays([]);
            return;
        }
        try {
            const res = await fetch(
                `/api/sessions/${encodeURIComponent(window.MP_SESSION_ID)}/convoy?player=${encodeURIComponent(playerName())}`
            );
            const data = await res.json();
            updateConvoyDisplays(data.convoy || []);
        } catch {
            updateConvoyDisplays([]);
        }
    }

    function onSessionUpdate(data) {
        sessionData = data;
        updateGhostTrails(data.trails);
        renderInboxFromSession();
        renderLobby();
        if (document.querySelector('.mp-tab.active')?.dataset.tab === "dispatch") {
            renderDispatch();
        } else {
            updateConvoyPanel();
        }
    }

    function hookSocket() {
        if (!window.socket) {
            setTimeout(hookSocket, 500);
            return;
        }
        window.socket.on("session_update", onSessionUpdate);
        window.socket.on("dispatch_message", (msg) => {
            if (msg.session_id !== window.MP_SESSION_ID) return;
            if (msg.target && msg.target !== playerName()) return;
            appendInboxMessage(msg);
        });
        subscribeSession();
    }

    async function init() {
        const params = new URLSearchParams(location.search);
        const urlSession = params.get("session");
        const stored = loadStoredSession();

        document.querySelectorAll(".mp-tab").forEach((btn) => {
            btn.addEventListener("click", () => setTab(btn.dataset.tab));
        });

        const savedTab = localStorage.getItem("ts-mp-tab") || "map";
        setTab(savedTab);

        $("mp-btn-overlay")?.addEventListener("click", () => {
            const url = `/overlay?player=${encodeURIComponent(playerName())}&session=${encodeURIComponent(window.MP_SESSION_ID || "")}`;
            window.open(url, "ts-overlay", "width=420,height=280");
        });

        await new Promise((r) => setTimeout(r, 400));

        if (urlSession) {
            await joinSession(urlSession, stored?.role || "driver");
        } else if (stored?.sessionId) {
            saveSession(stored.sessionId, stored.role || "driver");
            await joinSession(stored.sessionId, stored.role || "driver");
        } else {
            window.MP_SESSION_ID = "";
            renderLobby();
            renderDispatch();
        }

        hookSocket();
        setInterval(() => {
            if (window.MP_SESSION_ID) updateConvoyPanel();
        }, 4000);
    }

    window.mpFilterPositions = function (players) {
        if (!window.MP_SESSION_ID) return players;
        return players.filter(
            (p) => !p.session_id || p.session_id === window.MP_SESSION_ID
        );
    };

    window.MP = {
        init,
        setConvoyAlertKm(km) {
            convoyAlertKm = km;
        },
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            window.MP.init();
        });
    } else {
        window.MP.init();
    }
})();

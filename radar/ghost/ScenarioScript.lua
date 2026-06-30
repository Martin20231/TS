------------------------------------------------
-- ScenarioScript.lua – Multiplayer Ghost (Silent)
-- KEINE Menü-Fenster (TS stapelt jeden Alert beim Klick)
-- Bridge + Karte/Overlay zeigen Eric · optional 1x Nähe-Warnung
------------------------------------------------

FALSE = 0
TRUE = 1

CONDITION_NOT_YET_MET = 0
CONDITION_SUCCEEDED = 1
CONDITION_FAILED = 2

MT_ALERT = 1

POLL_SECONDS = 1.0
GHOST_OBJECT = "GHOST_MP"
NEAR_KM = 2.0

GHOST_DIST_CONTROLS = {
	"PassLightValue", "InstrumentLightning", "ConsoleLightning",
	"MirrorLeft", "MirrorRight", "SunShade",
}
GHOST_BEARING_CONTROLS = {
	"CablightValue", "Cablight", "WiperInterval", "HeadlightsMode", "Marker",
}
GHOST_ACTIVE_CONTROLS = {
	"Vigilance", "WiperControl", "SunShade",
}

gGhostHasObject = FALSE
gGhostNearWarned = FALSE

function GhostReadControl(names)
	local i, name, v
	for i, name in ipairs(names) do
		v = SysCall("PlayerEngine:GetControlValue", name, 0)
		if v ~= nil and v >= 0.0 then
			return v, name
		end
	end
	return 0.0, nil
end

function GhostReadBus()
	local dist_v = GhostReadControl(GHOST_DIST_CONTROLS)
	local bear_v = GhostReadControl(GHOST_BEARING_CONTROLS)
	local act_v = GhostReadControl(GHOST_ACTIVE_CONTROLS)
	return dist_v, bear_v, act_v
end

function GhostTryMoveObject(dist_km, bearing_deg)
	if gGhostHasObject == FALSE then
		return
	end
	local px, py, pz = SysCall("PlayerEngine:getNearPosition")
	if px == nil then
		return
	end
	local dist_m = dist_km * 1000.0
	if dist_m > 8000.0 then
		dist_m = 8000.0
	end
	local rad = math.rad(bearing_deg)
	local gx = px + dist_m * math.sin(rad)
	local gz = pz + dist_m * math.cos(rad)
	SysCall(GHOST_OBJECT .. ":setNearPosition", gx, py, gz)
end

function GhostProbeObject()
	local ok = pcall(function()
		return SysCall(GHOST_OBJECT .. ":getNearPosition")
	end)
	if ok then
		gGhostHasObject = TRUE
	else
		gGhostHasObject = FALSE
	end
end

function OnEvent_GhostStart()
	GhostProbeObject()
	SysCall("ScenarioManager:TriggerDeferredEvent", "GhostPoll", POLL_SECONDS)
	return TRUE
end

function OnEvent_GhostPoll()
	local dist_v, bear_v, act_v = GhostReadBus()

	if act_v >= 0.45 then
		local dist_km = dist_v * 50.0
		local bearing = bear_v * 360.0
		GhostTryMoveObject(dist_km, bearing)

		if dist_km < NEAR_KM and gGhostNearWarned == FALSE then
			SysCall(
				"ScenarioManager:ShowMessage",
				"Konvoi",
				"Anderer Spieler unter 2 km!",
				MT_ALERT
			)
			gGhostNearWarned = TRUE
		elseif dist_km >= (NEAR_KM + 0.5) then
			gGhostNearWarned = FALSE
		end
	end

	SysCall("ScenarioManager:TriggerDeferredEvent", "GhostPoll", POLL_SECONDS)
	return TRUE
end

-- Alte Fahrplan-Events (GhostMenu, GhostMenuHtml, Stellwerk …) → nichts tun
function OnEvent_GhostMenu()
	return TRUE
end

function OnEvent_GhostMenuHtml()
	return TRUE
end

function OnEvent_StellwerkStart()
	return TRUE
end

function OnEventGhostMenu()
	return TRUE
end

function OnEventGhostMenuHtml()
	return TRUE
end

function InitScenario()
	return TRUE
end

function OnEvent(event)
	local handler = _G["OnEvent_" .. event]
	if handler == nil then
		handler = _G["OnEvent" .. event]
	end
	if handler ~= nil then
		return handler()
	end
	return FALSE
end

function TestCondition(condition)
	return CONDITION_NOT_YET_MET
end

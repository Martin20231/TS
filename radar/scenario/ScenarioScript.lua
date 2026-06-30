------------------------------------------------
-- ScenarioScript.lua – TS Multiplayer-Radar (Konvoi im Menü)
-- Fahrplan-Start-Event: MPRadarStart
-- Tracker sendet Konvoi-Daten über RailDriver-Bus (mp_bus_control).
-- WICHTIG: Keine Meldungen im Poll-Loop – nur im Menü anzeigen.
------------------------------------------------

FALSE = 0
TRUE = 1

CONDITION_NOT_YET_MET = 0
CONDITION_SUCCEEDED = 1
CONDITION_FAILED = 2

MSG_BOTTOM = 4
MSG_RIGHT = 32
MSG_REG = 1

gMPBooted = FALSE
KEEPALIVE_SECONDS = 0.15
gConvoy = {}

MP_BUS_CONTROLS = {
	"PassLightValue",
	"CablightValue",
	"SunShade",
	"InstrumentLightning",
	"ConsoleLightning",
	"MirrorLeft",
	"MirrorRight",
	"WiperControl",
	"HeadlightsMode",
}

function MP_ClearConvoy()
	gConvoy = {}
end

function MP_FormatDistance(km)
	if km < 1.0 then
		return math.floor(km * 1000 + 0.5) .. " m"
	end
	return string.format("%.1f km", km)
end

function MP_ReadBusCommand()
	local i, name, v, code, slot, dist_tenths
	for i, name in ipairs(MP_BUS_CONTROLS) do
		v = SysCall("PlayerEngine:GetControlValue", name, 0)
		if v ~= nil and v >= 0.08 then
			code = math.floor(v * 1000 + 0.5)
			if code <= 0 then
				return 0, name
			end
			slot = math.floor(code / 100)
			dist_tenths = code - slot * 100
			if slot >= 0 and slot <= 9 and dist_tenths >= 0 and dist_tenths <= 99 then
				return code, name
			end
		end
	end
	return 0, nil
end

function MP_ClearBusControl(name)
	if name ~= nil then
		SysCall("PlayerEngine:SetControlValue", name, 0, 0)
	end
end

function MP_ApplyBusCommand(code)
	local slot, dist_tenths, dist_km
	if code <= 0 then
		return
	end
	slot = math.floor(code / 100)
	dist_tenths = code - slot * 100
	dist_km = dist_tenths / 10.0

	if slot == 0 then
		MP_ClearConvoy()
		return
	end

	gConvoy[slot] = {
		slot = slot,
		distance_km = dist_km,
	}
end

function MP_BuildConvoyText()
	local lines = {}
	local i, entry, count

	count = 0
	for i = 1, 9 do
		entry = gConvoy[i]
		if entry ~= nil then
			count = count + 1
			if count == 1 then
				table.insert(lines, "Naechster Zug: " .. MP_FormatDistance(entry.distance_km))
			else
				table.insert(
					lines,
					"Zug " .. i .. ": " .. MP_FormatDistance(entry.distance_km)
				)
			end
		end
	end

	if count == 0 then
		return "Keine anderen Zuege in der Naehe.\n\nTracker + Session aktiv?"
	end

	table.insert(lines, "")
	table.insert(lines, "Namen siehe Radar-Karte im Browser.")
	return table.concat(lines, "\n")
end

function MP_ShowInfo(title, text)
	SysCall(
		"ScenarioManager:ShowInfoMessageExt",
		title,
		text,
		10.0,
		MSG_BOTTOM + MSG_RIGHT,
		MSG_REG,
		FALSE
	)
end

function MP_OpenMenu()
	SysCall(
		"ScenarioManager:ShowAlertMessageExt",
		"Konvoi",
		"Entfernungen anzeigen",
		600.0,
		"MP_SHOW"
	)
	SysCall(
		"ScenarioManager:ShowAlertMessageExt",
		"Radar",
		"Menue aktualisieren",
		600.0,
		"MP_MENU"
	)
end

function MP_Boot()
	if gMPBooted == TRUE then
		return
	end
	gMPBooted = TRUE
	MP_ClearConvoy()
	SysCall("ScenarioManager:BeginConditionCheck", "MPRadarBus")
	SysCall("ScenarioManager:TriggerDeferredEvent", "MPRadarKeepAlive", KEEPALIVE_SECONDS)
end

function OnEvent_MPRadarStart()
	MP_Boot()
	MP_OpenMenu()
	MP_ShowInfo(
		"Multiplayer-Radar",
		"Konvoi-Menue oben rechts.\nKeine Dauer-Meldungen mehr."
	)
	return TRUE
end

function OnEvent_MPRadarKeepAlive()
	local code, busName = MP_ReadBusCommand()
	if code > 0 then
		MP_ApplyBusCommand(code)
		MP_ClearBusControl(busName)
	end
	SysCall("ScenarioManager:BeginConditionCheck", "MPRadarBus")
	SysCall("ScenarioManager:TriggerDeferredEvent", "MPRadarKeepAlive", KEEPALIVE_SECONDS)
	return TRUE
end

function OnEvent_MP_SHOW()
	MP_ShowInfo("Konvoi", MP_BuildConvoyText())
	MP_OpenMenu()
	return TRUE
end

function OnEvent_MP_MENU()
	MP_OpenMenu()
	return TRUE
end

function OnEvent(event)
	local handler = _G["OnEvent_" .. event]
	if handler ~= nil then
		return handler()
	end
	return FALSE
end

function TestCondition(condition)
	if condition == "MPRadarBus" then
		MP_Boot()
		local code, busName = MP_ReadBusCommand()
		if code > 0 then
			MP_ApplyBusCommand(code)
			MP_ClearBusControl(busName)
			SysCall("ScenarioManager:BeginConditionCheck", "MPRadarBus")
			return CONDITION_SUCCEEDED
		end
		return CONDITION_NOT_YET_MET
	end
	return CONDITION_NOT_YET_MET
end

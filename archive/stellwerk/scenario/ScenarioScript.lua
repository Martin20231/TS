------------------------------------------------
-- ScenarioScript.lua – Stellwerk Adlershof
-- Signal im Editor: Object Name = SW_S1 (exakt!)
-- Start-Event im Fahrplan: StellwerkStart
------------------------------------------------

FALSE = 0
TRUE = 1

CONDITION_NOT_YET_MET = 0
CONDITION_SUCCEEDED = 1
CONDITION_FAILED = 2

MSG_TOP = 1
MSG_BOTTOM = 4
MSG_RIGHT = 32
MSG_VCENTRE = 2
MSG_CENTRE = 16
MSG_SMALL = 0
MSG_REG = 1
MT_ALERT = 1

gStellwerkBooted = FALSE
gHornLast = 0.0
gHornPulses = 0
gHornQuiet = 0
HORN_QUIET_TICKS = 8
HORN_THRESHOLD = 0.12
KEEPALIVE_SECONDS = 0.08
gMenuRefreshTick = 0
MENU_REFRESH_TICKS = 24

-- Fuer HTML-Dateien im Szenario-Ordner (Berlin JWD / virtualTracks)
SCENARIO_HTML_ID = "16133f2c-3362-474b-a3cb-266914695836"

ANIM_HP0 = 0
ANIM_HP1 = 1
ANIM_SH1 = 4

SIGNAL_BLOCKED = 12
SIGNAL_CLEARED = 13

STELLWERK_BUS_PAIRS = {
	{ "Sand", "Wipers" },
	{ "Sand", "Wiper" },
	{ "Sandstreuer", "Wipers" },
	{ "Wipers", "CabLight" },
	{ "Wiper", "CabLight" },
	{ "CabLight", "Marker" },
}

STELLWERK_SINGLE_CONTROLS = {
	"CablightValue",
	"Cablight",
	"SunShade",
	"InstrumentLightning",
	"ConsoleLightning",
	"PassLightValue",
	"MirrorLeft",
	"MirrorRight",
	"WiperControl",
	"Wipers",
	"Wiper",
	"Sandstreuer",
	"Sand",
	"VirtualThrottle",
	"Regulator",
	"TrainBrake",
	"TrainBrakeControl",
}

function StellwerkReadBusCommand()
	local i, pair, sig_name, asp_name, sig_v, asp_v, sig_idx, asp_code
	for i, pair in ipairs(STELLWERK_BUS_PAIRS) do
		sig_name = pair[1]
		asp_name = pair[2]
		sig_v = SysCall("PlayerEngine:GetControlValue", sig_name, 0)
		asp_v = SysCall("PlayerEngine:GetControlValue", asp_name, 0)
		if sig_v >= 0.04 and asp_v >= 0.04 then
			sig_idx = math.floor(sig_v * 10 + 0.5)
			asp_code = math.floor(asp_v * 10 + 0.5)
			if asp_code > 3 then
				asp_code = math.floor(asp_v + 0.5)
			end
			if sig_idx >= 1 and asp_code >= 1 then
				return sig_idx * 10 + asp_code, sig_name, asp_name
			end
		end
	end

	for i, name in ipairs(STELLWERK_SINGLE_CONTROLS) do
		sig_v = SysCall("PlayerEngine:GetControlValue", name, 0)
		if sig_v >= 0.08 then
			sig_idx = math.floor(sig_v * 100 + 0.5)
			if sig_idx >= 11 and sig_idx <= 93 then
				return sig_idx, name, name
			end
		end
	end

	return 0, nil, nil
end

function StellwerkReadHornValue()
	local names, i, name, v, best
	names = { "Horn", "HornControl" }
	best = 0.0
	for i, name in ipairs(names) do
		v = SysCall("PlayerEngine:GetControlValue", name, 0)
		if v ~= nil and v > best then
			best = v
		end
	end
	return best
end

function StellwerkApplyHornPulses(pulses)
	local aspect = ANIM_HP0
	local aspect_name = "Hp0 Halt"

	if pulses == 2 then
		aspect = ANIM_SH1
		aspect_name = "Sh1 Rangier"
	elseif pulses >= 3 then
		aspect = ANIM_HP1
		aspect_name = "Hp1 Frei"
	end

	if SIGNALS[1] == nil then
		return
	end

	gActiveSignalIndex = 1
	StellwerkSetAspect(1, aspect)
	StellwerkShowRadarStatus(
		SIGNALS[1].label .. ": " .. aspect_name .. " (" .. pulses .. "x Hupe)"
	)
end

function StellwerkPollHornInput()
	local horn, rising

	horn = StellwerkReadHornValue()
	rising = FALSE
	if gHornLast < HORN_THRESHOLD and horn >= HORN_THRESHOLD then
		rising = TRUE
	end

	if rising == TRUE then
		gHornPulses = gHornPulses + 1
		gHornQuiet = 0
	elseif horn < HORN_THRESHOLD then
		gHornQuiet = gHornQuiet + 1
	end

	gHornLast = horn

	if gHornPulses > 0 and gHornQuiet >= HORN_QUIET_TICKS then
		StellwerkApplyHornPulses(gHornPulses)
		gHornPulses = 0
		gHornQuiet = 0
	end
end

function StellwerkClearBusControls(signalName, aspectName)
	if signalName ~= nil then
		SysCall("PlayerEngine:SetControlValue", signalName, 0, 0)
	end
	if aspectName ~= nil and aspectName ~= signalName then
		SysCall("PlayerEngine:SetControlValue", aspectName, 0, 0)
	end
end

function StellwerkBoot()
	if gStellwerkBooted == TRUE then
		return
	end
	gStellwerkBooted = TRUE
	SysCall("ScenarioManager:BeginConditionCheck", "StellwerkBus")
	SysCall("ScenarioManager:TriggerDeferredEvent", "StellwerkKeepAlive", KEEPALIVE_SECONDS)
end

-- id = Object Name im Editor (SW_S1), fallback = Signal-ID Zahl (566)
SIGNALS = {
	{ id = "SW_S1", name = "SW_S1", route_id = "566", label = "Test-Signal Adlershof" },
}

gActiveSignalIndex = 1

function StellwerkSignalIds(sig)
	local ids = {}
	local seen = {}
	local function add(id)
		if id ~= nil and id ~= "" and seen[id] == nil then
			seen[id] = TRUE
			table.insert(ids, id)
		end
	end
	add(sig.id)
	add(sig.name)
	add(sig.route_id)
	return ids
end

function StellwerkInvokeId(id, method, arg)
	if arg == nil then
		SysCall(id .. ":" .. method)
	else
		SysCall(id .. ":" .. method, arg)
	end
end

function StellwerkReadAspectCode(id)
	local value = SysCall(id .. ":GetDispatcherAspect")
	if value == nil then
		return nil
	end
	return value
end

function StellwerkFindReachableId(sig)
	local ids = StellwerkSignalIds(sig)
	local i, id, probe
	for i, id in ipairs(ids) do
		probe = StellwerkReadAspectCode(id)
		if probe ~= nil then
			return id, probe
		end
	end
	return nil, -1
end

function StellwerkTryWakeSignal(sig)
	local ids = StellwerkSignalIds(sig)
	local i, id
	for i, id in ipairs(ids) do
		SysCall(id .. ":SetDispatcherMode", 1)
	end
end

function StellwerkInvokeSignal(sig, method, arg)
	local ids = StellwerkSignalIds(sig)
	local i, id
	for i, id in ipairs(ids) do
		StellwerkInvokeId(id, method, arg)
	end
end

function StellwerkSetAspect(signalIndex, aspect)
	local sig = SIGNALS[signalIndex]
	if sig == nil then
		return
	end

	StellwerkInvokeSignal(sig, "SetDispatcherMode", 1)

	if aspect == ANIM_HP0 then
		StellwerkInvokeSignal(sig, "DispatcherSetAspect", ANIM_HP0)
		StellwerkInvokeSignal(sig, "SetState", SIGNAL_BLOCKED)
	elseif aspect == ANIM_HP1 then
		StellwerkInvokeSignal(sig, "DispatcherSetAspect", ANIM_HP1)
		StellwerkInvokeSignal(sig, "SetState", SIGNAL_CLEARED)
	else
		StellwerkInvokeSignal(sig, "DispatcherSetAspect", ANIM_SH1)
	end
end

function StellwerkAllManual()
	local i
	for i = 1, table.getn(SIGNALS) do
		StellwerkSetAspect(i, ANIM_HP0)
	end
end

function StellwerkShowStatus(title, text, position)
	local pos = position
	if pos == nil then
		pos = MSG_BOTTOM + MSG_RIGHT
	end
	SysCall(
		"ScenarioManager:ShowInfoMessageExt",
		title,
		text,
		8.0,
		pos,
		MSG_REG,
		FALSE
	)
end

function StellwerkShowClickAlert(title, text, eventName, seconds)
	local duration = seconds
	if duration == nil then
		duration = 600.0
	end
	SysCall(
		"ScenarioManager:ShowAlertMessageExt",
		title,
		text,
		duration,
		eventName
	)
end

function StellwerkShowRadarStatus(text)
	SysCall("ScenarioManager:ShowMessage", "Radar", text, MT_ALERT)
	SysCall(
		"ScenarioManager:ShowAlertMessageExt",
		"Radar",
		text,
		15.0,
		"SW_MENU"
	)
end

function StellwerkOpenMenu()
	StellwerkShowClickAlert("Hp0 Halt", "Klicken -> Signal ROT", "SW_A_HP0", 600.0)
	StellwerkShowClickAlert("Sh1 Rangier", "Klicken -> Signal GELB", "SW_A_SH1", 600.0)
	StellwerkShowClickAlert("Hp1 Frei", "Klicken -> Signal FAHRT", "SW_A_HP1", 600.0)
end

function StellwerkApplyAspect(aspect, aspectName)
	local sig = SIGNALS[gActiveSignalIndex]
	local reachableId, aspectCode = StellwerkFindReachableId(sig)
	local note = ""

	if reachableId == nil then
		note = " (Script sendet an SW_S1/566 - Lampe rot? Sonst Signal im SZENARIO-Editor setzen!)"
	end

	StellwerkSetAspect(gActiveSignalIndex, aspect)
	StellwerkShowRadarStatus(sig.label .. ": " .. aspectName .. note)
	StellwerkOpenMenu()
end

function StellwerkApplyBusCommand(cmd)
	local sig_idx = math.floor(cmd / 10)
	local aspect_code = cmd - sig_idx * 10
	local aspect = ANIM_HP0
	local aspect_name = "Hp0 Halt"

	if aspect_code == 2 then
		aspect = ANIM_HP1
		aspect_name = "Hp1 Frei"
	elseif aspect_code == 3 then
		aspect = ANIM_SH1
		aspect_name = "Sh1 Rangier"
	end

	if SIGNALS[sig_idx] == nil then
		return
	end

	gActiveSignalIndex = sig_idx
	StellwerkSetAspect(sig_idx, aspect)
	StellwerkShowRadarStatus(SIGNALS[sig_idx].label .. ": " .. aspect_name)
end

function OnEvent_StellwerkStart()
	SysCall(
		"ScenarioManager:ShowAlertMessageExt",
		"Stellwerk aktiv",
		"Klicke die Meldungen: Hp0 / Sh1 / Hp1",
		30.0,
		"SW_MENU"
	)
	StellwerkBoot()
	local reachableId, aspectCode = StellwerkFindReachableId(SIGNALS[1])
	if reachableId == nil then
		StellwerkShowClickAlert(
			"WICHTIG",
			"Signal SW_S1 fehlt! SZENARIO-Editor: HL-Signal platzieren, Name SW_S1",
			"SW_MENU",
			90.0
		)
	else
		StellwerkShowClickAlert(
			"Signal OK",
			"Verbunden als " .. reachableId .. " (Aspect " .. aspectCode .. ")",
			"SW_MENU",
			20.0
		)
	end
	StellwerkOpenMenu()
	return TRUE
end

function OnEvent_StellwerkKeepAlive()
	local cmd, sigName, aspName = StellwerkReadBusCommand()
	if cmd > 0 then
		StellwerkApplyBusCommand(cmd)
		StellwerkClearBusControls(sigName, aspName)
	end
	StellwerkPollHornInput()
	SysCall("ScenarioManager:BeginConditionCheck", "StellwerkBus")
	SysCall("ScenarioManager:TriggerDeferredEvent", "StellwerkKeepAlive", KEEPALIVE_SECONDS)
	return TRUE
end

function OnEvent_SW_MENU()
	StellwerkOpenMenu()
	return TRUE
end

function OnEvent_SW_A_HP0()
	gActiveSignalIndex = 1
	StellwerkApplyAspect(ANIM_HP0, "Hp0 Halt")
	return TRUE
end

function OnEvent_SW_A_SH1()
	gActiveSignalIndex = 1
	StellwerkApplyAspect(ANIM_SH1, "Sh1 Rangierfahrt")
	return TRUE
end

function OnEvent_SW_A_HP1()
	gActiveSignalIndex = 1
	StellwerkApplyAspect(ANIM_HP1, "Hp1 Fahrt frei")
	return TRUE
end

function OnEventSW_MENU()
	return OnEvent_SW_MENU()
end

function OnEventSW_A_HP0()
	return OnEvent_SW_A_HP0()
end

function OnEventSW_A_SH1()
	return OnEvent_SW_A_SH1()
end

function OnEventSW_A_HP1()
	return OnEvent_SW_A_HP1()
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
	if condition == "StellwerkBus" then
		StellwerkBoot()
		StellwerkPollHornInput()
		local cmd, sigName, aspName = StellwerkReadBusCommand()
		if cmd > 0 then
			StellwerkApplyBusCommand(cmd)
			StellwerkClearBusControls(sigName, aspName)
			SysCall("ScenarioManager:BeginConditionCheck", "StellwerkBus")
			return CONDITION_SUCCEEDED
		end
		return CONDITION_NOT_YET_MET
	end
	return CONDITION_NOT_YET_MET
end

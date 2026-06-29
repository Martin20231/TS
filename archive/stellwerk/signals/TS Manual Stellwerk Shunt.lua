-------------------------------------------------------------------------------
-- TS Manual Stellwerk Shunt
-- Manuell steuerbares deutsches Rangiersignal (Hp0 / Sh1 / Hp1)
-- Vom Szenario per SysCall ansteuerbar:
--   SignalName:SetDispatcherMode(1)
--   SignalName:DispatcherSetAspect(0|1|4)
--   SignalName:SetState(12|13)  -- rot / frei
-------------------------------------------------------------------------------

DEBUG = false

function DebugPrint(message)
	if DEBUG then
		Print(message)
	end
end

function Initialise()
	RESET_SIGNAL_STATE = 0
	JUNCTION_STATE_CHANGE = 2

	CLEAR = 0
	WARNING = 1
	BLOCKED = 2

	ANIMSTATE_HP0 = 0
	ANIMSTATE_HP1 = 1
	ANIMSTATE_SH1 = 4

	SIGNAL_BLOCKED = 12
	SIGNAL_CLEARED = 13

	gConnectedLink = -1
	gDispatcherMode = false
	gManualAspect = ANIMSTATE_HP0
	gInitialised = false

	Call("BeginUpdate")
end

function ResetSignalState()
	DebugPrint("ResetSignalState()")
	Initialise()
end

function SetDispatcherMode(enabled)
	if enabled == 1 or enabled == true then
		gDispatcherMode = true
	else
		gDispatcherMode = false
	end
end

function DispatcherSetAspect(aspect)
	gDispatcherMode = true
	gManualAspect = aspect
	ApplyAspect(aspect)
end

function SetState(newState)
	if newState == SIGNAL_CLEARED then
		DispatcherSetAspect(ANIMSTATE_HP1)
	else
		DispatcherSetAspect(ANIMSTATE_HP0)
	end
end

function GetDispatcherAspect()
	return gManualAspect
end

function ApplyAspect(aspect)
	if aspect == ANIMSTATE_HP1 then
		Call("Set2DMapSignalState", CLEAR)
		Call("ActivateNode", "gr_trk_Shunt_RedOn", 0)
		Call("ActivateNode", "gr_trk_Shunt_WhiteOn", 1)
	elseif aspect == ANIMSTATE_SH1 then
		Call("Set2DMapSignalState", WARNING)
		Call("ActivateNode", "gr_trk_Shunt_RedOn", 0)
		Call("ActivateNode", "gr_trk_Shunt_WhiteOn", 1)
	else
		Call("Set2DMapSignalState", BLOCKED)
		Call("ActivateNode", "gr_trk_Shunt_RedOn", 1)
		Call("ActivateNode", "gr_trk_Shunt_WhiteOn", 0)
	end
end

function OnJunctionStateChange(junction_state, parameter, direction, linkIndex)
	if gDispatcherMode then
		return
	end

	DebugPrint("OnJunctionStateChange")

	gConnectedLink = Call("GetConnectedLink", "10", 1, 0)

	if gConnectedLink == 1 then
		gManualAspect = ANIMSTATE_HP1
	else
		gManualAspect = ANIMSTATE_HP0
	end

	ApplyAspect(gManualAspect)
end

function OnConsistPass(prevFrontDist, prevBackDist, frontDist, backDist, linkIndex)
end

function OnSignalMessage(message, parameter, direction, linkIndex)
	if message == RESET_SIGNAL_STATE then
		ResetSignalState()
	elseif message == JUNCTION_STATE_CHANGE then
		if linkIndex == 0 and parameter == "0" then
			OnJunctionStateChange(0, "", 1, 0)
			Call("SendSignalMessage", message, parameter, -direction, 1, linkIndex)
		end
	elseif linkIndex == 1 and parameter ~= "DoNotForward" then
		Call("SendSignalMessage", message, parameter, -direction, 1, 1)
	elseif message == 3 then
		Call("SendSignalMessage", message, parameter, -direction, 1, linkIndex)
	end
end

function Update(time)
	gInitialised = true

	if not gDispatcherMode then
		OnJunctionStateChange(0, "", 1, 0)
	else
		ApplyAspect(gManualAspect)
	end

	Call("EndUpdate")
end

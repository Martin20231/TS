-------------------------------------------------------------------------------

-- TS Stellwerk HL HS (Wrapper)

-- Laedt das Original virtualTracks-Script und uebersteuert es im Dispatcher-Modus.

-- Aspect-Codes: 0 = Hp0, 1 = Hp1, 4 = Sh1

-------------------------------------------------------------------------------



gStellwerkDispatcher = false

gStellwerkAspectCode = 0



dofile("Assets/virtualTracks/Berlin-Leipzig/RailNetwork/Signals/German-HL/vT HL HS.lua")



local _Update = Update

local _OnSignalMessage = OnSignalMessage

local _OnJunctionStateChange = OnJunctionStateChange

local _OnConsistPass = OnConsistPass

local _ReactToSignalMessage = ReactToSignalMessage

local _DetermineSignalState = DetermineSignalState
if _DetermineSignalState == nil then
	function _DetermineSignalState()
	end
end



function StellwerkApply()

	if not gStellwerkDispatcher then

		return

	end



	if gStellwerkAspectCode == 1 then

		SetLights(ANIMSTATE_SLOW, ANIMSTATE_SLOW)

	elseif gStellwerkAspectCode == 4 then

		SetLights(ANIMSTATE_SH1, ANIMSTATE_HP0)

	else

		SetLights(ANIMSTATE_HP0, ANIMSTATE_HP0)

	end

end



function SetDispatcherMode(enabled)

	if enabled == 1 or enabled == true then

		gStellwerkDispatcher = true

		StellwerkApply()

	else

		gStellwerkDispatcher = false

	end

end



function DispatcherSetAspect(aspect)

	gStellwerkDispatcher = true

	gStellwerkAspectCode = aspect

	StellwerkApply()

end



function SetState(newState)

	if newState == SIGNAL_CLEARED then

		DispatcherSetAspect(1)

	else

		DispatcherSetAspect(0)

	end

end



function GetDispatcherAspect()

	return gStellwerkAspectCode

end



function Update(time)

	if gStellwerkDispatcher then

		StellwerkApply()

		Call("EndUpdate")

	else

		_Update(time)

	end

end



function OnSignalMessage(message, parameter, direction, linkIndex)

	if gStellwerkDispatcher then

		return

	end

	_OnSignalMessage(message, parameter, direction, linkIndex)

end



function OnJunctionStateChange(junction_state, parameter, direction, linkIndex)

	if gStellwerkDispatcher then

		return

	end

	_OnJunctionStateChange(junction_state, parameter, direction, linkIndex)

end



function OnConsistPass(prevFrontDist, prevBackDist, frontDist, backDist, linkIndex)

	if gStellwerkDispatcher then

		return

	end

	_OnConsistPass(prevFrontDist, prevBackDist, frontDist, backDist, linkIndex)

end



function ReactToSignalMessage(message, parameter, direction, linkIndex)

	if gStellwerkDispatcher then

		return

	end

	_ReactToSignalMessage(message, parameter, direction, linkIndex)

end



function DetermineSignalState()

	if gStellwerkDispatcher then

		return

	end

	_DetermineSignalState()

end



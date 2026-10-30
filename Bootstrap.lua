-- Enhanced-client capabilities used by the deferred aura refresh.
BCS_EngineReady = type(CLASSIC_API_VERSION) == "number"

    and C_Timer and C_Timer.NewTimer
    and C_UnitAuras and C_UnitAuras.GetAuraDataBySpellName

if not BCS_EngineReady and DEFAULT_CHAT_FRAME then
    DEFAULT_CHAT_FRAME:AddMessage("BetterCharacterStats requires ClassicAPI, including aura lookup and timer APIs.")
end

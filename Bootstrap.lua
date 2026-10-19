-- Enhanced-client capabilities used by the deferred aura refresh.
local MIN_CLASSIC_API = 11600
BCS_EngineReady = type(CLASSIC_API_VERSION) == "number"
    and CLASSIC_API_VERSION >= MIN_CLASSIC_API
    and C_Timer and C_Timer.NewTimer
    and C_UnitAuras and C_UnitAuras.GetAuraDataBySpellName

if not BCS_EngineReady and DEFAULT_CHAT_FRAME then
    DEFAULT_CHAT_FRAME:AddMessage("BetterCharacterStats requires ClassicAPI 1.16.0 or later, including aura lookup and timer APIs.")
end

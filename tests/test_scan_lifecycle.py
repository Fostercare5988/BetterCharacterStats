"""Dirty gear scans and hidden character-panel refresh regressions."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]

def runtime():
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
        function widget()
            local f={shown=true,scripts={},height=100}
            function f:Hide() self.shown=false end
            function f:IsVisible() return self.shown end
            function f:RegisterEvent() end
            function f:UnregisterEvent() end
            function f:SetScript(k,v) self.scripts[k]=v end
            function f:GetScript(k) return self.scripts[k] end
            function f:GetHeight() return self.height end
            function f:SetHeight(h) self.height=h end
            return f
        end
        function UnitName() return 'Player' end
        function UnitClass() return 'Rogue','ROGUE' end
        PaperDollFrame=widget(); BCSFrame=widget()
        CharacterAttributesFrame=widget();CharacterModelFrame=widget()
        BCS={L={['Tree of Life Aura']='Tree of Life Aura'}}
        BCS.GetPlayerAura=function() return false end
        updates=0; auraReads=0; messages=0; tree=false; timers={}
        C_Timer={NewTimer=function(delay,callback)
            local t={callback=callback}; function t:Cancel() self.cancelled=true end
            timers[#timers+1]=t;return t
        end}
        C_UnitAuras={GetAuraDataBySpellName=function(unit,name,filter)
            assert(unit=='player' and name=='Tree of Life Aura' and filter=='HELPFUL')
            auraReads=auraReads+1;return tree and {name=name} or nil
        end}
        function GetNumPartyMembers() return 4 end
        function GetNumRaidMembers() return 0 end
        function SendAddonMessage(prefix,message,channel)
            assert(prefix=='bcs' and message=='TREE,Player' and channel=='PARTY')
            messages=messages+1
        end
    """)
    lua.execute((ROOT/'Bootstrap.lua').read_text(encoding='utf-8-sig'))
    source=(ROOT/'BetterCharacterStats.lua').read_text(encoding='utf-8-sig')
    lua.execute(source[:source.index('-- debugging / profiling')])
    lua.execute("""
        function BCS:UpdateStats()
            updates=updates+1; lastGear=self.needScanGear;lastSkills=self.needScanSkills
            self.needScanGear=false;self.needScanSkills=false
        end
        function inventoryEvent()
            event='UNIT_INVENTORY_CHANGED';arg1='player';BCS:OnEvent()
        end
        function tick(dt)
            arg1=dt
            if PaperDollFrame:IsVisible() and BCSFrame:GetScript('OnUpdate') then
                BCSFrame:GetScript('OnUpdate')()
            end
        end
        BCS:OnLoad()
    """)
    return lua

class ScanLifecycleTests(unittest.TestCase):
    def test_dirty_gear_is_scanned_once_per_stats_update(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute("""
            gear=0;talents=0;auras=0;BCS={}
            function ScanAllGear() gear=gear+1 end
            function ScanAllTalents() talents=talents+1 end
            function ScanAllAuras() auras=auras+1 end
        """)
        s=(ROOT/'helper.lua').read_text(encoding='utf-8-sig')
        lua.execute(s[s.index('function BCS:RunScans()'):s.index('-- Expose scan functions')])
        lua.execute("""
            BCS.needScanGear=true;BCS.needScanTalents=true;BCS.needScanAuras=true
            BCS:RunScans();assert(gear==1 and talents==1 and auras==1)
            BCS.needScanGear=false;BCS.needScanTalents=false;BCS.needScanAuras=false
            BCS:RunScans();assert(gear==1 and talents==1 and auras==1)
        """)

    def test_inventory_debounce_only_runs_while_work_is_pending(self):
        lua=runtime()
        lua.execute("""
            assert(not BCSFrame:GetScript('OnUpdate'))
            for i=1,50 do inventoryEvent() end
            assert(BCSFrame:GetScript('OnUpdate') and updates==0)
            tick(.1);assert(updates==0)
            tick(.11);assert(updates==1 and lastGear and lastSkills and not BCSFrame:GetScript('OnUpdate'))
            tick(10);assert(updates==1)
        """)

    def test_opening_panel_consumes_pending_equipment_change_immediately(self):
        lua=runtime()
        lua.execute("""
            PaperDollFrame:Hide();inventoryEvent();tick(1)
            assert(updates==0 and not BCS.needUpdate)
            PaperDollFrame.shown=true;BCS:OnShow()
            assert(updates==1 and lastGear and lastSkills and not BCSFrame:GetScript('OnUpdate'))
            tick(1);assert(updates==1)
        """)

    def test_aura_bursts_use_one_fresh_native_lookup_and_one_stats_refresh(self):
        lua=runtime()
        lua.execute("""
            tree=true
            for i=1,100 do event='PLAYER_AURAS_CHANGED'; BCS:OnEvent() end
            assert(#timers==1 and auraReads==0 and updates==0 and messages==0)
            timers[1].callback()
            assert(auraReads==1 and updates==1 and messages==1)
            tree=false; event='PLAYER_AURAS_CHANGED';BCS:OnEvent();timers[2].callback()
            assert(auraReads==2 and updates==2 and messages==1)
        """)

    def test_opening_panel_flushes_aura_work_and_rejects_cancelled_callback(self):
        lua=runtime()
        lua.execute("""
            PaperDollFrame:Hide();event='PLAYER_AURAS_CHANGED';BCS:OnEvent()
            local old=timers[1].callback
            PaperDollFrame.shown=true;BCS:OnShow()
            assert(updates==1 and auraReads==1 and timers[1].cancelled)
            old();assert(updates==1 and auraReads==1)
        """)

    def test_missing_required_aura_api_leaves_native_character_stats_available(self):
        lua=runtime()
        lua.execute("""
            C_UnitAuras=nil;warnings=0
            DEFAULT_CHAT_FRAME={AddMessage=function() warnings=warnings+1 end}
            CharacterAttributesFrame.shown=true
        """)
        lua.execute((ROOT/'Bootstrap.lua').read_text(encoding='utf-8-sig'))
        lua.execute("""
            BCS:OnLoad();BCS:OnShow();event='PLAYER_AURAS_CHANGED';BCS:OnEvent()
            assert(not BCSFrame:IsVisible() and CharacterAttributesFrame:IsVisible())
            assert(warnings==1 and #timers==0 and updates==0)
        """)

if __name__=='__main__':unittest.main()

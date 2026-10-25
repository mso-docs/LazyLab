"""Execute the actual storage bridge logic against a browser-API test double."""
import json
import shutil
import subprocess
import pytest


def test_browser_bridge_persists_preferences_forgets_key_and_avoids_rerun_loop(tmp_path):
    node=shutil.which('node')
    if not node:
        pytest.skip('Node is needed to execute frontend unit logic')
    from slothlab.ui.identity import BROWSER_JS
    bridge=tmp_path/'bridge.mjs';bridge.write_text(BROWSER_JS)
    script=tmp_path/'test.mjs'
    script.write_text('''import render from './bridge.mjs';
let stored='{}';const results=[];
globalThis.localStorage={getItem:()=>stored,setItem:(_,value)=>{stored=value;}};
globalThis.window={matchMedia:()=>({matches:true,addEventListener:()=>{},removeEventListener:()=>{}})};
const call=data=>render({data,setStateValue:(key,value)=>results.push(value)});
call({desired:{mode:'Browser profile',theme:'Dark',token:'a'.repeat(43)}});
const first=results.at(-1);
if(first.theme!=='Dark'||!first.system_dark||JSON.parse(stored).token!=='a'.repeat(43))throw Error('did not persist');
const count=results.length;call({observed:first});if(results.length!==count)throw Error('rerun loop');
call({desired:{token:null,mode:'Guest'}});if(JSON.parse(stored).token!==undefined)throw Error('forget failed');
console.log('frontend storage behavior passed');
''')
    result=subprocess.run([node,str(script)],text=True,capture_output=True,timeout=10)
    assert result.returncode==0,result.stderr

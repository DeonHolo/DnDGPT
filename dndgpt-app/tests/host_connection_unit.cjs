// Execute the actual dashboard startup with protocol hosts; no npm dependencies.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../app/index.html'),'utf8');
const start=html.indexOf('async function initializeDashboardHost(){');
assert(start>=0,'Dashboard host bootstrap missing');
const source=html.slice(start,html.indexOf('</script>',start));
const normalizeStart=html.indexOf('function normalizeViewPreferences(');
const normalizeSource=html.slice(normalizeStart,html.indexOf('let preferences=',normalizeStart));
function host(bridge=false,embedded=true){
 const events=[],timers=new Map(),nodes=new Map();let resolveInit,rejectInit;
 const context={standard:false,hostCapabilities:{},hostContext:{},pollingTimer:null,syncIssue:false,uiVersion:'fixture',
  window:{openai:bridge?{callTool(){}}:undefined},
  rpc(method){events.push(method);return new Promise((resolve,reject)=>{resolveInit=resolve;rejectInit=reject})},
  notify(method){events.push(method)},
  setTimeout(fn,ms){timers.set(ms,fn);return ms},clearTimeout(id){timers.delete(id)},
  $(id){if(!nodes.has(id))nodes.set(id,{dataset:{}});return nodes.get(id)},
  applyHostContext(){},renderChoices(){},restorePreferences(){},receive(){},
  refresh(){events.push('retry');context.syncIssue=false;return Promise.resolve()},
  startSavedConnection(){if(context.pollingTimer)return context.initialConnection;context.pollingTimer=1;events.push(context.standard?'standard-read':'compatibility-read');context.initialConnection=Promise.resolve();return context.initialConnection}
 };
 context.window.parent=embedded?{}:context.window;
 vm.createContext(context);vm.runInContext(source,context);
 return {context,events,timers,resolve:init=>resolveInit(init),reject:()=>rejectInit(Error('No standard bridge'))};
}
const init={protocolVersion:'2026-01-26',hostCapabilities:{serverTools:{}},hostContext:{}};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 for(const bridge of [false,true]){
  const h=host(bridge);assert.deepEqual(h.events,['ui/initialize']);h.resolve(init);await tick();
  assert.deepEqual(h.events,['ui/initialize','ui/notifications/initialized','standard-read']);assert.equal(h.timers.size,0);
 }
 const legacy=host(true);assert(legacy.timers.has(300));legacy.timers.get(300)();
 assert.deepEqual(legacy.events,['ui/initialize','compatibility-read']);legacy.reject();await tick();assert.equal(legacy.events.filter(e=>e==='compatibility-read').length,1);
 const slow=host(true);slow.timers.get(300)();slow.context.syncIssue=true;slow.resolve(init);await tick();
 assert.deepEqual(slow.events,['ui/initialize','compatibility-read','ui/notifications/initialized','retry']);
 const standalone=host(false,false);assert.deepEqual(standalone.events,[]);
 const sandbox={};vm.createContext(sandbox);vm.runInContext(normalizeSource,sandbox);
 const partial=sandbox.normalizeViewPreferences({layout:'ember'});assert.equal(partial.layout,'ember');assert.equal(partial.panels.length,0);assert.equal(partial.details.length,0);
 for(const value of [null,[],{panels:'skills',details:null},{panels:[null,'skills'],details:[1,'appearance-domain']}]){
  const preferences=sandbox.normalizeViewPreferences(value);assert(Array.isArray(preferences.panels)&&Array.isArray(preferences.details));assert(preferences.panels.every(v=>typeof v==='string')&&preferences.details.every(v=>typeof v==='string'));
 }
 console.log('Host bootstrap: standard, hybrid, legacy, delayed recovery, standalone and partial preferences passed');
})().catch(error=>{console.error(error);process.exitCode=1});

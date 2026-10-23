import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createServer, request as httpRequest, globalAgent } from 'node:http'
import { mkdtemp, readFile, writeFile, mkdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as pause } from 'node:timers/promises'
import { staticServer } from '../../ops/serve_frontend.mjs'

export async function coverageBrowser() {
  assert.equal(process.env.RUN_AUC08_BROWSER,'1')
  const host=process.env.AUC_API_HOST
  assert.match(host,/^auc08-[a-f0-9]+-backend$/)
  const work='/checks',site=staticServer('/site'),artifacts=join(work,'screenshots')
  await mkdir(artifacts,{recursive:true})
  const proxy=createServer((req,res)=>{
    if(!req.url.startsWith('/api/'))return site.emit('request',req,res)
    const upstream=httpRequest({hostname:host,port:8000,path:req.url,method:req.method,headers:req.headers},response=>{
      res.writeHead(response.statusCode,response.headers);response.pipe(res)
    })
    upstream.on('error',error=>{if(res.headersSent)res.destroy();else{res.writeHead(502);res.end(error.message)}});req.pipe(upstream)
  })
  await new Promise(resolve=>proxy.listen(18175,'127.0.0.1',resolve))
  const profile=await mkdtemp(join(tmpdir(),'auc08-chromium-'))
  const processBrowser=spawn('/usr/bin/chromium',['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
    '--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--window-size=1440,1000',`--user-data-dir=${profile}`],{stdio:'ignore'})
  let port
  for(let i=0;i<100;i++){
    try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break}catch{await pause(100)}
  }
  assert.ok(port,'Chromium started')
  const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  const socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl)
  await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true})})
  let sequence=0
  const pending=new Map(),exceptions=[]
  socket.addEventListener('message',event=>{
    const message=JSON.parse(event.data)
    if(message.method==='Runtime.exceptionThrown')exceptions.push(message.params.exceptionDetails.exception?.description??message.params.exceptionDetails.text)
    const task=pending.get(message.id)
    if(!task)return
    pending.delete(message.id);clearTimeout(task.timeout)
    if(message.error)task.reject(new Error(message.error.message));else task.resolve(message.result)
  })
  const command=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++sequence,timeout=setTimeout(()=>{pending.delete(id);reject(new Error(method+' timeout'))},15000)
    pending.set(id,{resolve,reject,timeout});socket.send(JSON.stringify({id,method,params}))
  })
  async function evaluate(expression){
    const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})
    if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text)
    return r.result.value
  }
  async function wait(expression){
    for(let i=0;i<150;i++){if(await evaluate(expression))return;await pause(75)}
    const alerts=await evaluate(`[...document.querySelectorAll('[role="alert"]')].map(x=>x.innerText)`)
    throw new Error('Wait failed: '+expression+'; alerts='+JSON.stringify(alerts))
  }
  const fill=async(selector,value)=>{
    await wait(`!!document.querySelector(${JSON.stringify(selector)})&&document.querySelector(${JSON.stringify(selector)}).checkVisibility()&&!document.querySelector(${JSON.stringify(selector)}).disabled`)
    return evaluate(`(()=>{
    const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw new Error('Missing input '+${JSON.stringify(selector)});
    const p=e instanceof HTMLSelectElement?HTMLSelectElement.prototype:e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(p,'value').set.call(e,${JSON.stringify(String(value))});
    e.dispatchEvent(new Event('input',{bubbles:true}));if(e instanceof HTMLSelectElement)e.dispatchEvent(new Event('change',{bubbles:true}));
  })()`)
  }
  async function click(label,scope=''){
    const selector=scope?scope+' button':'button'
    await wait(`!![...document.querySelectorAll(${JSON.stringify(selector)})].find(e=>e.checkVisibility()&&e.textContent.trim()===${JSON.stringify(label)}&&!e.disabled)`)
    await evaluate(`[...document.querySelectorAll(${JSON.stringify(selector)})].find(e=>e.checkVisibility()&&e.textContent.trim()===${JSON.stringify(label)}&&!e.disabled).click()`)
  }
  const screenshot=async name=>{
    const r=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})
    await writeFile(join(artifacts,name+'.png'),Buffer.from(r.data,'base64'))
  }
  await command('Runtime.enable')
  await command('Page.enable')
  await command('Page.addScriptToEvaluateOnNewDocument',{source:`
    (()=>{if(window.__aucInstrumented)return;window.__aucInstrumented=true;
    window.__aucWrites=[];const nativeFetch=window.fetch.bind(window);
    window.fetch=async(...args)=>{const r=await nativeFetch(...args);const method=args[1]?.method??'GET';
      if(!['GET','HEAD','OPTIONS'].includes(method)&&!String(args[0]).includes('/auth/')){
        let body=null;try{body=await r.clone().json()}catch{};
        window.__aucWrites.push({url:String(args[0]),method,status:r.status,body});
      }return r};})();`})
  for(let i=0;i<100;i++){
    try{if((await fetch(`http://${host}:8000/api/health/`)).ok)break}catch{}
    if(i===99)throw new Error('Temporary API did not start');await pause(100)
  }
  await command('Page.navigate',{url:'http://127.0.0.1:18175/'})
  await wait('Array.isArray(window.__aucWrites)')
  return {evaluate,wait,fill,click,screenshot,pause,exceptions,
    async close(){
      socket.close();processBrowser.kill('SIGTERM')
      for(const task of pending.values())clearTimeout(task.timeout)
      await new Promise(resolve=>{proxy.close(resolve);proxy.closeAllConnections()})
      globalAgent.destroy()
    }}
}

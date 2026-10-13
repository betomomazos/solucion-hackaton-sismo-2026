const {spawn} = require('node:child_process');
const fs = require('node:fs');
const {chromium} = require('C:/Users/LENOVO/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const server=spawn('python',['-c',"from app import app; app.run(host='127.0.0.1',port=5056,debug=False,use_reloader=False)"],{cwd:process.cwd(),stdio:'ignore',windowsHide:true});
 let browser;
 try {
  let ready=false;
  for(let i=0;i<60;i++) {try{const r=await fetch('http://127.0.0.1:5056/'); if(r.ok){ready=true; break;}}catch{} await new Promise(r=>setTimeout(r,250));}
  if(!ready) throw Error('Servidor de prueba no disponible');
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let analysisRequests=0;
  page.on('request',r=>{if(r.url().endsWith('/api/analisis')) analysisRequests++;});
  await page.route('**/*',route=>route.request().url().startsWith('http://127.0.0.1:5056/')?route.continue():route.abort());
  await page.goto('http://127.0.0.1:5056/');
  await page.getByRole('button',{name:'IA e informes',exact:true}).click();
  await page.locator('#consultar-web').uncheck();
  await page.locator('#generar-informe').click();
  await page.waitForFunction(()=>!document.querySelector('#descargar-pdf').disabled,{timeout:30000});
  if(await page.locator('#informe-contenido').innerText().then(s=>!s.includes('Los Santos'))) throw Error('No aparece el ranking');
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#descargar-pdf').click()]);
  await download.saveAs('tmp/pdfs/descarga-navegador.pdf');
  if(fs.readFileSync('tmp/pdfs/descarga-navegador.pdf').subarray(0,5).toString()!=='%PDF-')throw Error('Descarga no PDF');
  if(analysisRequests!==1)throw Error('La exportacion repitio el analisis');
  await page.screenshot({path:'tmp/pdfs/interfaz.png',fullPage:false});
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2))throw Error('Desbordamiento movil');
  if(errors.length)throw Error(errors.join('\n'));
  console.log('Navegador: analisis sin recursos externos, ranking, PDF sin nueva consulta y vista movil correctos.');
 } finally {if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});

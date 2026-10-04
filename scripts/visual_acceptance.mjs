/** Isolated real-Chromium QA. Only the explicitly authorized loopback origin is reachable. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const playwrightPath=process.env.PLAYWRIGHT_MODULE;
if(!playwrightPath)throw new Error('Set PLAYWRIGHT_MODULE to installed playwright-core/index.mjs');
const {chromium}=await import(pathToFileURL(playwrightPath));
const origin=process.env.VISUAL_BASE_URL||'http://127.0.0.1:18089';
if(origin!=='http://127.0.0.1:18089')throw new Error('This QA runner is restricted to the authorized isolated origin');
const output=process.env.VISUAL_OUTPUT||'artifacts/release/visual-20261003';
await fs.mkdir(path.join(output,'screenshots'),{recursive:true});
const env=Object.fromEntries((await fs.readFile('artifacts/release/.env.smoke.local','utf8')).split('\n').filter(x=>x&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1)]}));
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const result={origin,scope:'Synthetic disposable data; real Chromium UI; no real AI or campus integration',pages:[],errors:[],blockedRequests:[],flows:[]};
async function capture(page,name){
  await page.waitForLoadState('networkidle',{timeout:15000}).catch(()=>{});
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:path.join(output,'screenshots',name+'.png'),fullPage:false});
  const info=await page.evaluate(()=>({title:document.title,url:location.pathname,text:document.body.innerText.slice(0,16000),viewport:{width:innerWidth,height:innerHeight},documentWidth:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll('button')].map(x=>x.innerText).filter(Boolean),headings:[...document.querySelectorAll('h1,h2,h3')].map(x=>x.textContent)}));
  result.pages.push({name,...info});
  await fs.writeFile(path.join(output,'result.json'),JSON.stringify(result,null,2));
}
try {
 for(const [role,username,password,routes] of [
   ['student','perf-user-0','synthetic-only-password',['/student','/scores','/ability','/reports','/environment-results']],
   ['teacher','perf-teacher-0','synthetic-only-password',['/teacher','/classes','/class-scores','/batch-reports','/env-check']],
   ['admin',env.BOOTSTRAP_ADMIN_USER||'admin',env.BOOTSTRAP_ADMIN_PASSWORD,['/admin','/admin/release','/admin/config','/dashboard']],
 ]){
  const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'zh-CN',reducedMotion:'reduce'});
  await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin===origin)return route.continue();result.blockedRequests.push(u.origin+u.pathname);return route.abort();});
  const page=await context.newPage();page.setDefaultTimeout(20000);page.setDefaultNavigationTimeout(30000);
  page.on('pageerror',e=>result.errors.push({role,path:new URL(page.url()).pathname,error:e.message}));
  page.on('response',r=>{if(r.status()>=400)result.errors.push({role,path:new URL(r.url()).pathname,status:r.status()})});
  await page.goto(origin+'/login');
  if(role==='student')await capture(page,'login-desktop');
  await page.getByLabel('用户名',{exact:true}).fill(username);
  await page.getByLabel('密码',{exact:true}).fill(password);
  await page.getByRole('button',{name:'登录',exact:true}).click();
  await page.waitForURL(u=>u.pathname!=='/login');
  result.flows.push({role,action:'login',passed:true});
  for(const route of routes){await page.goto(origin+route);await capture(page,role+route.replaceAll('/','-'));}
  if(role==='admin'){
   await page.goto(origin+'/admin/release');
   for(const name of ['真实实训导入','校方数据源','操作审计','运行与备份']){
    const button=page.getByRole('button',{name,exact:true});
    if(await button.count()){await button.click();await capture(page,'admin-release-'+name);}
   }
  }
  await page.setViewportSize({width:390,height:844});
  for(const route of [routes[0],role==='admin'?'/admin/release':routes[1],...(role==='student'?['/environment-results']:[])]){
   await page.goto(origin+route);await capture(page,role+'-mobile'+route.replaceAll('/','-'));
  }
  if(role!=='admin'){
    await page.goto(origin+'/admin/release');await page.waitForURL(u=>u.pathname==='/'+role);result.flows.push({role,action:'admin route rejected',passed:true});
  }
  await page.getByRole('button',{name:'退出',exact:true}).click();await page.waitForURL('**/login');result.flows.push({role,action:'logout',passed:true});
  if(role==='student')await capture(page,'login-mobile');
  await context.close();
 }
} finally {
 await browser.close();await fs.writeFile(path.join(output,'result.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify({pages:result.pages.length,flows:result.flows,errors:result.errors,overflow:result.pages.filter(x=>x.documentWidth>x.viewport.width).map(x=>({name:x.name,width:x.documentWidth,viewport:x.viewport.width}))}));
}

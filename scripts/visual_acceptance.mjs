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
const testPhoto=path.join(output,'synthetic-photo.png');
// Blue synthetic schematic labelled NOT SCHOOL PHOTO; no real personal or school imagery.
await fs.writeFile(testPhoto,Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAoAAAAFoCAIAAABIUN0GAAALQElEQVR4nO3cf6zVdR3H8e+9FwF/JDl1TJoyUXBRkGmZkYQ6HJlhotjQWVamW6hI5g9SdBaTmabiL+YQZsNSav7AX0wQmYsUFJUSBYSB/BCUAOs6SX7dexteu7u759zruTZ4sXg8/rr33O/3+/58vne7z3vOuVDVdfA1BQCwa1Xv4nkAgAADQIZnwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABDQocjpc0S30ecP2qumZnt9/cg7Htlv704Trhp28oi76hsaiqKYcdvwEXc8Mv3W4a++tfrMayc2nrJkynW9ho357jd7Xzi4X1EUx/Xu/vLClUVRTHp67m2XDuk1bEzTxRuPLIpixcM3zF/yTuOD019etGrdP9s497xBXz//1OM2fbR100dbrhz/+NoNtaUXbP5x8wfLruruXwxtPv3eqS+02PXRPb9QetZTL7xRertWPvzr0ltRFMWwgcdecNrxW7fXdexQc9+Tc/4867WyK2m8ZovpazfUlt1y8321Pau1B1tcoUnjt6OhoejQofr6idP+tvSdymeV3dd+e3cqnQ6w+0sGeNyIM88b88C7G2q/1+9LN/z01ItunrJ41brTT+gzdfbrA7921Ir33l+8ct2W7dtraqr79Tn8xQVvN504bc7CaXMWNv6wHnLNJ0G67dIhZads3V7XdEzT6WXPHXD0kUO+3XfwVRM2b9128rG97hw5dOjoSZVvp7VVtZheuuvSs8oqeytOOqbnuaccO3T0pNpNm7vs2/mB63/03sbasispO/2PM16pfMtlZ9XUVJc++Je/L2vtIk3fji927zrusrMGXT6+8lml+zrpmJ4Xnd6v8ukAu4/kS9AHfX6/znvt+A1g+kuLJz09tyiKW6fMGvmDE6urqkacPeB3D81qPOyWB2dede7AXbCenw85YezkGZu3biuKYtarS1a8u3GvmppdsOvKld6K4UP6/+b+Z2o3bS6KonbT5jH3P3PJ0AGVT2/XlsvOau8Cmixaue6wrge0a9ZnPgxgN5QM8NjJMx6/6cLbR5x5XO/uL725oiiKpavXL1zx3i0Xn7Fmfe2S1f9oPOyvry8viuJbfXrs7PUcdVjXBcvfbfr0inumbqur2wW7rlzpreh56MELlq9t+vT15Wt7HXpw5dPbteWys9q7gCb9v3LEG81GVzLrMx8GsBtKvgT9p+dee+alRace33vMhadNm7Pwdw891/gkePb4kf2Hj2t+5M0Pzrz63IHf/9WO/LSmY4eax8b+rPmnpY/fOHnGK4tXtXaFmuqq/3lPba2qcXrZXZcadd4p3+jd/b4nX2x80bXCW1FVVH38BnqrWkxvbcut3czSWVVV7VtA45Wrqqo+2LT58rsea9esT1XhYQB7dIAP7LJvj0MOnLd41ZSZrz47b/Hzd41oTNGyNRs+/GjLsjUbmh/84oK36+obTujb1pPgFu/1LplyXdnH27B87cYvH37Ia0tW7/hRXlV1x2VnjRj3cNNXG+obaqqr6+rrO9RU19XVV7jNFtNb23Wpm/7wbNnHW9yKJavX9+3Rbd5/f6voe0S3t1ata20xpdOXrdlQdstlb2bZWdXV1ZUvoOy3o/JZpVdr1/YBdiuxl6AbGhomXH1Ot4O6FEVxwOf2WbP+X20ff/ODM6/cye8E3z9t7qgfntLx47dIz+jfp9PHHzSZv/SdAUcfWRTFiV/tOX/pJ3/YvLN3/am3Yvyjs6/7yXf236dzURRd9u08+seD7nl0duXT295yC2VntWsBlavwsjtpOsD/8zPg9z/49xX3TJ046pzNW7bX1dePvPPRto+f++aKbdvrOnVo94Kbv8L5yuJVN06e0dqRj89e0KPbQc/efvHG2k0baj8cde8Tzb967YSnbr1kyIizd/yNzy/vfuwzT2/Xrj/1Vjw/f+khB+7/yNgLtm7b8e9wJj41Z3brfwNces8Xr1zXxpZbaG1W2Qc7dqh54rcXNZ44b9HKMb+f3q49Vrivdm0fYLdS1XXwNek1AMAex/+EBQABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAgwAewbPgAEgQIABIECAASBAgAEgQIABIECAASBAgAEgQIABIECAASBAgAEgQIABIECAASBAgAEgQIABIECAASBAgAFAgAFgz+AZMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAECDAABAgwAAQIMAAUu95/AML/MHsGsMYhAAAAAElFTkSuQmCC','base64'));

const env=Object.fromEntries((await fs.readFile('artifacts/release/.env.smoke.local','utf8')).split('\n').filter(x=>x&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1)]}));
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const runId=Date.now().toString();
const result={origin,scope:'Synthetic disposable data; real Chromium UI; no real AI or campus integration',pages:[],errors:[],blockedRequests:[],flows:[]};
async function requestAction(page,name,method,url,button) {
 const pending=page.waitForResponse(r=>r.request().method()===method&&r.url().includes(url));
 await page.getByRole('button',{name:button,exact:true}).click();
 const response=await pending;const data=await response.json();
 if(!response.ok())throw new Error(name+': '+response.status());
 result.flows.push({action:name,passed:true,response:data});return data;
}
async function download(page,name,button){const pending=page.waitForEvent('download');await page.getByRole('button',{name:button,exact:true}).click();const file=await pending;await file.saveAs(path.join(output,name));if(await file.failure())throw new Error(name);result.flows.push({action:name,passed:true});}
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
  if(process.env.VISUAL_ROLES&&!process.env.VISUAL_ROLES.split(',').includes(role))continue;
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

  if(role==='student'){
   await page.goto(origin+'/scores');await page.getByRole('button',{name:/查看步骤证据/}).first().click();await page.getByRole('button',{name:'关闭',exact:true}).waitFor();await capture(page,'student-score-evidence');
   await page.setViewportSize({width:390,height:844});await capture(page,'student-score-evidence-mobile');await page.setViewportSize({width:1440,height:1000});
   await page.goto(origin+'/reports');await page.getByRole('button',{name:/合成项目0.*合成学生0诊断报告/}).click();await page.getByRole('button',{name:'下载 Word',exact:true}).waitFor();await capture(page,'student-report-document');await download(page,'diagnostic-report.doc','下载 Word');
   await page.setViewportSize({width:390,height:844});await capture(page,'student-report-mobile');await page.getByRole('button',{name:'下载 Word',exact:true}).scrollIntoViewIfNeeded();await capture(page,'student-report-mobile-body');await page.setViewportSize({width:1440,height:1000});
   await page.getByRole('link',{name:/关联实训/}).click();await page.getByRole('button',{name:'关闭',exact:true}).waitFor();result.flows.push({role,action:'report linked score evidence',passed:true});
   await page.goto(origin+'/reports');await requestAction(page,'report task submission','POST','/api/v1/reports/generate','生成单次报告');await page.getByRole('status').filter({hasText:'生成失败'}).waitFor({timeout:45000});await capture(page,'student-report-unconfigured-ai');result.flows.push({role,action:'unconfigured AI honestly reports failure',passed:true});
   await page.goto(origin+'/environment-results');await page.getByLabel(/^关联实训/).selectOption({index:1});await page.getByLabel(/^对应实训室/).selectOption('perf-lab-0');await page.getByLabel('现场图片',{exact:true}).setInputFiles(testPhoto);
   await requestAction(page,'image upload task submission','POST','/api/v1/environment/tasks','提交环境检查');await page.getByRole('status').filter({hasText:'failed'}).waitFor({timeout:45000});await capture(page,'student-image-upload-unconfigured-ai');result.flows.push({role,action:'image task failure is visible',passed:true});
  }
  if(role==='teacher'){
   await page.goto(origin+'/classes');await page.getByLabel(/^授权班级/).selectOption('perf-class-0');await page.getByRole('button',{name:/合成学生0 /}).waitFor();await capture(page,'teacher-class-populated');await download(page,'class-overview.csv','导出班级统计与能力分析');
   await page.getByRole('button',{name:/合成学生0 /}).click();await page.getByRole('heading',{name:'毕业标准评估',exact:true}).waitFor();await capture(page,'teacher-student-detail');await page.setViewportSize({width:390,height:844});await capture(page,'teacher-student-detail-mobile');await page.setViewportSize({width:1440,height:1000});
   await page.goto(origin+'/env-check');await page.getByLabel(/^学生/).selectOption('perf-student-0');await capture(page,'teacher-before-review');await page.getByLabel(/^复核总结/).fill('合成视觉验收：人工调整首项为19分；非真实教学评价。');await page.getByLabel('人工分数',{exact:true}).first().fill('19');await page.getByLabel(/^整体复核备注/).fill('浏览器自动化核对修改、驳回、确认与留痕');
   const modified=await requestAction(page,'teacher modifies image review','POST','/review','保存人工复核');if(modified.final_score!==79)throw new Error('Expected reviewed total 79');await capture(page,'teacher-review-modified');
   await requestAction(page,'teacher rejects image review','POST','/review','驳回并保存');await requestAction(page,'teacher confirms image review','POST','/review','确认 AI 结果');
   await page.reload();await page.getByLabel(/^学生/).selectOption('perf-student-0');await page.getByText(/最近复核：/).waitFor();await capture(page,'teacher-review-persisted');await page.setViewportSize({width:390,height:844});await page.getByLabel(/^复核总结/).scrollIntoViewIfNeeded();await capture(page,'teacher-review-mobile');await page.setViewportSize({width:1440,height:1000});
  }
  if(role==='admin'){
   await page.goto(origin+'/admin/release');await page.getByLabel(/^数据类型/).selectOption('majors');await page.getByLabel('名称 *',{exact:true}).fill('视觉测试专业 '+runId);await page.getByLabel('编码 *',{exact:true}).fill('VIS-'+runId);
   const created=await requestAction(page,'admin creates catalog entry','POST','/release/catalog/majors','保存');await page.getByRole('button',{name:new RegExp('视觉测试专业 '+runId)}).click();await page.getByLabel('说明',{exact:true}).fill('仅限隔离环境的合成视觉验收');await requestAction(page,'admin edits catalog entry','PUT','/release/catalog/majors/','保存');await requestAction(page,'admin reads version history','GET','/release/versions/','查看修改前后记录');await capture(page,'admin-config-version-history');await download(page,'major-template.csv','下载导入模板');
   await page.getByLabel(/^数据类型/).selectOption('labs');await page.getByRole('button',{name:/合成实训室0/}).click();await page.getByLabel('标准状态图片',{exact:true}).setInputFiles(testPhoto);await requestAction(page,'admin uploads standard photo','POST','/reference','保存标准状态图片');await requestAction(page,'admin reads reference photo list','GET','/reference-images','管理已有参考图');await capture(page,'admin-reference-photo');
   await page.getByRole('button',{name:'真实实训导入',exact:true}).click();const steps=JSON.stringify({s1:true,s2:false}).replaceAll('"','""');const csv='source_record_id,student_no,project_code,completed_at,steps\nVIS-'+runId+',SYN0000,SYN-P0,2026-09-02T08:00:00+08:00,"'+steps+'"\n';await page.getByLabel('实训记录文件',{exact:true}).setInputFiles({name:'visual-records.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
   const imported=await requestAction(page,'admin imports actual-format synthetic record','POST','/release/records/import','导入并计算');const duplicate=await requestAction(page,'admin repeats same import','POST','/release/records/import','导入并计算');if(imported.success!==1||imported.errors!==0||duplicate.success!==0||duplicate.skipped!==1||duplicate.errors!==0)throw new Error('Import/deduplication mismatch');result.flows.push({action:'import and deduplication results',passed:true,imported,duplicate});await requestAction(page,'admin reads synchronization history','GET','/admin/sync/history','查询同步历史与异常');await capture(page,'admin-record-import-history');
   await page.getByRole('button',{name:'操作审计',exact:true}).click();await requestAction(page,'admin queries audit','GET','/release/audit','查询');await capture(page,'admin-audit-results');
   await page.getByRole('button',{name:'运行与备份',exact:true}).click();await requestAction(page,'admin creates encrypted backup','POST','/release/backups','立即创建加密备份');await capture(page,'admin-backup-created');
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
 if(result.errors.length||result.blockedRequests.length||result.pages.some(x=>x.documentWidth>x.viewport.width))process.exitCode=1;
 console.log(JSON.stringify({pages:result.pages.length,flows:result.flows.map(({response,...rest})=>rest),errors:result.errors,overflow:result.pages.filter(x=>x.documentWidth>x.viewport.width).map(x=>({name:x.name,width:x.documentWidth,viewport:x.viewport.width}))}));
}

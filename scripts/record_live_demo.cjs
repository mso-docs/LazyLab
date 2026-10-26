/** Record the real Streamlit UI. Requires Playwright + its Chromium/FFmpeg.
 * Start an isolated demo workspace, then run with NODE_PATH pointing to the
 * installed playwright package directory. Raw output remains in artifacts/.
 */
const {chromium}=require('playwright');
const fs=require('node:fs');const path=require('node:path');
(async()=>{
 const out=path.resolve('artifacts/public-demo/recording');fs.mkdirSync(out,{recursive:true});
 fs.rmSync(path.join(out,'chapters.json'),{force:true});
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000},recordVideo:{dir:out,size:{width:1440,height:1000}},acceptDownloads:true,reducedMotion:'reduce'});
 const page=await context.newPage();page.setDefaultTimeout(25000);
 const epochs=[];let start;
 const pause=ms=>page.waitForTimeout(ms);
 async function shot(name,text,ms=5000){const visible=await page.locator('body').innerText();
  const inputs=await page.locator('input:visible,textarea:visible').evaluateAll(items=>items.map(x=>x.value).join(' '));
  if (/\/home\/|\/Users\/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/.test(visible+' '+inputs)) throw new Error('Potential private information visible; recording stopped');
  epochs.push({name,text,start:(Date.now()-start)/1000});await page.screenshot({path:path.join(out,`${String(epochs.length).padStart(2,'0')}.png`)});console.log(name);await pause(ms);}
 async function tab(name){await page.getByRole('tab',{name,exact:true}).click();await pause(700);}
 async function choose(label,option){await page.getByRole('combobox',{name:label,exact:true}).click();await page.getByRole('option',{name:option,exact:true}).click();await pause(1000);}
 try {
  await page.goto(process.env.DEMO_URL||'http://127.0.0.1:8502');
  await choose('Research session',process.env.DEMO_SESSION||'Independent confirmation of a scoped prevalence-shift condition · completed · 5bee1711');
  await choose('Appearance','Light');await pause(1000);
  start=Date.now();
  await shot('Welcome','This is the running SlothLab app. The selected investigation was completed earlier; this walkthrough does not start a new research run.');
  await choose('Appearance','Dark');await shot('Dark appearance','Switch between Light, Dark, and System appearance.',4000);
  await choose('Appearance','Light');
  await tab('New investigation');
  await page.getByLabel('Research question',{exact:true}).scrollIntoViewIfNeeded();
  await shot('Design a question','New investigation defines a testable question within the registered prior-correction experiment.');
  await page.getByText('AI server connection · local or remote',{exact:true}).click();
  await page.getByRole('button',{name:'Discover installed models',exact:true}).click();await pause(1500);
  await shot('Local or remote AI','Discover installed models on a local or remote Ollama-compatible endpoint. Experiments still execute on the app host.');
  await page.getByLabel('Maximum experiments',{exact:true}).scrollIntoViewIfNeeded();
  await shot('Finite research budgets','Set experiment and token budgets before running. Reserve independent confirmation seeds. No new investigation is launched in this recording.',6000);
  await tab('Research');
  await page.getByRole('tab',{name:'Overview',exact:true}).scrollIntoViewIfNeeded();
  await shot('Recorded measurements','The completed investigation contains five real executions and one verified reuse. These are recorded results, not simulated demo data.',6000);
  await tab('Experiments');await shot('Experiment history','Inspect the experiment table and distinguish execution from exact-result reuse. Reuse does not count as independent replication.',6000);
  await tab('Findings');await shot('Evidence and uncertainty','Read the finite protocol assessment and confirmatory evidence. Operational completion does not establish a universal scientific conclusion.',7000);
  await tab('Provenance & export');
  await page.getByRole('button',{name:'Prepare research bundle',exact:true}).click();
  const download=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download research bundle',exact:true}).click()]).then(x=>x[0]);
  const bundle=path.join(out,'demo-history.zip');await download.saveAs(bundle);
  await shot('Portable export','Prepare and download a portable research bundle containing recorded measurements and artifacts.',5000);
  await choose('History mode','Guest');
  await shot('Guest without SQL','Guest mode uses temporary JSON documents and artifact files. Download a bundle to preserve the session.',5000);
  await page.getByText('Guest history · open a downloaded research bundle',{exact:true}).click();
  await page.getByTestId('stFileUploader').locator('input[type=file]').setInputFiles(bundle);await pause(900);
  await page.getByRole('button',{name:'Open research bundle',exact:true}).click();await pause(1200);
  await page.getByRole('tab',{name:'Overview',exact:true}).scrollIntoViewIfNeeded();
  await shot('Reopened guest history','The exported investigation is now reopened in Guest mode. Importing history starts no inference.',6000);
  await tab('Learn & help');
  await page.getByRole('combobox',{name:'Jump to a chapter',exact:true}).scrollIntoViewIfNeeded();
  await shot('Interactive learning','Learn and help provides a captioned lesson, chapter navigation, transcripts, and practice questions.',5000);
  await tab('Research design checklist');
  await page.getByText('Before you run',{exact:true}).scrollIntoViewIfNeeded();
  await shot('Research design checklist','Use the checklist to plan hypotheses, controls, confirmation seeds, budgets, and uncertainty.',5000);
  await choose('History mode','Browser profile');
  await page.getByRole('textbox',{name:'Profile name',exact:true}).fill('Demo researcher');
  await page.getByRole('textbox',{name:'Profile name',exact:true}).press('Enter');await pause(1000);
  await page.getByRole('button',{name:'Create browser profile',exact:true}).click();await pause(1200);
  await shot('Remembered local profile','A named local browser profile keeps separate history on this browser and origin. It is a convenience profile, not cross-device account sign-in.',6000);
  fs.writeFileSync(path.join(out,'chapters.json'),JSON.stringify({chapters:epochs,end:(Date.now()-start)/1000},null,2));
  await page.screenshot({path:path.join(out,'final.png')});
 } catch(error){await page.screenshot({path:path.join(out,'error.png')});console.error(error);process.exitCode=1;}
 finally {const video=page.video();await context.close();const videoPath=await video.path();fs.writeFileSync(path.join(out,'video-path.txt'),videoPath);await browser.close();console.log('Raw video:',videoPath);}
})();
